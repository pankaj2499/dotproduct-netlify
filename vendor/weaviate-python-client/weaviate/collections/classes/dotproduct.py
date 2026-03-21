from dataclasses import dataclass
from typing import Optional


@dataclass
class ClusterSubmission:
    workload_id: str
    task_id: Optional[str]
    collection: str
    uuids: list[str]
    status: str
