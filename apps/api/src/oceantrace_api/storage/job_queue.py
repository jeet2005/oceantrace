from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class JobRecord:
    def __init__(
        self,
        id: UUID,
        status: JobStatus,
        case_id: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        detail: str = "",
        error: str | None = None,
    ) -> None:
        self.id = id
        self.status = status
        self.case_id = case_id
        self.created_at = created_at or datetime.now(tz=UTC)
        self.updated_at = updated_at or datetime.now(tz=UTC)
        self.detail = detail
        self.error = error


class JobQueue(ABC):
    @abstractmethod
    def enqueue(self, func: str, *args: Any, **kwargs: Any) -> JobRecord:
        """Enqueue a job for background execution."""
        ...

    @abstractmethod
    def get_job(self, job_id: UUID) -> JobRecord | None:
        """Get job status by ID."""
        ...

    @abstractmethod
    def update_job(
        self,
        job_id: UUID,
        status: JobStatus | None = None,
        case_id: UUID | None = None,
        detail: str | None = None,
        error: str | None = None,
    ) -> JobRecord | None:
        """Update job status."""
        ...