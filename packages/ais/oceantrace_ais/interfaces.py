from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class AISDataset:
    id: UUID = field(default_factory=uuid4)
    source_uri: str = ""
    points: list[AISPoint] = field(default_factory=list)
    tracks: list[VesselTrack] = field(default_factory=list)
    rejected_rows: int = 0