from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field


class SegmentationResult(BaseModel):
    mask: "np.ndarray"  # binary mask [H, W]
    probability_map: "np.ndarray | None" = None  # probability map [H, W]
    confidence: float = Field(ge=0, le=1)
    uncertainty: str
    transform: Any  # rasterio Affine
    crs: Any  # rasterio CRS
    metadata: dict[str, Any] = Field(default_factory=dict)


class SatelliteModel(Protocol):
    name: str

    def segment(self, raster_path: Path) -> SegmentationResult:
        """Return an oil-slick segmentation result for one satellite raster."""

    def segment_batch(self, raster_paths: list[Path]) -> list[SegmentationResult]:
        """Segment multiple rasters."""

    def segment_array(self, array: "np.ndarray") -> SegmentationResult:
        """Segment a pre-loaded numpy array."""


class ModelRegistry(Protocol):
    def register(self, name: str, model: SatelliteModel) -> None:
        """Register a model."""

    def get(self, name: str) -> SatelliteModel | None:
        """Get a registered model."""

    def list_models(self) -> list[str]:
        """List registered model names."""


class CheckpointLoader(Protocol):
    def load(self, checkpoint_path: Path, device: str = "cpu") -> SatelliteModel:
        """Load model from checkpoint."""


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


@dataclass(frozen=True)
class Tile:
    """A single tile from a larger raster."""
    data: np.ndarray
    transform: Affine
    window: Any  # rasterio Window
    tile_index: tuple[int, int]  # (row, col)