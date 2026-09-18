from datetime import datetime, timedelta
from typing import Protocol

from oceantrace_common.models import Geometry
from pydantic import BaseModel, Field


class DriftRequest(BaseModel):
    spill_region: Geometry
    observation_time: datetime
    duration: timedelta
    timestep: timedelta
    particle_count: int = Field(ge=1)
    current_coefficient: float = 1.0
    wind_coefficient: float = 0.03


class DriftResult(BaseModel):
    origin_region: Geometry | None = None
    forecast_corridor: Geometry | None = None
    confidence: float = Field(ge=0, le=1)
    trajectory_count: int = Field(ge=0)


class DriftEngine(Protocol):
    def run_backward(self, request: DriftRequest) -> DriftResult:
        """Estimate probable release region and time window."""

    def run_forward(self, request: DriftRequest) -> DriftResult:
        """Estimate future slick movement corridor."""

