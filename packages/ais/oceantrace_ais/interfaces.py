from pathlib import Path
from typing import Protocol

from oceantrace_common.models import AISPoint, VesselTrack


class AISProcessor(Protocol):
    def load_points(self, source: Path) -> list[AISPoint]:
        """Load and validate AIS observations from CSV or Parquet."""

    def build_tracks(self, points: list[AISPoint]) -> list[VesselTrack]:
        """Group sorted AIS points into vessel tracks."""

