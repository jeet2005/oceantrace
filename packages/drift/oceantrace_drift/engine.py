from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from oceantrace_drift.interfaces import (
    CurrentField,
    DriftRequest,
    DriftResult,
    ParticleState,
    WindField,
)
from oceantrace_drift.fields import UniformCurrentField, UniformWindField


KM_PER_DEG_LAT = 111.0


def lat_lon_to_xy(lat: float, lon: float, ref_lat: float) -> tuple[float, float]:
    """Convert lat/lon to local Cartesian (km)."""
    x = (lon - 0) * KM_PER_DEG_LAT * np.cos(np.radians(ref_lat))
    y = (lat - 0) * KM_PER_DEG_LAT
    return x, y


def xy_to_lat_lon(x: float, y: float, ref_lat: float) -> tuple[float, float]:
    """Convert local Cartesian (km) back to lat/lon."""
    lon = x / (KM_PER_DEG_LAT * np.cos(np.radians(ref_lat)))
    lat = y / KM_PER_DEG_LAT
    return lat, lon


def rk4_step(
    lat: float,
    lon: float,
    time: datetime,
    dt_seconds: float,
    current_field: CurrentField,
    wind_field: WindField,
    current_coeff: float,
    wind_coeff: float,
) -> tuple[float, float]:
    """Single RK4 step for particle advection."""
    # Velocity function combining current + wind drift
    def velocity(lat_: float, lon_: float, t: datetime) -> tuple[float, float]:
        cu, cv = current_field.get_velocity(lat_, lon_, t)
        wu, wv = wind_field.get_velocity(lat_, lon_, t)
        return (
            current_coeff * cu + wind_coeff * wu,
            current_coeff * cv + wind_coeff * wv,
        )

    # Convert to local Cartesian for integration
    ref_lat = lat
    x0, y0 = lat_lon_to_xy(lat, lon, ref_lat)

    def vel_xy(x: float, y: float, t: datetime) -> tuple[float, float]:
        lat_, lon_ = xy_to_lat_lon(x, y, ref_lat)
        vx, vy = velocity(lat_, lon_, t)
        # Convert m/s to km/s
        return vx / 1000.0, vy / 1000.0

    # RK4 integration
    k1x, k1y = vel_xy(x0, y0, time)
    k2x, k2y = vel_xy(x0 + 0.5 * dt_seconds * k1x, y0 + 0.5 * dt_seconds * k1y, time + timedelta(seconds=dt_seconds / 2))
    k3x, k3y = vel_xy(x0 + 0.5 * dt_seconds * k2x, y0 + 0.5 * dt_seconds * k2y, time + timedelta(seconds=dt_seconds / 2))
    k4x, k4y = vel_xy(x0 + dt_seconds * k3x, y0 + dt_seconds * k3y, time + timedelta(seconds=dt_seconds))

    x1 = x0 + (dt_seconds / 6.0) * (k1x + 2 * k2x + 2 * k3x + k4x)
    y1 = y0 + (dt_seconds / 6.0) * (k1y + 2 * k2y + 2 * k3y + k4y)

    lat1, lon1 = xy_to_lat_lon(x1, y1, ref_lat)
    return lat1, lon1


def euler_maruyama_step(
    lat: float,
    lon: float,
    time: datetime,
    dt_seconds: float,
    current_field: CurrentField,
    wind_field: WindField,
    current_coeff: float,
    wind_coeff: float,
    diffusion_coeff: float,
    rng: np.random.Generator,
) -> tuple[float, float]:
    """Euler-Maruyama step with stochastic diffusion."""
    # Deterministic advection (simplified Euler for diffusion term)
    cu, cv = current_field.get_velocity(lat, lon, time)
    wu, wv = wind_field.get_velocity(lat, lon, time)

    vx = current_coeff * cu + wind_coeff * wu
    vy = current_coeff * cv + wind_coeff * wv

    # Convert to km/s
    vx_km = vx / 1000.0
    vy_km = vy / 1000.0

    # Deterministic displacement
    x, y = lat_lon_to_xy(lat, lon, lat)
    x += vx_km * dt_seconds
    y += vy_km * dt_seconds

    # Stochastic diffusion: sqrt(2 * D * dt) * N(0,1)
    sigma = np.sqrt(2 * diffusion_coeff * dt_seconds) / 1000.0  # km
    x += rng.normal(0, sigma)
    y += rng.normal(0, sigma)

    lat_new, lon_new = xy_to_lat_lon(x, y, lat)
    return lat_new, lon_new


@dataclass
class Particle:
    lat: float
    lon: float
    time: datetime
    weight: float = 1.0
    trajectory: list[tuple[float, float, datetime]] | None = None

    def record_position(self) -> None:
        if self.trajectory is not None:
            self.trajectory.append((self.lat, self.lon, self.time))


class DriftEngine:
    def __init__(
        self,
        current_field: CurrentField | None = None,
        wind_field: WindField | None = None,
    ):
        self.current_field = current_field or UniformCurrentField(0.0, 0.0)
        self.wind_field = wind_field or UniformWindField(0.0, 0.0)

    def run_backward(self, request: DriftRequest) -> DriftResult:
        return self._run(request, backward=True)

    def run_forward(self, request: DriftRequest) -> DriftResult:
        return self._run(request, backward=False)

    def run_monte_carlo(
        self,
        request: DriftRequest,
        ensemble_size: int = 10,
        param_ranges: dict[str, tuple[float, float]] | None = None,
    ) -> DriftResult:
        if param_ranges is None:
            param_ranges = {
                "current_coeff": (0.8, 1.2),
                "wind_coeff": (0.02, 0.04),
                "diffusion_coeff": (5.0, 20.0),
            }

        rng = np.random.default_rng(request.random_seed)
        ensemble_results = []

        for i in range(ensemble_size):
            # Perturb parameters
            perturbed_request = self._perturb_request(request, param_ranges, rng)
            perturbed_request.random_seed = int(rng.integers(0, 2**32))

            result = self._run(perturbed_request, backward=request.backward)
            ensemble_results.append(result)

        return self._aggregate_ensemble(ensemble_results, request)

    def _perturb_request(
        self,
        request: DriftRequest,
        param_ranges: dict[str, tuple[float, float]],
        rng: np.random.Generator,
    ) -> DriftRequest:
        current_coeff = rng.uniform(*param_ranges.get("current_coeff", (request.current_coefficient, request.current_coefficient)))
        wind_coeff = rng.uniform(*param_ranges.get("wind_coeff", (request.wind_coefficient, request.wind_coefficient)))
        diffusion_coeff = rng.uniform(*param_ranges.get("diffusion_coeff", (request.diffusion_coefficient, request.diffusion_coefficient)))

        return DriftRequest(
            spill_region=request.spill_region,
            observation_time=request.observation_time,
            duration=request.duration,
            timestep=request.timestep,
            particle_count=request.particle_count,
            current_coefficient=current_coeff,
            wind_coefficient=wind_coeff,
            diffusion_coefficient=diffusion_coeff,
            backward=request.backward,
            stochastic=request.stochastic,
            random_seed=rng.integers(0, 2**32),
        )

    def _run(self, request: DriftRequest, backward: bool) -> DriftResult:
        rng = np.random.default_rng(request.random_seed)

        # Initialize particles from spill region
        particles = self._initialize_particles(request, rng)

        # Time stepping
        dt = request.timestep
        if backward:
            dt = -dt

        total_steps = int(abs(request.duration.total_seconds() / dt.total_seconds()))
        dt_seconds = dt.total_seconds()

        # Store trajectories if requested
        store_trajectories = request.particle_count <= 1000
        for p in particles:
            if store_trajectories:
                p.trajectory = [(p.lat, p.lon, p.time)]

        for step in range(total_steps):
            for particle in particles:
                if request.stochastic:
                    particle.lat, particle.lon = euler_maruyama_step(
                        particle.lat, particle.lon, particle.time,
                        abs(dt_seconds),
                        self.current_field, self.wind_field,
                        request.current_coefficient, request.wind_coefficient,
                        request.diffusion_coefficient,
                        rng
                    )
                else:
                    particle.lat, particle.lon = rk4_step(
                        particle.lat, particle.lon, particle.time,
                        abs(dt_seconds),
                        self.current_field, self.wind_field,
                        request.current_coefficient, request.wind_coefficient,
                    )

                particle.time += dt
                particle.record_position()

        return self._build_result(particles, request, backward)

    def _initialize_particles(self, request: DriftRequest, rng: np.random.Generator) -> list[Particle]:
        """Initialize particles uniformly within spill region polygon."""
        from shapely.geometry import shape

        # Convert Pydantic Geometry to dict for shapely
        geom_dict = request.spill_region.model_dump() if hasattr(request.spill_region, 'model_dump') else request.spill_region
        geom = shape(geom_dict)
        if geom.geom_type == "Polygon":
            polygons = [geom]
        elif geom.geom_type == "MultiPolygon":
            polygons = list(geom.geoms)
        else:
            # Fallback: use bounding box
            minx, miny, maxx, maxy = geom.bounds
            particles = []
            for _ in range(request.particle_count):
                lat = rng.uniform(miny, maxy)
                lon = rng.uniform(minx, maxx)
                particles.append(Particle(lat=lat, lon=lon, time=request.observation_time))
            return particles

        # Uniform sampling within polygon(s)
        total_area = sum(p.area for p in polygons)
        particles = []

        for poly in polygons:
            n_particles = max(1, int(request.particle_count * (poly.area / total_area)))
            minx, miny, maxx, maxy = poly.bounds

            for _ in range(n_particles):
                # Rejection sampling
                for _ in range(100):
                    lat = rng.uniform(miny, maxy)
                    lon = rng.uniform(minx, maxx)
                    if poly.contains(shape({"type": "Point", "coordinates": [lon, lat]})):
                        particles.append(Particle(lat=lat, lon=lon, time=request.observation_time))
                        break
                else:
                    # Fallback to centroid
                    particles.append(Particle(lat=poly.centroid.y, lon=poly.centroid.x, time=request.observation_time))

        return particles

    def _build_result(
        self,
        particles: list[Particle],
        request: DriftRequest,
        backward: bool,
    ) -> DriftResult:
        if not particles:
            return DriftResult(
                confidence=0.0,
                trajectory_count=0,
            )

        # Compute final positions
        lats = np.array([p.lat for p in particles])
        lons = np.array([p.lon for p in particles])

        # Convex hull for origin/forecast region
        from shapely.geometry import MultiPoint, Polygon
        from shapely.ops import unary_union

        points = MultiPoint(list(zip(lons, lats)))
        hull = points.convex_hull

        # Buffer slightly for region
        if hull.geom_type == "Point":
            hull = hull.buffer(0.01)
        elif hull.geom_type == "LineString":
            hull = hull.buffer(0.01)

        region_geom = {
            "type": "Polygon",
            "coordinates": [list(hull.exterior.coords)],
        } if hull.geom_type == "Polygon" else {
            "type": "MultiPolygon",
            "coordinates": [[list(p.exterior.coords)] for p in hull.geoms],
        }

        # Statistics
        lat_mean, lat_std = np.mean(lats), np.std(lats)
        lon_mean, lon_std = np.mean(lons), np.std(lons)

        confidence = 1.0 / (1.0 + lat_std + lon_std)  # Simple confidence metric

        return DriftResult(
            origin_region=region_geom if backward else None,
            forecast_corridor=region_geom if not backward else None,
            confidence=min(1.0, max(0.0, confidence)),
            trajectory_count=len(particles),
            particles=[
                ParticleState(lat=p.lat, lon=p.lon, time=p.time, weight=p.weight)
                for p in particles
            ],
            statistics={
                "lat_mean": float(lat_mean),
                "lat_std": float(lat_std),
                "lon_mean": float(lon_mean),
                "lon_std": float(lon_std),
                "backward": backward,
            },
        )

    def _aggregate_ensemble(
        self,
        ensemble_results: list[DriftResult],
        request: DriftRequest,
    ) -> DriftResult:
        """Aggregate Monte Carlo ensemble into probability corridor."""
        if not ensemble_results:
            return DriftResult(confidence=0.0, trajectory_count=0)

        # Collect all particles from ensemble
        all_lats = []
        all_lons = []
        all_times = []

        for result in ensemble_results:
            for p in result.particles:
                all_lats.append(p.lat)
                all_lons.append(p.lon)
                all_times.append(p.time)

        if not all_lats:
            return ensemble_results[0]

        # Compute probability density via kernel density estimation
        from scipy.stats import gaussian_kde

        points = np.vstack([all_lats, all_lons])
        kde = gaussian_kde(points)

        # Create grid for probability corridor
        lat_min, lat_max = np.min(all_lats), np.max(all_lats)
        lon_min, lon_max = np.min(all_lons), np.max(all_lons)

        # Add buffer
        lat_range = lat_max - lat_min
        lon_range = lon_max - lon_min
        lat_min -= 0.1 * lat_range
        lat_max += 0.1 * lat_range
        lon_min -= 0.1 * lon_range
        lon_max += 0.1 * lon_range

        # Evaluate KDE on grid
        grid_res = 50
        lat_grid = np.linspace(lat_min, lat_max, grid_res)
        lon_grid = np.linspace(lon_min, lon_max, grid_res)
        Lon, Lat = np.meshgrid(lon_grid, lat_grid)
        grid_points = np.vstack([Lat.ravel(), Lon.ravel()])
        density = kde(grid_points).reshape(grid_res, grid_res)

        # Contour at 50% probability level for corridor
        from shapely.geometry import Polygon, MultiPoint
        from shapely.ops import unary_union
        from skimage import measure

        contours = measure.find_contours(density, 0.5 * density.max())  # type: ignore[no-untyped-call]
        corridor_polygons = []

        for contour in contours:
            if len(contour) > 3:
                lats_c = lat_grid[contour[:, 0].astype(int).clip(0, grid_res - 1)]
                lons_c = lon_grid[contour[:, 1].astype(int).clip(0, grid_res - 1)]
                poly = Polygon(zip(lons_c, lats_c))
                if poly.area > 0:
                    corridor_polygons.append(poly)

        if corridor_polygons:
            union = unary_union(corridor_polygons)
            if union.geom_type == "Polygon":
                corridor_geom = {
                    "type": "Polygon",
                    "coordinates": [list(union.exterior.coords)],
                }
            else:
                corridor_geom = {
                    "type": "MultiPolygon",
                    "coordinates": [[list(p.exterior.coords)] for p in union.geoms],
                }
        else:
            # Fallback to convex hull
            all_points = np.column_stack([all_lons, all_lats])
            from shapely.geometry import MultiPoint
            hull = MultiPoint(all_points).convex_hull
            corridor_geom = {
                "type": "Polygon",
                "coordinates": [list(hull.exterior.coords)],
            }

        # Aggregate statistics
        total_particles = sum(r.trajectory_count for r in ensemble_results)
        avg_confidence = np.mean([r.confidence for r in ensemble_results])

        return DriftResult(
            origin_region=ensemble_results[0].origin_region if request.backward else None,
            forecast_corridor=corridor_geom if not request.backward else None,
            confidence=float(avg_confidence),
            trajectory_count=total_particles,
            statistics={
                "ensemble_size": len(ensemble_results),
                "total_particles": total_particles,
                "lat_std": float(np.std(all_lats)),
                "lon_std": float(np.std(all_lons)),
            },
        )