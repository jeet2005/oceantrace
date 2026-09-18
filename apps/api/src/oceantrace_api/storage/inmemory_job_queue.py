from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from oceantrace_api.pipeline import build_demo_investigation
from oceantrace_api.storage.job_queue import JobQueue, JobRecord, JobStatus
from oceantrace_api.storage.repository import repository


class InMemoryJobQueue(JobQueue):
    """In-memory job queue for testing and development without Redis."""

    def __init__(self) -> None:
        self._jobs: dict[UUID, JobRecord] = {}

    def enqueue(self, func: str, *args: Any, **kwargs: Any) -> JobRecord:
        # Extract job_id from args if provided (second argument after func)
        # The route passes: func, case_number, job_id, detail=...
        job_id = None
        if len(args) >= 2:
            try:
                job_id = UUID(args[1])
            except (ValueError, TypeError):
                pass

        if job_id is None:
            job_id = uuid4()

        # For testing, run the demo investigation synchronously and save to repository
        try:
            result = build_demo_investigation()
            repository.save(result)
            job = JobRecord(
                id=job_id,
                status=JobStatus.COMPLETE,
                case_id=result.case.id,
                detail=kwargs.get("detail", ""),
            )
        except Exception as e:
            job = JobRecord(
                id=job_id,
                status=JobStatus.FAILED,
                detail=kwargs.get("detail", ""),
                error=str(e),
            )

        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: UUID) -> JobRecord | None:
        return self._jobs.get(job_id)

    def update_job(
        self,
        job_id: UUID,
        status: JobStatus | None = None,
        case_id: UUID | None = None,
        detail: str | None = None,
        error: str | None = None,
    ) -> JobRecord | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        if status is not None:
            job.status = status
        if case_id is not None:
            job.case_id = case_id
        if detail is not None:
            job.detail = detail
        if error is not None:
            job.error = error
        job.updated_at = datetime.now(tz=UTC)
        return job