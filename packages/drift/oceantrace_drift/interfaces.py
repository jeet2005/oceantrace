from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from pydantic import BaseModel, Field

from oceantrace_common.models import Geometry


class CurrentField(Protocol):
    def get_velocity(self, lat: float, lon: float, time: datetime) -> tuple[float, float]:
        """Return (u, v) velocity in m/s at given lat/lon/time."""
        ...


class WindField(Protocol):
    def get_velocity(self, lat: float, lon: float, time: datetime) -> tuple[float, float]:
        """Return (u, v) wind velocity in m/s at given lat/lon/time."""
        ...


class DriftRequest(BaseModel):
    spill_region: Geometry
    observation_time: datetime
    duration: timedelta
    timestep: timedelta
    particle_count: int = Field(ge=1, default=250)
    current_coefficient: float = Field(default=1.0, ge=0)
    wind_coefficient: float = Field(default=0.03, ge=0)
    diffusion_coefficient: float = Field(default=10.0, ge=0)  # m²/s
    backward: bool = True
    stochastic: bool = True
    random_seed: int | None = None


class ParticleState(BaseModel):
    lat: float
    lon: float
    time: datetime
    weight: float = 1.0


class DriftResult(BaseModel):
    origin_region: Geometry | None = None
    forecast_corridor: Geometry | None = None
    confidence: float = Field(ge=0, le=1)
    trajectory_count: int = Field(ge=0)
    particles: list[ParticleState] = Field(default_factory=list)
    statistics: dict[str, Any] = Field(default_factory=dict)


class DriftEngine(Protocol):
    def run_backward(self, request: DriftRequest) -> DriftResult:
        """Estimate probable release region and time window."""

    def run_forward(self, request: DriftRequest) -> DriftResult:
        """Estimate future slick movement corridor."""

    def run_monte_carlo(self, request: DriftRequest, ensemble_size: int = 10) -> DriftResult:
        """Run Monte Carlo ensemble with perturbed parameters."""


class CurrentProvider(Protocol):
    def get_field(self, start_time: datetime, end_time: datetime, bounds: tuple[float, float, float, float]) -> CurrentField:
        """Get current field for time range and geographic bounds."""

    def close(self) -> None:
        """Clean up resources."""


class WindProvider(Protocol):
    def get_field(self, start_time: datetime, end_time: datetime, bounds: tuple[float, float, float, float]) -> WindField:
        """Get wind field for time range and geographic bounds."""

    def close(self) -> None:
        """Clean up resources."""