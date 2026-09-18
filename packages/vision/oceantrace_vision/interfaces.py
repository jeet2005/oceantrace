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


class SentinelReader(Protocol):
    def read_safe(self, safe_path: Path) -> "SentinelObservation":
        """Read a Sentinel-1 SAFE product."""

    def read_geotiff(self, tiff_path: Path) -> "SentinelObservation":
        """Read a GeoTIFF file."""

    def calibrate(self, observation: "SentinelObservation") -> "SentinelObservation":
        """Apply radiometric calibration."""

    def to_db_scale(self, observation: "SentinelObservation") -> "SentinelObservation":
        """Convert linear scale to dB."""

    def normalize(self, observation: "SentinelObservation") -> "SentinelObservation":
        """Normalize to [0, 1] range."""


from dataclasses import dataclass
from typing import Any

import numpy as np
from rasterio.crs import CRS
from rasterio.transform import Affine


@dataclass(frozen=True)
class SentinelObservation:
    vv: np.ndarray
    vh: np.ndarray | None
    transform: Affine
    crs: CRS
    bounds: tuple[float, float, float, float]
    width: int
    height: int
    metadata: dict[str, Any]
    product_type: str
    acquisition_time: str | None
    orbit_direction: str | None