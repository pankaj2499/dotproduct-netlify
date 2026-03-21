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
        self.submission_platform = os.getenv("DOTPRODUCT_SUBMISSION_PLATFORM", "jupyter-notebook")
        self.runtime_platform = os.getenv("DOTPRODUCT_RUNTIME_PLATFORM", "celery-worker+scikit-learn")


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
            self._ensure_column(conn, "workloads", "started_at", "TEXT")
            self._ensure_column(conn, "workloads", "completed_at", "TEXT")
            self._ensure_column(conn, "workloads", "wall_time_ms", "INTEGER")
            self._ensure_column(conn, "workloads", "cpu_time_ms", "INTEGER")
            self._ensure_column(conn, "workloads", "rss_before_bytes", "INTEGER")
            self._ensure_column(conn, "workloads", "rss_after_bytes", "INTEGER")
            self._ensure_column(conn, "workloads", "rss_peak_bytes", "INTEGER")
            self._ensure_column(conn, "workloads", "error_message", "TEXT")
            self._ensure_column(conn, "workloads", "result_json", "TEXT")
            self._ensure_column(conn, "workloads", "submission_platform", "TEXT")
            self._ensure_column(conn, "workloads", "runtime_platform", "TEXT")
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workloads_status_created_at
                ON workloads(status, created_at DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workloads_collection_created_at
                ON workloads(collection, created_at DESC)
                """
            )

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_type: str,
    ) -> None:
        columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        if any(column["name"] == column_name for column in columns):
            return
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

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
        submission_platform: Optional[str] = None,
        runtime_platform: Optional[str] = None,
    ) -> str:
        workload_id = str(uuid_package.uuid4())
        now = _utcnow()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workloads (
                    workload_id, collection, tenant, kind, algorithm, params_json, query_json,
                    status, executor_task_id, created_at, updated_at, submission_platform, runtime_platform
                ) VALUES (?, ?, ?, 'cluster', ?, ?, ?, 'queued', NULL, ?, ?, ?, ?)
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
                    submission_platform,
                    runtime_platform,
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

    def mark_workload_running(
        self,
        workload_id: str,
        *,
        started_at: Optional[str] = None,
        rss_before_bytes: Optional[int] = None,
    ) -> None:
        now = _utcnow()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workloads
                SET status = 'running',
                    started_at = COALESCE(started_at, ?),
                    rss_before_bytes = COALESCE(?, rss_before_bytes),
                    updated_at = ?
                WHERE workload_id = ?
                """,
                (started_at or now, rss_before_bytes, now, workload_id),
            )

    def complete_workload(
        self,
        workload_id: str,
        *,
        status: str,
        completed_at: Optional[str] = None,
        metrics: Optional[Mapping[str, Any]] = None,
        result: Optional[Mapping[str, Any]] = None,
        error_message: Optional[str] = None,
        runtime_platform: Optional[str] = None,
    ) -> None:
        now = _utcnow()
        metrics = dict(metrics or {})
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workloads
                SET status = ?,
                    completed_at = ?,
                    wall_time_ms = ?,
                    cpu_time_ms = ?,
                    rss_before_bytes = COALESCE(?, rss_before_bytes),
                    rss_after_bytes = ?,
                    rss_peak_bytes = ?,
                    error_message = ?,
                    result_json = ?,
                    runtime_platform = COALESCE(?, runtime_platform),
                    updated_at = ?
                WHERE workload_id = ?
                """,
                (
                    status,
                    completed_at or now,
                    metrics.get("wall_time_ms"),
                    metrics.get("cpu_time_ms"),
                    metrics.get("rss_before_bytes"),
                    metrics.get("rss_after_bytes"),
                    metrics.get("rss_peak_bytes"),
                    error_message,
                    json.dumps(result) if result is not None else None,
                    runtime_platform,
                    now,
                    workload_id,
                ),
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
        result_json = result.pop("result_json")
        result["result"] = json.loads(result_json) if result_json else None
        return result

    def list_workloads(
        self,
        *,
        limit: int = 100,
        statuses: Optional[Sequence[str]] = None,
        collections: Optional[Sequence[str]] = None,
    ) -> list[dict[str, Any]]:
        filters: list[str] = []
        values: list[Any] = []
        if statuses:
            filters.append(f"w.status IN ({','.join('?' for _ in statuses)})")
            values.extend(statuses)
        if collections:
            filters.append(f"w.collection IN ({','.join('?' for _ in collections)})")
            values.extend(collections)

        where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
        query = f"""
            SELECT
                w.*,
                (
                    SELECT COUNT(*)
                    FROM workload_members wm
                    WHERE wm.workload_id = w.workload_id
                ) AS member_count,
                (
                    SELECT COUNT(*)
                    FROM cluster_results cr
                    WHERE cr.workload_id = w.workload_id
                ) AS result_count,
                EXISTS(
                    SELECT 1
                    FROM workload_artifacts wa
                    WHERE wa.workload_id = w.workload_id
                      AND wa.artifact_type = 'cluster_plot'
                ) AS has_cluster_plot
            FROM workloads w
            {where_sql}
            ORDER BY w.created_at DESC
            LIMIT ?
        """
        values.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, values).fetchall()

        workloads: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["params"] = json.loads(item.pop("params_json"))
            item["query"] = json.loads(item.pop("query_json"))
            result_json = item.pop("result_json")
            item["result"] = json.loads(result_json) if result_json else None
            workloads.append(item)
        return workloads

    def summarize_workloads(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_workloads,
                    SUM(CASE WHEN status = 'queued' THEN 1 ELSE 0 END) AS queued_workloads,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS running_workloads,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_workloads,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_workloads,
                    AVG(wall_time_ms) AS avg_wall_time_ms,
                    AVG(cpu_time_ms) AS avg_cpu_time_ms,
                    AVG(
                        CASE
                            WHEN rss_after_bytes IS NOT NULL AND rss_before_bytes IS NOT NULL
                            THEN rss_after_bytes - rss_before_bytes
                            ELSE NULL
                        END
                    ) AS avg_rss_delta_bytes
                FROM workloads
                """
            ).fetchone()
        return dict(row) if row is not None else {}

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
