from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


class CaseStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class Geometry(BaseModel):
    type: str = Field(examples=["Polygon", "Point"])
    coordinates: list[Any]


class SatelliteObservation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    captured_at: datetime
    sensor: str
    source_uri: str
    bbox: tuple[float, float, float, float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpillGeometry(BaseModel):
    polygon: Geometry
    centroid: tuple[float, float]
    area_km2: float = Field(ge=0)
    perimeter_km: float = Field(ge=0)
    length_km: float | None = Field(default=None, ge=0)
    width_km: float | None = Field(default=None, ge=0)


class SpillDetection(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    observation_id: UUID
    confidence: float = Field(ge=0, le=1)
    uncertainty: str
    geometry: SpillGeometry
    estimated_age_hours: float | None = Field(default=None, ge=0)


class DriftSimulation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    detection_id: UUID
    mode: str = Field(pattern="^(forward|backward|monte_carlo)$")
    started_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    release_window_start: datetime | None = None
    release_window_end: datetime | None = None
    confidence: float = Field(default=0, ge=0, le=1)
    origin_region: Geometry | None = None
    forecast_corridor: Geometry | None = None
    trajectory_count: int = Field(default=0, ge=0)


class AISPoint(BaseModel):
    mmsi: str
    timestamp: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    sog: float | None = Field(default=None, ge=0)
    cog: float | None = Field(default=None, ge=0, le=360)
    heading: float | None = Field(default=None, ge=0, le=360)
    imo: str | None = None
    vessel_type: str | None = None

    @field_validator("mmsi")
    @classmethod
    def mmsi_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("mmsi must not be blank")
        return value.strip()


class VesselTrack(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    mmsi: str
    points: list[AISPoint]


class AISDataset(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_uri: str
    points: list[AISPoint]
    tracks: list[VesselTrack]
    rejected_rows: int = Field(default=0, ge=0)


class InvestigationRequest(BaseModel):
    case_number: str
    observation: SatelliteObservation
    ais_dataset: AISDataset | None = None


class CandidateScore(BaseModel):
    proximity: float = Field(ge=0, le=100)
    temporal_overlap: float = Field(ge=0, le=100)
    trajectory_consistency: float = Field(ge=0, le=100)
    drift_consistency: float = Field(ge=0, le=100)
    behavioral_anomaly: float = Field(ge=0, le=100)
    total: float = Field(ge=0, le=100)


class VesselCandidate(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    mmsi: str
    vessel_name: str | None = None
    score: CandidateScore
    explanation: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    disclaimer: str = "Investigative ranking only; not definitive attribution."


class Evidence(BaseModel):
    id: str
    source: str
    title: str
    reference: str | HttpUrl
    excerpt: str


class RAGDocument(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    source: str
    document_type: str
    jurisdiction: str | None = None
    version: str | None = None
    publication_date: datetime | None = None
    uri: str
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class InvestigationReport(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    case_id: UUID
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    executive_summary: str
    claims: list[dict[str, Any]]
    evidence_ids: list[str] = Field(default_factory=list)
    disclaimer: str = "Candidate vessels are ranked for investigation, not legal attribution."


class InvestigationCase(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    case_number: str
    status: CaseStatus = CaseStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    observation: SatelliteObservation | None = None
    detections: list[SpillDetection] = Field(default_factory=list)
    drift_simulations: list[DriftSimulation] = Field(default_factory=list)
    candidates: list[VesselCandidate] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    report: InvestigationReport | None = None


class PipelineStep(BaseModel):
    name: str
    status: str
    detail: str


class InvestigationResult(BaseModel):
    case: InvestigationCase
    steps: list[PipelineStep]
    tracks: list[VesselTrack]
    ground_truth_mmsi: str | None = None
