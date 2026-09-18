from math import atan2, cos, degrees, hypot, radians

from oceantrace_common.models import Geometry

KM_PER_DEGREE_LATITUDE = 111.0


def box(center_lat: float, center_lon: float, half_lat: float, half_lon: float) -> Geometry:
    return Geometry(
        type="Polygon",
        coordinates=[
            [
                [center_lon - half_lon, center_lat - half_lat],
                [center_lon + half_lon, center_lat - half_lat],
                [center_lon + half_lon, center_lat + half_lat],
                [center_lon - half_lon, center_lat + half_lat],
                [center_lon - half_lon, center_lat - half_lat],
            ]
        ],
    )


def distance_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    lat_km = (a_lat - b_lat) * KM_PER_DEGREE_LATITUDE
    lon_km = (a_lon - b_lon) * KM_PER_DEGREE_LATITUDE * cos(radians((a_lat + b_lat) / 2))
    return hypot(lat_km, lon_km)


def bearing_degrees(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    return (degrees(atan2(b_lon - a_lon, b_lat - a_lat)) + 360) % 360


def polygon_centroid(region: Geometry) -> tuple[float, float]:
    ring = region.coordinates[0]
    latitudes = [float(point[1]) for point in ring[:-1]]
    longitudes = [float(point[0]) for point in ring[:-1]]
    return sum(latitudes) / len(latitudes), sum(longitudes) / len(longitudes)

