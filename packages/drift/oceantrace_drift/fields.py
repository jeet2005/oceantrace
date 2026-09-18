from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from oceantrace_drift.interfaces import CurrentField, WindField


@dataclass
class UniformCurrentField(CurrentField):
    """Uniform constant current field for testing."""
    u: float  # m/s (eastward)
    v: float  # m/s (northward)

    def get_velocity(self, lat: float, lon: float, time: datetime) -> tuple[float, float]:
        return self.u, self.v


@dataclass
class UniformWindField(WindField):
    """Uniform constant wind field for testing."""
    u: float  # m/s (eastward)
    v: float  # m/s (northward)

    def get_velocity(self, lat: float, lon: float, time: datetime) -> tuple[float, float]:
        return self.u, self.v


@dataclass
class GriddedCurrentField(CurrentField):
    """Gridded current field from structured data (e.g., CMEMS, HYCOM)."""
    lats: np.ndarray
    lons: np.ndarray
    u_data: np.ndarray  # [time, lat, lon]
    v_data: np.ndarray  # [time, lat, lon]
    times: np.ndarray  # datetime64

    def __post_init__(self) -> None:
        from scipy.interpolate import RegularGridInterpolator
        self._u_interp = RegularGridInterpolator(
            (self.times, self.lats, self.lons), self.u_data,
            bounds_error=False, fill_value=0.0
        )
        self._v_interp = RegularGridInterpolator(
            (self.times, self.lats, self.lons), self.v_data,
            bounds_error=False, fill_value=0.0
        )

    def get_velocity(self, lat: float, lon: float, time: datetime) -> tuple[float, float]:
        t = np.datetime64(time)
        point = np.array([[t, lat, lon]])
        u = float(self._u_interp(point))
        v = float(self._v_interp(point))
        return u, v


@dataclass
class GriddedWindField(WindField):
    """Gridded wind field from structured data (e.g., ERA5, NOAA)."""
    lats: np.ndarray
    lons: np.ndarray
    u_data: np.ndarray  # [time, lat, lon]
    v_data: np.ndarray  # [time, lat, lon]
    times: np.ndarray  # datetime64

    def __post_init__(self) -> None:
        from scipy.interpolate import RegularGridInterpolator
        self._u_interp = RegularGridInterpolator(
            (self.times, self.lats, self.lons), self.u_data,
            bounds_error=False, fill_value=0.0
        )
        self._v_interp = RegularGridInterpolator(
            (self.times, self.lats, self.lons), self.v_data,
            bounds_error=False, fill_value=0.0
        )

    def get_velocity(self, lat: float, lon: float, time: datetime) -> tuple[float, float]:
        t = np.datetime64(time)
        point = np.array([[t, lat, lon]])
        u = float(self._u_interp(point))
        v = float(self._v_interp(point))
        return u, v


class MockCurrentProvider:
    """Mock current provider for testing - generates synthetic eddy field."""

    def __init__(self, center_lat: float = 15.0, center_lon: float = 73.0) -> None:
        self.center_lat = center_lat
        self.center_lon = center_lon

    def get_field(
        self,
        start_time: datetime,
        end_time: datetime,
        bounds: tuple[float, float, float, float],
    ) -> CurrentField:
        class EddyCurrentField(CurrentField):
            def __init__(self, center_lat: float, center_lon: float) -> None:
                self.center_lat = center_lat
                self.center_lon = center_lon

            def get_velocity(self, lat: float, lon: float, time: datetime) -> tuple[float, float]:
                from math import sin, cos, sqrt
                dx = (lon - self.center_lon) * 111000 * cos(lat * np.pi / 180)
                dy = (lat - self.center_lat) * 111000
                r = sqrt(dx * dx + dy * dy)
                if r < 50000:
                    theta = np.arctan2(dy, dx)
                    speed = 0.5 * (r / 50000)
                    return -speed * sin(theta), speed * cos(theta)
                return 0.0, 0.0

        return EddyCurrentField(self.center_lat, self.center_lon)

    def close(self) -> None:
        pass


class MockWindProvider:
    """Mock wind provider for testing - constant wind with diurnal variation."""

    def __init__(self, base_u: float = 5.0, base_v: float = 2.0) -> None:
        self.base_u = base_u
        self.base_v = base_v

    def get_field(
        self,
        start_time: datetime,
        end_time: datetime,
        bounds: tuple[float, float, float, float],
    ) -> WindField:
        class DiurnalWindField(WindField):
            def __init__(self, base_u: float, base_v: float) -> None:
                self.base_u = base_u
                self.base_v = base_v

            def get_velocity(self, lat: float, lon: float, time: datetime) -> tuple[float, float]:
                hour = time.hour + time.minute / 60
                factor = 1.0 + 0.3 * np.sin(2 * np.pi * (hour - 6) / 24)
                return self.base_u * factor, self.base_v * factor

        return DiurnalWindField(self.base_u, self.base_v)

    def close(self) -> None:
        pass