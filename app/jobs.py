from enum import Enum
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timezone
from pydantic import BaseModel

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Job(BaseModel):
    id: str
    job_type: str = "generic"
    name: str = "job"
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    heartbeat_at: Optional[datetime] = None
    message: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None

# In-memory storage (Note: Will be reset on container restart)
# For persistence, we would use Redis or Mongo, but for this single-user app memory is fine.
current_jobs: Dict[str, Job] = {}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_job(job_type: str = "generic", name: str = "job") -> Job:
    job_id = str(uuid4())
    job = Job(
        id=job_id,
        job_type=job_type,
        name=name,
        status=JobStatus.QUEUED,
        created_at=_utc_now(),
        message="queued",
    )
    current_jobs[job_id] = job
    return job

def get_job(job_id: str) -> Optional[Job]:
    return current_jobs.get(job_id)

def update_job_status(job_id: str, status: JobStatus, result: Any = None, error: str = None, message: str | None = None):
    if job_id in current_jobs:
        job = current_jobs[job_id]
        job.status = status
        if status == JobStatus.RUNNING:
            job.started_at = job.started_at or _utc_now()
            job.heartbeat_at = _utc_now()
        if status in {JobStatus.COMPLETED, JobStatus.FAILED}:
            job.finished_at = _utc_now()
            job.heartbeat_at = _utc_now()
        if result:
            job.result = result
        if error:
            job.error = error
        if message is not None:
            job.message = message
        current_jobs[job_id] = job


def touch_job(job_id: str, message: str | None = None):
    if job_id not in current_jobs:
        return
    job = current_jobs[job_id]
    job.heartbeat_at = _utc_now()
    if message is not None:
        job.message = message
    current_jobs[job_id] = job


def list_jobs(job_type: str | None = None):
    jobs = list(current_jobs.values())
    if job_type:
        jobs = [job for job in jobs if job.job_type == job_type]
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return jobs


def get_latest_job(job_type: str | None = None) -> Optional[Job]:
    jobs = list_jobs(job_type=job_type)
    return jobs[0] if jobs else None
