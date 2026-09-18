from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field


class SegmentationResult(BaseModel):
    mask_path: Path | None = None
    confidence: float = Field(ge=0, le=1)
    uncertainty: str


class SatelliteModel(Protocol):
    name: str

    def segment(self, raster_path: Path) -> SegmentationResult:
        """Return an oil-slick segmentation result for one satellite raster."""

