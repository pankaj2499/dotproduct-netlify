# Dotproduct: Jupyter, Weaviate, SQLite, and Worker Workloads

This setup gives you:

- A `notebook` container running JupyterLab
- A `worker` container running Celery
- A `redis` container acting as the queue and result backend
- A `weaviate` container for local vector search

The notebook container does **not** execute the job itself. It submits the job to Redis, and the worker container picks it up and runs it.

## Start the stack

```bash
docker compose up --build
```

If you want the OpenAI cookbook clustering notebook to call the OpenAI API for optional cluster naming, export your API key before starting the stack:

```bash
export OPENAI_API_KEY=your_key_here
docker compose up --build
```

Open JupyterLab at:

```text
http://localhost:8888/lab?token=devtoken
```

Weaviate is available at:

```text
http://localhost:8080
```

## Submit a job from a notebook

In a notebook cell:

```python
from app.tasks import long_running_sum

job = long_running_sum.delay([1, 2, 3, 4], delay_seconds=10)
job.id
```

Check job state:

```python
job.status
```

Wait for completion and fetch the result:

```python
job.get(timeout=30)
```

Expected result:

```python
10
```

## Use the patched local Weaviate client

The repo vendors and patches the official Python client so you can connect to the local Weaviate service and call collection-level workload helpers:

```python
import weaviate
from weaviate.classes.config import Configure, Property, DataType

client = weaviate.connect_to_dotproduct_local()
demo_docs = client.collections.use("DemoDocs")
if not demo_docs.exists():
    client.collections.create(
        name="DemoDocs",
        properties=[
            Property(name="title", data_type=DataType.TEXT),
            Property(name="body", data_type=DataType.TEXT),
        ],
        vector_config=Configure.Vectors.self_provided(),
    )
```

Insert records through the patched `collection.insert(...)`. This writes to Weaviate and also records properties, metadata, and the vector in SQLite at `/workspace/.data/dotproduct.sqlite3`.

```python
docs = client.collections.use("DemoDocs")

docs.insert(
    properties={"title": "Alpha", "body": "first cluster"},
    vector=[1.0, 1.0, 0.0],
    metadata={"source": "notebook", "tag": "demo"},
)

docs.insert(
    properties={"title": "Beta", "body": "first cluster neighbor"},
    vector=[0.9, 1.1, 0.1],
    metadata={"source": "notebook", "tag": "demo"},
)

docs.insert(
    properties={"title": "Gamma", "body": "second cluster"},
    vector=[8.0, 8.0, 0.0],
    metadata={"source": "notebook", "tag": "demo"},
)
```

Run `collection.cluster(...)` to search Weaviate for candidate objects, store the returned UUID list in SQLite, and enqueue clustering in the worker:

```python
submission = docs.cluster(
    near_vector=[1.0, 1.0, 0.0],
    limit=3,
    params={"k": 2},
)
submission
```

Example return:

```python
ClusterSubmission(
    workload_id="...",
    task_id="...",
    collection="DemoDocs",
    uuids=["...", "...", "..."],
    status="queued",
)
```

The executor task stores results back in SQLite in the `cluster_results` table. It also stores a PNG cluster plot in the `workload_artifacts` table as an `image/png` blob, which the notebook can fetch and display directly from the database.

## OpenAI cookbook clustering notebook

A notebook adapted from the OpenAI clustering cookbook is available at [`notebooks/openai_cookbook_clustering.ipynb`](/Users/sourabhdattawad/cursor/dotproduct/notebooks/openai_cookbook_clustering.ipynb).

It does two things:

- Loads the downloaded dataset at `/workspace/data/fine_food_reviews_with_embeddings_1k.csv`, which already contains embeddings in the `embedding` column, and runs local KMeans clustering plus t-SNE.
- Pushes a balanced subset of those embedded reviews into local Weaviate and uses `collection.cluster(...)` to send the clustering workload to the worker container.

If `OPENAI_API_KEY` is not set, the notebook still runs completely because the embeddings are already present in the CSV. The key is only used for optional cluster naming.

## PySpark job example

This project can also run PySpark jobs inside the worker container. This uses Spark in `local[*]` mode inside that container, not a separate Spark cluster.

In a notebook cell:

```python
from app.tasks import spark_dot_product

job = spark_dot_product.delay([1, 2, 3], [4, 5, 6])
job.id
```

Fetch the result:

```python
job.get(timeout=60)
```

Expected result:

```python
{
    "dot_product": 32.0,
    "vector_length": 3,
    "partitions": 3,
}
```

## Clustering job example

In a notebook cell:

```python
from app.tasks import kmeans_cluster

points = [
    [1.0, 1.1],
    [0.9, 1.0],
    [1.1, 0.8],
    [8.0, 8.1],
    [7.8, 7.9],
    [8.2, 8.3],
    [0.0, 8.0],
    [0.2, 7.8],
    [-0.1, 8.2],
]

job = kmeans_cluster.delay(points, n_clusters=3)
job.id
```

Fetch the worker result:

```python
result = job.get(timeout=30)
result
```

Example result shape:

```python
{
    "labels": [2, 2, 2, 0, 0, 0, 1, 1, 1],
    "cluster_centers": [[8.0, 8.1], [0.03, 8.0], [1.0, 0.97]],
    "cluster_sizes": {"0": 3, "1": 3, "2": 3},
    "inertia": 0.20666666666666658,
    "n_iter": 2,
}
```

## Why this works

- The notebook container acts as a client only.
- The worker container runs `celery worker` and executes tasks.
- Redis carries the task and stores the result.

## Notes

- Put shared task definitions in [`app/tasks.py`](/Users/sourabhdattawad/cursor/dotproduct/app/tasks.py).
- The patched client source lives in [`vendor/weaviate-python-client`](/Users/sourabhdattawad/cursor/dotproduct/vendor/weaviate-python-client).
- If you want GPU or custom system packages, add them to the worker image in [`Dockerfile`](/Users/sourabhdattawad/cursor/dotproduct/Dockerfile).
- If you want a real multi-container Spark cluster with Spark master and Spark workers, that is a different setup from the current Celery worker model.
- If you want the *entire notebook kernel* to run in another container, that is a different design. In that case use Jupyter remote kernels or Jupyter Enterprise Gateway instead of Celery.
