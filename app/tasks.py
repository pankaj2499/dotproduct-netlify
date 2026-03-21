import io
from collections import Counter
import time

import matplotlib
import numpy as np
from pyspark.sql import SparkSession
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE
from weaviate.dotproduct import DotproductStore

from .celery_app import celery_app

matplotlib.use("Agg")
import matplotlib.pyplot as plt


@celery_app.task(name="app.tasks.long_running_sum")
def long_running_sum(values: list[int], delay_seconds: int = 5) -> int:
    """Example task that simulates work in the worker container."""
    time.sleep(delay_seconds)
    return sum(values)


def _build_spark_session(app_name: str) -> SparkSession:
    return (
        SparkSession.builder.master("local[*]")
        .appName(app_name)
        .config("spark.ui.enabled", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "0.0.0.0")
        .getOrCreate()
    )


def _project_vectors_for_plot(vectors: list[list[float]]) -> tuple[np.ndarray, str]:
    array = np.asarray(vectors, dtype=float)
    if array.ndim != 2:
        raise ValueError("Expected a 2D vector matrix for plotting")
    if array.shape[0] < 3:
        if array.shape[1] >= 2:
            return array[:, :2], "raw"
        return np.column_stack([array[:, 0], np.zeros(array.shape[0])]), "raw"

    perplexity = max(1, min(30, array.shape[0] - 1))
    coords = TSNE(
        n_components=2,
        perplexity=perplexity,
        random_state=42,
        init="random",
        learning_rate=200,
    ).fit_transform(array)
    return coords, "tsne"


def _build_cluster_plot_png(
    *,
    workload_id: str,
    vectors: list[list[float]],
    labels: list[int],
) -> tuple[bytes, dict]:
    coords, plot_kind = _project_vectors_for_plot(vectors)
    label_array = np.asarray(labels)
    colors = ["#0b7285", "#e8590c", "#2b8a3e", "#c92a2a", "#6741d9", "#495057"]

    fig, ax = plt.subplots(figsize=(8, 6))
    for cluster_id in sorted(set(labels)):
        mask = label_array == cluster_id
        color = colors[cluster_id % len(colors)]
        ax.scatter(
            coords[mask, 0],
            coords[mask, 1],
            alpha=0.7,
            color=color,
            label=f"Cluster {cluster_id}",
        )
        ax.scatter(
            float(coords[mask, 0].mean()),
            float(coords[mask, 1].mean()),
            marker="x",
            s=140,
            color=color,
        )

    ax.set_title(f"Cluster plot for workload {workload_id}")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.legend(loc="best")
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue(), {
        "plot_kind": plot_kind,
        "point_count": int(len(labels)),
        "cluster_count": int(len(set(labels))),
    }


@celery_app.task(name="app.tasks.kmeans_cluster")
def kmeans_cluster(
    points: list[list[float]],
    n_clusters: int = 3,
    random_state: int = 42,
) -> dict:
    """Run KMeans in the worker container and return JSON-safe results."""
    if not points:
        raise ValueError("points must not be empty")
    if n_clusters < 1:
        raise ValueError("n_clusters must be at least 1")

    model = KMeans(n_clusters=n_clusters, n_init=10, random_state=random_state)
    labels = model.fit_predict(points)
    label_list = [int(label) for label in labels.tolist()]
    cluster_sizes = {
        str(cluster_id): count
        for cluster_id, count in sorted(Counter(label_list).items())
    }

    return {
        "labels": label_list,
        "cluster_centers": model.cluster_centers_.tolist(),
        "cluster_sizes": cluster_sizes,
        "inertia": float(model.inertia_),
        "n_iter": int(model.n_iter_),
    }


@celery_app.task(name="app.tasks.spark_dot_product")
def spark_dot_product(
    left: list[float],
    right: list[float],
    partitions: int | None = None,
) -> dict:
    """Run a simple PySpark job inside the worker container."""
    if len(left) != len(right):
        raise ValueError("left and right must have the same length")
    if not left:
        raise ValueError("vectors must not be empty")

    spark = _build_spark_session("dotproduct-spark-dot-product")
    try:
        spark_context = spark.sparkContext
        num_slices = partitions or max(1, min(len(left), spark_context.defaultParallelism))
        dot_product = (
            spark_context.parallelize(list(zip(left, right)), numSlices=num_slices)
            .map(lambda pair: float(pair[0]) * float(pair[1]))
            .sum()
        )

        return {
            "dot_product": float(dot_product),
            "vector_length": len(left),
            "partitions": int(num_slices),
        }
    finally:
        spark.stop()


@celery_app.task(name="app.tasks.run_weaviate_cluster_workload")
def run_weaviate_cluster_workload(workload_id: str) -> dict:
    """Execute a queued cluster workload using vectors recorded in SQLite."""
    store = DotproductStore()
    workload = store.get_workload(workload_id)
    members = store.get_workload_members(workload_id)
    points = []
    for member in members:
        vector = member["vector"]
        if isinstance(vector, dict):
            vector = vector.get("default") or next(iter(vector.values()), None)
        if vector is not None:
            points.append((member["uuid"], vector))
    if len(points) < 2:
        store.set_workload_status(workload_id, "failed")
        raise ValueError("At least two stored vectors are required to cluster a workload")

    requested_k = int(workload["params"].get("k", 3))
    n_clusters = max(1, min(requested_k, len(points)))
    should_plot = bool(workload["params"].get("plot", True))

    store.set_workload_status(workload_id, "running")
    model = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    vectors = [vector for _, vector in points]
    labels = model.fit_predict(vectors).tolist()

    assignments = [(uuid, int(label), None) for (uuid, _), label in zip(points, labels)]
    store.replace_cluster_results(workload_id, assignments)
    plot_artifact = None
    plot_error = None
    if should_plot:
        try:
            plot_bytes, plot_metadata = _build_cluster_plot_png(
                workload_id=workload_id,
                vectors=vectors,
                labels=[int(label) for label in labels],
            )
            store.upsert_workload_artifact(
                workload_id=workload_id,
                artifact_type="cluster_plot",
                mime_type="image/png",
                artifact_blob=plot_bytes,
                metadata=plot_metadata,
            )
            plot_artifact = {
                "artifact_type": "cluster_plot",
                "mime_type": "image/png",
                "metadata": plot_metadata,
            }
        except Exception as exc:
            plot_error = str(exc)
    store.set_workload_status(workload_id, "completed")

    cluster_sizes = {
        str(cluster_id): count
        for cluster_id, count in sorted(Counter(int(label) for label in labels).items())
    }
    return {
        "workload_id": workload_id,
        "algorithm": workload["algorithm"],
        "cluster_sizes": cluster_sizes,
        "n_clusters": n_clusters,
        "plot_artifact": plot_artifact,
        "plot_error": plot_error,
    }
