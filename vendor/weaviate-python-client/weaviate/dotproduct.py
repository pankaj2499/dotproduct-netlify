import json
import os
import sqlite3
import uuid as uuid_package
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from celery import Celery


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkloadSubmission:
    workload_id: str
    task_id: Optional[str]
    collection: str
    uuids: list[str]
    status: str


class DotproductSettings:
    def __init__(self) -> None:
        self.metadata_db = os.getenv("DOTPRODUCT_METADATA_DB", "/workspace/.data/dotproduct.sqlite3")
        self.cluster_task_name = os.getenv(
            "DOTPRODUCT_CLUSTER_TASK_NAME", "app.tasks.run_weaviate_cluster_workload"
        )
        self.celery_broker_url = os.getenv(
            "DOTPRODUCT_CELERY_BROKER_URL",
            os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
        )
        self.celery_result_backend = os.getenv(
            "DOTPRODUCT_CELERY_RESULT_BACKEND",
            os.getenv("CELERY_RESULT_BACKEND", self.celery_broker_url),
        )


class DotproductStore:
    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or DotproductSettings().metadata_db
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS objects (
                    uuid TEXT PRIMARY KEY,
                    collection TEXT NOT NULL,
                    tenant TEXT,
                    properties_json TEXT NOT NULL,
                    references_json TEXT,
                    metadata_json TEXT,
                    vector_json TEXT,
                    sync_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workloads (
                    workload_id TEXT PRIMARY KEY,
                    collection TEXT NOT NULL,
                    tenant TEXT,
                    kind TEXT NOT NULL,
                    algorithm TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    query_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    executor_task_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workload_members (
                    workload_id TEXT NOT NULL,
                    uuid TEXT NOT NULL,
                    rank_index INTEGER,
                    distance REAL,
                    PRIMARY KEY (workload_id, uuid),
                    FOREIGN KEY (workload_id) REFERENCES workloads(workload_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS cluster_results (
                    workload_id TEXT NOT NULL,
                    uuid TEXT NOT NULL,
                    cluster_id INTEGER NOT NULL,
                    score REAL,
                    PRIMARY KEY (workload_id, uuid),
                    FOREIGN KEY (workload_id) REFERENCES workloads(workload_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS workload_artifacts (
                    workload_id TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    artifact_blob BLOB NOT NULL,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (workload_id, artifact_type),
                    FOREIGN KEY (workload_id) REFERENCES workloads(workload_id) ON DELETE CASCADE
                );
                """
            )

    def upsert_object(
        self,
        *,
        uuid: str,
        collection: str,
        tenant: Optional[str],
        properties: Mapping[str, Any],
        references: Optional[Mapping[str, Any]],
        metadata: Optional[Mapping[str, Any]],
        vector: Optional[Any],
        sync_status: str,
    ) -> None:
        now = _utcnow()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO objects (
                    uuid, collection, tenant, properties_json, references_json,
                    metadata_json, vector_json, sync_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(uuid) DO UPDATE SET
                    collection=excluded.collection,
                    tenant=excluded.tenant,
                    properties_json=excluded.properties_json,
                    references_json=excluded.references_json,
                    metadata_json=excluded.metadata_json,
                    vector_json=excluded.vector_json,
                    sync_status=excluded.sync_status,
                    updated_at=excluded.updated_at
                """,
                (
                    uuid,
                    collection,
                    tenant,
                    json.dumps(properties),
                    json.dumps(references) if references is not None else None,
                    json.dumps(metadata) if metadata is not None else None,
                    json.dumps(vector) if vector is not None else None,
                    sync_status,
                    now,
                    now,
                ),
            )

    def create_cluster_workload(
        self,
        *,
        collection: str,
        tenant: Optional[str],
        algorithm: str,
        params: Mapping[str, Any],
        query: Mapping[str, Any],
        members: Sequence[tuple[str, Optional[float]]],
    ) -> str:
        workload_id = str(uuid_package.uuid4())
        now = _utcnow()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workloads (
                    workload_id, collection, tenant, kind, algorithm, params_json, query_json,
                    status, executor_task_id, created_at, updated_at
                ) VALUES (?, ?, ?, 'cluster', ?, ?, ?, 'queued', NULL, ?, ?)
                """,
                (
                    workload_id,
                    collection,
                    tenant,
                    algorithm,
                    json.dumps(params),
                    json.dumps(query),
                    now,
                    now,
                ),
            )
            conn.executemany(
                """
                INSERT INTO workload_members (workload_id, uuid, rank_index, distance)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (workload_id, uuid, idx, distance)
                    for idx, (uuid, distance) in enumerate(members)
                ],
            )
        return workload_id

    def set_executor_task_id(self, workload_id: str, task_id: str) -> None:
        now = _utcnow()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workloads
                SET executor_task_id = ?, updated_at = ?
                WHERE workload_id = ?
                """,
                (task_id, now, workload_id),
            )

    def set_workload_status(self, workload_id: str, status: str) -> None:
        now = _utcnow()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workloads
                SET status = ?, updated_at = ?
                WHERE workload_id = ?
                """,
                (status, now, workload_id),
            )

    def get_workload(self, workload_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workloads WHERE workload_id = ?",
                (workload_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown workload_id: {workload_id}")
        result = dict(row)
        result["params"] = json.loads(result.pop("params_json"))
        result["query"] = json.loads(result.pop("query_json"))
        return result

    def get_workload_members(self, workload_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT wm.uuid, wm.rank_index, wm.distance, o.vector_json, o.properties_json, o.metadata_json
                FROM workload_members wm
                LEFT JOIN objects o ON o.uuid = wm.uuid
                WHERE wm.workload_id = ?
                ORDER BY wm.rank_index ASC
                """,
                (workload_id,),
            ).fetchall()
        return [
            {
                "uuid": row["uuid"],
                "rank_index": row["rank_index"],
                "distance": row["distance"],
                "vector": json.loads(row["vector_json"]) if row["vector_json"] else None,
                "properties": json.loads(row["properties_json"]) if row["properties_json"] else None,
                "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else None,
            }
            for row in rows
        ]

    def replace_cluster_results(
        self,
        workload_id: str,
        assignments: Iterable[tuple[str, int, Optional[float]]],
    ) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM cluster_results WHERE workload_id = ?", (workload_id,))
            conn.executemany(
                """
                INSERT INTO cluster_results (workload_id, uuid, cluster_id, score)
                VALUES (?, ?, ?, ?)
                """,
                [(workload_id, uuid, cluster_id, score) for uuid, cluster_id, score in assignments],
            )

    def get_cluster_results(self, workload_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT workload_id, uuid, cluster_id, score
                FROM cluster_results
                WHERE workload_id = ?
                ORDER BY cluster_id ASC, uuid ASC
                """,
                (workload_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_workload_artifact(
        self,
        *,
        workload_id: str,
        artifact_type: str,
        mime_type: str,
        artifact_blob: bytes,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        now = _utcnow()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workload_artifacts (
                    workload_id, artifact_type, mime_type, artifact_blob, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(workload_id, artifact_type) DO UPDATE SET
                    mime_type=excluded.mime_type,
                    artifact_blob=excluded.artifact_blob,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    workload_id,
                    artifact_type,
                    mime_type,
                    artifact_blob,
                    json.dumps(metadata) if metadata is not None else None,
                    now,
                    now,
                ),
            )

    def get_workload_artifact(self, workload_id: str, artifact_type: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT workload_id, artifact_type, mime_type, artifact_blob, metadata_json, created_at, updated_at
                FROM workload_artifacts
                WHERE workload_id = ? AND artifact_type = ?
                """,
                (workload_id, artifact_type),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown artifact for workload_id={workload_id!r}, artifact_type={artifact_type!r}")

        result = dict(row)
        result["metadata"] = json.loads(result.pop("metadata_json")) if result["metadata_json"] else None
        return result


def submit_cluster_workload(workload_id: str) -> Optional[str]:
    settings = DotproductSettings()
    app = Celery("dotproduct-workloads")
    app.conf.broker_url = settings.celery_broker_url
    app.conf.result_backend = settings.celery_result_backend
    result = app.send_task(settings.cluster_task_name, kwargs={"workload_id": workload_id})
    return result.id


def serialize_submission(submission: WorkloadSubmission) -> dict[str, Any]:
    return asdict(submission)
