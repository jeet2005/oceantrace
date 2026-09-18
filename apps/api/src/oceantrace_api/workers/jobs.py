from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from oceantrace_api.db import get_session
from oceantrace_api.db_models import JobRecordRow
from oceantrace_api.services.pipeline_service import InvestigationPipelineService
from oceantrace_common.models import InvestigationRequest


def run_investigation_job(case_number: str, request_dict: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Background job to run a full investigation pipeline."""
    from sqlalchemy import select

    with get_session() as session:
        # Update job status to running
        job = session.execute(
            select(JobRecordRow).where(JobRecordRow.id == UUID(job_id))
        ).scalar_one_or_none()
        if job:
            job.status = "running"
            job.updated_at = datetime.now(tz=UTC)
            session.commit()

    try:
        request = InvestigationRequest(**request_dict)
        result = InvestigationPipelineService().run_investigation(request)

        with get_session() as session:
            job = session.execute(
                select(JobRecordRow).where(JobRecordRow.id == UUID(job_id))
            ).scalar_one_or_none()
            if job:
                job.status = "complete"
                job.case_id = result.case.id
                job.detail = "Investigation completed successfully"
                job.completed_at = datetime.now(tz=UTC)
                job.updated_at = datetime.now(tz=UTC)
                session.commit()

        return {"case_id": str(result.case.id), "status": "complete"}

    except Exception as e:
        with get_session() as session:
            job = session.execute(
                select(JobRecordRow).where(JobRecordRow.id == UUID(job_id))
            ).scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error = str(e)
                job.detail = f"Investigation failed: {e}"
                job.completed_at = datetime.now(tz=UTC)
                job.updated_at = datetime.now(tz=UTC)
                session.commit()
        raise


def run_demo_investigation_job(case_number: str, job_id: str) -> dict[str, Any]:
    """Background job to run demo investigation."""
    from sqlalchemy import select

    with get_session() as session:
        job = session.execute(
            select(JobRecordRow).where(JobRecordRow.id == UUID(job_id))
        ).scalar_one_or_none()
        if job:
            job.status = "running"
            job.updated_at = datetime.now(tz=UTC)
            session.commit()

    try:
        result = InvestigationPipelineService().run_demo(case_number)

        with get_session() as session:
            job = session.execute(
                select(JobRecordRow).where(JobRecordRow.id == UUID(job_id))
            ).scalar_one_or_none()
            if job:
                job.status = "complete"
                job.case_id = result.case.id
                job.detail = "Demo investigation completed"
                job.completed_at = datetime.now(tz=UTC)
                job.updated_at = datetime.now(tz=UTC)
                session.commit()

        return {"case_id": str(result.case.id), "status": "complete"}

    except Exception as e:
        with get_session() as session:
            job = session.execute(
                select(JobRecordRow).where(JobRecordRow.id == UUID(job_id))
            ).scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error = str(e)
                job.detail = f"Demo investigation failed: {e}"
                job.completed_at = datetime.now(tz=UTC)
                job.updated_at = datetime.now(tz=UTC)
                session.commit()
        raise