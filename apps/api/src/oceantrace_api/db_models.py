from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oceantrace_api.db import Base

JSONDict = dict[str, Any]
JSONList = list[Any]


class InvestigationCaseRow(Base):
    __tablename__ = "investigation_cases"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    case_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("satellite_observations.id"), nullable=True)

    detections: Mapped[list["SpillDetectionRow"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    drift_simulations: Mapped[list["DriftSimulationRow"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    candidates: Mapped[list["VesselCandidateRow"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    evidence: Mapped[list["EvidenceRow"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    report: Mapped["InvestigationReportRow | None"] = relationship(back_populates="case", cascade="all, delete-orphan", uselist=False)


class SatelliteObservationRow(Base):
    __tablename__ = "satellite_observations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    sensor: Mapped[str] = mapped_column(String(64))
    source_uri: Mapped[str] = mapped_column(String(512))
    bbox: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)
    observation_metadata: Mapped[JSONDict] = mapped_column(JSONB, default=dict)


class SpillDetectionRow(Base):
    __tablename__ = "spill_detections"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investigation_cases.id"), index=True)
    observation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("satellite_observations.id"))
    confidence: Mapped[float] = mapped_column(Float)
    uncertainty: Mapped[str] = mapped_column(Text)
    estimated_age_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry: Mapped[JSONDict] = mapped_column(JSONB)
    area_km2: Mapped[float] = mapped_column(Float)
    perimeter_km: Mapped[float] = mapped_column(Float)
    length_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    width_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now())

    case: Mapped[InvestigationCaseRow] = relationship(back_populates="detections")


class DriftSimulationRow(Base):
    __tablename__ = "drift_simulations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investigation_cases.id"), index=True)
    detection_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("spill_detections.id"))
    mode: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    release_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    origin_region: Mapped[JSONDict | None] = mapped_column(JSONB, nullable=True)
    forecast_corridor: Mapped[JSONDict | None] = mapped_column(JSONB, nullable=True)
    trajectory_count: Mapped[int] = mapped_column(Integer)

    case: Mapped[InvestigationCaseRow] = relationship(back_populates="drift_simulations")


class VesselTrackRow(Base):
    __tablename__ = "vessel_tracks"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investigation_cases.id"), index=True)
    mmsi: Mapped[str] = mapped_column(String(32), index=True)
    vessel_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    points: Mapped[JSONList] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now())


class VesselCandidateRow(Base):
    __tablename__ = "vessel_candidates"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investigation_cases.id"), index=True)
    mmsi: Mapped[str] = mapped_column(String(32), index=True)
    vessel_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    proximity_score: Mapped[float] = mapped_column(Float)
    temporal_overlap_score: Mapped[float] = mapped_column(Float)
    trajectory_consistency_score: Mapped[float] = mapped_column(Float)
    drift_consistency_score: Mapped[float] = mapped_column(Float)
    behavioral_anomaly_score: Mapped[float] = mapped_column(Float)
    total_score: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    disclaimer: Mapped[str] = mapped_column(Text)

    case: Mapped[InvestigationCaseRow] = relationship(back_populates="candidates")

    __table_args__ = (
        Index("ix_vessel_candidates_case_score", "case_id", "total_score"),
    )


class EvidenceRow(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investigation_cases.id"), index=True)
    source: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(256))
    reference: Mapped[str] = mapped_column(String(512))
    excerpt: Mapped[str] = mapped_column(Text)

    case: Mapped[InvestigationCaseRow] = relationship(back_populates="evidence")


class InvestigationReportRow(Base):
    __tablename__ = "investigation_reports"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investigation_cases.id"), unique=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    executive_summary: Mapped[str] = mapped_column(Text)
    claims: Mapped[JSONList] = mapped_column(JSONB)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    disclaimer: Mapped[str] = mapped_column(Text)

    case: Mapped[InvestigationCaseRow] = relationship(back_populates="report")


class JobRecordRow(Base):
    __tablename__ = "job_records"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    case_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investigation_cases.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    message: Mapped[str] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)