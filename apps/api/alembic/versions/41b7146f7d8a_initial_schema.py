"""initial schema

Revision ID: 41b7146f7d8a
Revises: 
Create Date: 2026-09-18 18:41:48.770729

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '41b7146f7d8a'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investigation_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_number", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_number"),
    )
    op.create_index("ix_investigation_cases_case_number", "investigation_cases", ["case_number"], unique=True)
    op.create_index("ix_investigation_cases_status", "investigation_cases", ["status"])

    op.create_table(
        "satellite_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sensor", sa.String(64), nullable=False),
        sa.Column("source_uri", sa.String(512), nullable=False),
        sa.Column("bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("observation_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_satellite_observations_captured_at", "satellite_observations", ["captured_at"])

    op.create_table(
        "spill_detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("estimated_age_hours", sa.Float(), nullable=True),
        sa.Column("geometry", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("area_km2", sa.Float(), nullable=False),
        sa.Column("perimeter_km", sa.Float(), nullable=False),
        sa.Column("length_km", sa.Float(), nullable=True),
        sa.Column("width_km", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["case_id"], ["investigation_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["observation_id"], ["satellite_observations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_spill_detections_case_id", "spill_detections", ["case_id"])

    op.create_table(
        "drift_simulations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("detection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("release_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("origin_region", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("forecast_corridor", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("trajectory_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["investigation_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["detection_id"], ["spill_detections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drift_simulations_case_id", "drift_simulations", ["case_id"])

    op.create_table(
        "vessel_tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mmsi", sa.String(32), nullable=False),
        sa.Column("vessel_type", sa.String(64), nullable=True),
        sa.Column("points", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["case_id"], ["investigation_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vessel_tracks_case_id", "vessel_tracks", ["case_id"])
    op.create_index("ix_vessel_tracks_mmsi", "vessel_tracks", ["mmsi"])

    op.create_table(
        "vessel_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mmsi", sa.String(32), nullable=False),
        sa.Column("vessel_name", sa.String(128), nullable=True),
        sa.Column("proximity_score", sa.Float(), nullable=False),
        sa.Column("temporal_overlap_score", sa.Float(), nullable=False),
        sa.Column("trajectory_consistency_score", sa.Float(), nullable=False),
        sa.Column("drift_consistency_score", sa.Float(), nullable=False),
        sa.Column("behavioral_anomaly_score", sa.Float(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("disclaimer", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["investigation_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vessel_candidates_case_id", "vessel_candidates", ["case_id"])
    op.create_index("ix_vessel_candidates_mmsi", "vessel_candidates", ["mmsi"])
    op.create_index("ix_vessel_candidates_case_score", "vessel_candidates", ["case_id", "total_score"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("reference", sa.String(512), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["investigation_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_case_id", "evidence", ["case_id"])

    op.create_table(
        "investigation_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("claims", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("disclaimer", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["investigation_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id"),
    )

    op.create_table(
        "job_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["investigation_cases.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_records_case_id", "job_records", ["case_id"])
    op.create_index("ix_job_records_status", "job_records", ["status"])


def downgrade() -> None:
    op.drop_index("ix_job_records_status", table_name="job_records")
    op.drop_index("ix_job_records_case_id", table_name="job_records")
    op.drop_table("job_records")

    op.drop_table("investigation_reports")

    op.drop_index("ix_evidence_case_id", table_name="evidence")
    op.drop_table("evidence")

    op.drop_index("ix_vessel_candidates_case_score", table_name="vessel_candidates")
    op.drop_index("ix_vessel_candidates_mmsi", table_name="vessel_candidates")
    op.drop_index("ix_vessel_candidates_case_id", table_name="vessel_candidates")
    op.drop_table("vessel_candidates")

    op.drop_index("ix_vessel_tracks_mmsi", table_name="vessel_tracks")
    op.drop_index("ix_vessel_tracks_case_id", table_name="vessel_tracks")
    op.drop_table("vessel_tracks")

    op.drop_index("ix_drift_simulations_case_id", table_name="drift_simulations")
    op.drop_table("drift_simulations")

    op.drop_index("ix_spill_detections_case_id", table_name="spill_detections")
    op.drop_table("spill_detections")

    op.drop_index("ix_satellite_observations_captured_at", table_name="satellite_observations")
    op.drop_table("satellite_observations")

    op.drop_index("ix_investigation_cases_status", table_name="investigation_cases")
    op.drop_index("ix_investigation_cases_case_number", table_name="investigation_cases")
    op.drop_table("investigation_cases")