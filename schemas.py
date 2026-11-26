from typing import Optional

from pydantic import BaseModel


class JobCreated(BaseModel):
    job_id: str
    task: str
    status: str


class JobStatus(BaseModel):
    job_id: str
    task: str
    status: str  # queued | processing | completed | failed
    queue_ms: Optional[float] = None  # time spent waiting in the queue
    result: Optional[dict] = None
    error: Optional[str] = None
