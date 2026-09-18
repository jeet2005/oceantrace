from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException
from oceantrace_common.models import (
    AISDataset,
    InvestigationCase,
    InvestigationReport,
    InvestigationRequest,
    InvestigationResult,
    SatelliteObservation,
)
from pydantic import BaseModel, Field

from oceantrace_api.pipeline import build_demo_investigation
from oceantrace_api.services.ais_ingestion import AISCsvIngestionService
from oceantrace_api.services.observation_ingestion import SatelliteObservationIngestionService
from oceantrace_api.services.pipeline_service import InvestigationPipelineService
from oceantrace_api.storage.jobs import JobRecordResponse, create_job, get_job, job_queue
from oceantrace_api.storage.repository import repository

router = APIRouter()


class CreateInvestigationRequest(BaseModel):
    case_number: str = Field(pattern=r"^OT-\d{4}-\d{4}$", examples=["OT-2026-0001"])


class RegisterObservationRequest(BaseModel):
    metadata_path: str = Field(examples=["data/raw/sentinel_observation.json"])


class IngestAISRequest(BaseModel):
    csv_path: str = Field(examples=["data/raw/ais.csv"])


class AskInvestigationRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AskInvestigationResponse(BaseModel):
    answer: str
    evidence_ids: list[str]


class RunInvestigationAsyncRequest(BaseModel):
    case_number: str = Field(pattern=r"^OT-\d{4}-\d{4}$", examples=["OT-2026-0001"])
    observation: SatelliteObservation
    ais_dataset: AISDataset | None = None


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "oceantrace-api"}


@router.post("/investigations", response_model=InvestigationCase)
def create_investigation(payload: CreateInvestigationRequest) -> InvestigationCase:
    result = InvestigationPipelineService().run_demo(payload.case_number)
    repository.save(result)
    return result.case


@router.post("/investigations/run", response_model=InvestigationResult)
def run_investigation(payload: InvestigationRequest) -> InvestigationResult:
    result = InvestigationPipelineService().run_investigation(payload)
    return repository.save(result)


@router.post("/investigations/run-async", response_model=JobRecordResponse)
def run_investigation_async(payload: RunInvestigationAsyncRequest) -> JobRecordResponse:
    """Enqueue investigation for background processing."""
    request_dict = payload.model_dump(mode="json")
    job = create_job(f"Investigation for {payload.case_number}")
    job_queue.enqueue(
        "oceantrace_api.workers.jobs.run_investigation_job",
        payload.case_number,
        request_dict,
        str(job.id),
        detail=f"Investigation for {payload.case_number}",
    )
    return job


@router.post("/satellite-observations", response_model=SatelliteObservation)
def register_satellite_observation(payload: RegisterObservationRequest) -> SatelliteObservation:
    return SatelliteObservationIngestionService().load_metadata(Path(payload.metadata_path))


@router.post("/ais/datasets", response_model=AISDataset)
def ingest_ais_dataset(payload: IngestAISRequest) -> AISDataset:
    return AISCsvIngestionService().load_csv(Path(payload.csv_path))


@router.post("/dev/fixtures/investigations", response_model=InvestigationResult)
def run_demo_investigation() -> InvestigationResult:
    result = build_demo_investigation()
    return repository.save(result)


@router.post("/dev/fixtures/investigations/jobs", response_model=JobRecordResponse)
def run_demo_job() -> JobRecordResponse:
    # Create job record first so we have a job_id to pass to the worker
    job = create_job("Run deterministic fixture investigation pipeline.")
    job_queue.enqueue(
        "oceantrace_api.workers.jobs.run_demo_investigation_job",
        "OT-2026-0001",
        str(job.id),
        detail="Run deterministic fixture investigation pipeline.",
    )
    # Refresh job status after synchronous execution in test environment
    updated_job = get_job(job.id)
    return updated_job or job


@router.get("/dev/fixtures/investigations", response_model=InvestigationResult)
def get_demo_investigation() -> InvestigationResult:
    result = build_demo_investigation()
    return repository.save(result)


@router.get("/investigations", response_model=list[InvestigationCase])
def list_investigations() -> list[InvestigationCase]:
    return [result.case for result in repository.list()]


@router.get("/investigations/{case_id}", response_model=InvestigationResult)
def get_investigation(case_id: UUID) -> InvestigationResult:
    result = repository.get(case_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Investigation case not found.")
    return result


@router.get("/investigations/{case_id}/report", response_model=InvestigationReport)
def get_report(case_id: UUID) -> InvestigationReport:
    result = repository.get(case_id)
    if result is None or result.case.report is None:
        raise HTTPException(status_code=404, detail="Investigation report not found.")
    return result.case.report


@router.get("/investigations/{case_id}/candidates/{mmsi}")
def get_candidate(case_id: UUID, mmsi: str) -> dict[str, object]:
    result = repository.get(case_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Investigation case not found.")
    candidate = next((item for item in result.case.candidates if item.mmsi == mmsi), None)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate vessel not found.")
    evidence = [item for item in result.case.evidence if item.id in candidate.evidence_ids]
    return {"candidate": candidate, "evidence": evidence}


@router.post("/investigations/{case_id}/ask", response_model=AskInvestigationResponse)
def ask_investigation(case_id: UUID, payload: AskInvestigationRequest) -> AskInvestigationResponse:
    result = repository.get(case_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Investigation case not found.")
    terms = {term.lower() for term in payload.question.split() if len(term) > 3}
    matches = [
        evidence
        for evidence in result.case.evidence
        if terms & set((evidence.title + " " + evidence.excerpt).lower().split())
    ]
    if not matches:
        matches = result.case.evidence[:2]
    answer = (
        "Based on the available case evidence, this prototype can explain ranking, drift, "
        "and uncertainty, but it does not assert legal responsibility. "
        f"Relevant evidence: {', '.join(item.id for item in matches)}."
    )
    return AskInvestigationResponse(answer=answer, evidence_ids=[item.id for item in matches])


@router.get("/jobs/{job_id}", response_model=JobRecordResponse)
def get_job_endpoint(job_id: UUID) -> JobRecordResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("/evaluations")
def evaluations() -> dict[str, object]:
    return {
        "updated_at": datetime.now(tz=UTC),
        "metrics": [
            {"name": "synthetic_top_1", "value": 1.0, "scope": "single deterministic demo fixture"},
            {
                "name": "synthetic_top_3_recall",
                "value": 1.0,
                "scope": "single deterministic demo fixture",
            },
        ],
        "note": (
            "Demo metrics are from one synthetic fixture only and are not scientific "
            "performance claims."
        ),
    }