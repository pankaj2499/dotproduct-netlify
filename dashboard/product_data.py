from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_DB_PATH = "/workspace/.data/dotproduct.sqlite3"


def _db_path() -> str:
    return os.getenv("DOTPRODUCT_METADATA_DB", DEFAULT_DB_PATH)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _vector_to_array(value: Any) -> np.ndarray | None:
    if value is None:
        return None
    vector = value
    if isinstance(vector, dict):
        vector = vector.get("default") or next(iter(vector.values()), None)
    if not isinstance(vector, list) or not vector:
        return None
    return np.asarray(vector, dtype=float)


def list_collections() -> list[str]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT collection
            FROM objects
            ORDER BY collection ASC
            """
        ).fetchall()
    return [str(row["collection"]) for row in rows]


def load_objects(collection: str | None, *, limit: int = 2000) -> pd.DataFrame:
    where_sql = ""
    values: list[Any] = []
    if collection:
        where_sql = "WHERE collection = ?"
        values.append(collection)

    values.append(limit)
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT uuid, collection, properties_json, metadata_json, vector_json
            FROM objects
            {where_sql}
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            values,
        ).fetchall()

    if not rows:
        return pd.DataFrame()

    records: list[dict[str, Any]] = []
    for row in rows:
        properties = json.loads(row["properties_json"]) if row["properties_json"] else {}
        metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        raw_vector = json.loads(row["vector_json"]) if row["vector_json"] else None
        vector = _vector_to_array(raw_vector)
        if vector is None:
            continue

        title = ""
        body = ""
        if isinstance(properties, dict):
            for key in ("title", "name", "summary"):
                value = properties.get(key)
                if isinstance(value, str) and value.strip():
                    title = value.strip()
                    break
            for key in ("body", "text", "description", "combined"):
                value = properties.get(key)
                if isinstance(value, str) and value.strip():
                    body = " ".join(value.split())
                    break

        records.append(
            {
                "uuid": str(row["uuid"]),
                "collection": str(row["collection"]),
                "properties": properties,
                "metadata": metadata,
                "title": title or "Untitled",
                "preview": (body[:180] + "...") if len(body) > 180 else body,
                "vector": vector,
                "vector_dim": int(vector.shape[0]),
            }
        )

    return pd.DataFrame(records)


def parse_vector_input(raw: str) -> np.ndarray:
    values = [segment.strip() for segment in raw.split(",") if segment.strip()]
    if not values:
        raise ValueError("Enter at least one vector component.")
    return np.asarray([float(value) for value in values], dtype=float)


def cosine_similarity_search(
    query_vector: np.ndarray,
    objects_df: pd.DataFrame,
    *,
    top_k: int,
) -> pd.DataFrame:
    if objects_df.empty:
        return pd.DataFrame()

    vectors = vectors_matrix(objects_df)
    if vectors.shape[1] != query_vector.shape[0]:
        raise ValueError(
            f"Vector dimension mismatch: query has {query_vector.shape[0]} values but objects use {vectors.shape[1]}."
        )

    q_norm = np.linalg.norm(query_vector)
    if q_norm == 0:
        raise ValueError("Query vector cannot be all zeros.")

    doc_norms = np.linalg.norm(vectors, axis=1)
    safe_norms = np.where(doc_norms == 0, 1e-12, doc_norms)
    scores = (vectors @ query_vector) / (safe_norms * q_norm)

    ranked_df = objects_df.copy()
    ranked_df["similarity"] = scores
    ranked_df = ranked_df.sort_values("similarity", ascending=False).head(top_k)
    return ranked_df.reset_index(drop=True)


def vectors_matrix(objects_df: pd.DataFrame) -> np.ndarray:
    rows = [np.asarray(vector, dtype=float) for vector in objects_df["vector"].tolist()]
    if not rows:
        return np.empty((0, 0), dtype=float)
    return np.asarray(rows, dtype=float)


def workload_snapshot(limit: int = 200) -> tuple[pd.DataFrame, dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                workload_id,
                collection,
                algorithm,
                status,
                created_at,
                wall_time_ms,
                cpu_time_ms,
                rss_before_bytes,
                rss_after_bytes,
                (SELECT COUNT(*) FROM workload_members wm WHERE wm.workload_id = w.workload_id) AS member_count
            FROM workloads w
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        summary_row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_workloads,
                SUM(CASE WHEN status = 'queued' THEN 1 ELSE 0 END) AS queued_workloads,
                SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS running_workloads,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_workloads,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_workloads,
                AVG(wall_time_ms) AS avg_wall_time_ms,
                AVG(cpu_time_ms) AS avg_cpu_time_ms
            FROM workloads
            """
        ).fetchone()

    df = pd.DataFrame([dict(row) for row in rows])
    summary = dict(summary_row) if summary_row else {}
    return df, summary
