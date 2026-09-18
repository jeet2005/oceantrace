from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import redis
from oceantrace_api.storage.job_queue import JobQueue, JobRecord, JobStatus
from oceantrace_common.config import settings
from rq import Queue
from rq.job import Job as RQJob


class RQJobQueue(JobQueue):
    def __init__(self) -> None:
        self._redis = redis.from_url(settings.redis_url)
        self._queue = Queue(connection=self._redis)

    def enqueue(self, func: str, *args: Any, **kwargs: Any) -> JobRecord:
        # Import the function dynamically
        module_path, func_name = func.rsplit(".", 1)
        module = __import__(module_path, fromlist=[func_name])
        func_obj = getattr(module, func_name)

        rq_job = self._queue.enqueue(func_obj, *args, **kwargs)
        return JobRecord(
            id=UUID(rq_job.id),
            status=JobStatus.QUEUED,
            detail=kwargs.get("detail", ""),
        )

    def get_job(self, job_id: UUID) -> JobRecord | None:
        try:
            rq_job = RQJob.fetch(str(job_id), connection=self._redis)
        except Exception:
            return None

        status_map = {
            "queued": JobStatus.QUEUED,
            "started": JobStatus.RUNNING,
            "finished": JobStatus.COMPLETE,
            "failed": JobStatus.FAILED,
            "deferred": JobStatus.QUEUED,
            "scheduled": JobStatus.QUEUED,
        }

        created_at = rq_job.created_at
        ended_at = rq_job.ended_at
        return JobRecord(
            id=UUID(rq_job.id),
            status=status_map.get(rq_job.get_status(), JobStatus.QUEUED),
            case_id=(
                UUID(rq_job.result["case_id"])
                if rq_job.result
                and isinstance(rq_job.result, dict)
                and "case_id" in rq_job.result
                else None
            ),
            created_at=(
                datetime.fromtimestamp(created_at.timestamp(), tz=UTC) if created_at else None
            ),
            updated_at=(
                datetime.fromtimestamp(ended_at.timestamp(), tz=UTC) if ended_at else None
            ),
            detail=rq_job.description or "",
            error=rq_job.exc_info if rq_job.is_failed else None,
        )

    def update_job(
        self,
        job_id: UUID,
        status: JobStatus | None = None,
        case_id: UUID | None = None,
        detail: str | None = None,
        error: str | None = None,
    ) -> JobRecord | None:
        # RQ doesn't support manual status updates easily; job status is managed by workers
        # This is a no-op for RQ; status is derived from job state
        return self.get_job(job_id)