from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4

from oceantrace_common.models import AISPoint, VesselTrack


class AISProcessor(Protocol):
    def load_points(self, source: Path) -> list[AISPoint]:
        """Load and validate AIS observations from CSV or Parquet."""

    def build_tracks(self, points: list[AISPoint]) -> list[VesselTrack]:
        """Group sorted AIS points into vessel tracks."""


class AISIngestion(Protocol):
    def load_csv(self, csv_path: Path) -> "AISDataset":
        """Load AIS data from CSV file."""

    def load_parquet(self, parquet_path: Path) -> "AISDataset":
        """Load AIS data from Parquet file."""

    def validate_schema(
        self, data: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Validate AIS records, return (valid, invalid)."""

    def deduplicate(self, points: list[AISPoint]) -> list[AISPoint]:
        """Remove duplicate AIS points (same MMSI, timestamp, position)."""

    def detect_gaps(self, track: VesselTrack, max_gap_hours: float = 6.0) -> list[tuple[int, int]]:
        """Detect transmission gaps in a track, return list of (start_idx, end_idx)."""


class SpatialIndex(Protocol):
    def insert(self, track: VesselTrack) -> None:
        """Insert a track into the spatial index."""

    def query_bbox(self, bbox: tuple[float, float, float, float]) -> list[VesselTrack]:
        """Query tracks intersecting a bounding box (min_lon, min_lat, max_lon, max_lat)."""

    def query_radius(self, lat: float, lon: float, radius_km: float) -> list[VesselTrack]:
        """Query tracks within radius of a point."""

    def query_time_range(
        self, start: datetime, end: datetime
    ) -> list[VesselTrack]:
        """Query tracks with points in time range."""


class InterpolationService(Protocol):
    def interpolate_track(
        self, track: VesselTrack, interval_minutes: float = 10.0
    ) -> VesselTrack:
        """Interpolate track points to regular time intervals."""

    def fill_gaps(
        self, track: VesselTrack, max_gap_minutes: float = 60.0
    ) -> VesselTrack:
        """Fill gaps smaller than max_gap_minutes with linear interpolation."""


class AnomalyDetector(Protocol):
    def detect_stops(
        self, track: VesselTrack, speed_threshold_kn: float = 0.5, min_duration_minutes: float = 30.0
    ) -> list[tuple[int, int]]:
        """Detect stops (speed below threshold for min duration). Return (start_idx, end_idx)."""

    def detect_loitering(
        self, track: VesselTrack, radius_km: float = 5.0, min_duration_minutes: float = 60.0
    ) -> list[tuple[int, int]]:
        """Detect loitering (vessel stays within radius for duration). Return (start_idx, end_idx)."""

    def detect_route_deviation(
        self, track: VesselTrack, expected_route: list[tuple[float, float]], threshold_km: float = 10.0
    ) -> list[tuple[int, int]]:
        """Detect deviation from expected route. Return (start_idx, end_idx)."""

    def detect_speed_anomaly(
        self, track: VesselTrack, z_threshold: float = 3.0
    ) -> list[int]:
        """Detect speed anomalies using z-score. Return point indices."""

    def detect_course_change(
        self, track: VesselTrack, angle_threshold_deg: float = 45.0
    ) -> list[int]:
        """Detect sharp course changes. Return point indices."""


@dataclass(frozen=True)
class AISDataset:
    id: UUID = field(default_factory=uuid4)
    source_uri: str = ""
    points: list[AISPoint] = field(default_factory=list)
    tracks: list[VesselTrack] = field(default_factory=list)
    rejected_rows: int = 0


@dataclass(frozen=True)
class ScoringWeights:
    proximity: float = 0.25
    temporal_overlap: float = 0.25
    trajectory_consistency: float = 0.20
    drift_consistency: float = 0.20
    behavioral_anomaly: float = 0.10