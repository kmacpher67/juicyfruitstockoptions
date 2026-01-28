from enum import Enum
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Job(BaseModel):
    id: str
    status: JobStatus
    created_at: datetime
    result: Optional[Any] = None
    error: Optional[str] = None

# In-memory storage (Note: Will be reset on container restart)
# For persistence, we would use Redis or Mongo, but for this single-user app memory is fine.
current_jobs: Dict[str, Job] = {}

def create_job() -> Job:
    job_id = str(uuid4())
    job = Job(id=job_id, status=JobStatus.QUEUED, created_at=datetime.utcnow())
    current_jobs[job_id] = job
    return job

def get_job(job_id: str) -> Optional[Job]:
    return current_jobs.get(job_id)

def update_job_status(job_id: str, status: JobStatus, result: Any = None, error: str = None):
    if job_id in current_jobs:
        job = current_jobs[job_id]
        job.status = status
        if result:
            job.result = result
        if error:
            job.error = error
        current_jobs[job_id] = job
