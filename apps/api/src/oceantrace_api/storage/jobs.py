import os
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from oceantrace_api.storage.inmemory_job_queue import InMemoryJobQueue
from oceantrace_api.storage.job_queue import JobQueue, JobRecord, JobStatus
from pydantic import BaseModel


class _LazyJobQueue(JobQueue):
    """Lazy-initialized job queue that falls back to in-memory if Redis unavailable."""

    def __init__(self) -> None:
        self._queue: JobQueue | None = None

    def _get_queue(self) -> JobQueue:
        if self._queue is None:
            env = os.getenv("OT_ENVIRONMENT", "local")
            if env == "test":
                self._queue = InMemoryJobQueue()
            else:
                try:
                    from oceantrace_api.storage.rq_job_queue import RQJobQueue
                    self._queue = RQJobQueue()
                except Exception:
                    self._queue = InMemoryJobQueue()
        return self._queue

    def enqueue(self, func: str, *args: Any, **kwargs: Any) -> JobRecord:
        return self._get_queue().enqueue(func, *args, **kwargs)

    def get_job(self, job_id: UUID) -> JobRecord | None:
        return self._get_queue().get_job(job_id)

    def update_job(
        self,
        job_id: UUID,
        status: JobStatus | None = None,
        case_id: UUID | None = None,
        detail: str | None = None,
        error: str | None = None,
    ) -> JobRecord | None:
        return self._get_queue().update_job(job_id, status, case_id, detail, error)


job_queue: JobQueue = _LazyJobQueue()


class JobRecordResponse(BaseModel):
    id: UUID
    status: JobStatus
    case_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    detail: str
    error: str | None = None

    @classmethod
    def from_record(cls, record: JobRecord) -> "JobRecordResponse":
        return cls(
            id=record.id,
            status=record.status,
            case_id=record.case_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
            detail=record.detail,
            error=record.error,
        )


def create_job(detail: str) -> JobRecordResponse:
    """Create a new job (compatibility wrapper)."""
    job = JobRecord(
        id=uuid4(),
        status=JobStatus.QUEUED,
        detail=detail,
    )
    return JobRecordResponse.from_record(job)


def get_job(job_id: UUID) -> JobRecordResponse | None:
    """Get job by ID."""
    record = job_queue.get_job(job_id)
    if record is None:
        return None
    return JobRecordResponse.from_record(record)