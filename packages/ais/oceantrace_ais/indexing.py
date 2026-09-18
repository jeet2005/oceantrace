from datetime import datetime, timedelta
from typing import Any

import numpy as np
from shapely.geometry import Point, box, LineString
from shapely.strtree import STRtree

from oceantrace_ais.interfaces import (
    AnomalyDetector,
    InterpolationService,
    SpatialIndex,
)
from oceantrace_common.models import AISPoint, VesselTrack


class RTreeSpatialIndex(SpatialIndex):
    """R-tree spatial index for vessel tracks using shapely's STRtree."""

    def __init__(self) -> None:
        self._tracks: list[VesselTrack] = []
        self._geoms: list[Any] = []
        self._tree: STRtree | None = None

    def insert(self, track: VesselTrack) -> None:
        if len(track.points) < 2:
            return
        self._tracks.append(track)
        coords = [(p.longitude, p.latitude) for p in track.points]
        line = LineString(coords)
        self._geoms.append(line)
        self._tree = STRtree(self._geoms)

    def query_bbox(self, bbox: tuple[float, float, float, float]) -> list[VesselTrack]:
        min_lon, min_lat, max_lon, max_lat = bbox
        query_box = box(min_lon, min_lat, max_lon, max_lat)
        if self._tree is None:
            return []
        indices = self._tree.query(query_box)
        return [self._tracks[i] for i in indices if i < len(self._tracks)]

    def query_radius(self, lat: float, lon: float, radius_km: float) -> list[VesselTrack]:
        radius_deg = radius_km / 111.0
        query_box = box(lon - radius_deg, lat - radius_deg, lon + radius_deg, lat + radius_deg)
        return self.query_bbox((query_box.bounds[0], query_box.bounds[1], query_box.bounds[2], query_box.bounds[3]))

    def query_time_range(self, start: datetime, end: datetime) -> list[VesselTrack]:
        results = []
        for track in self._tracks:
            if track.points:
                track_start = track.points[0].timestamp
                track_end = track.points[-1].timestamp
                if track_start <= end and track_end >= start:
                    results.append(track)
        return results


class LinearInterpolationService(InterpolationService):
    """Linear interpolation for AIS tracks."""

    def interpolate_track(
        self, track: VesselTrack, interval_minutes: float = 10.0
    ) -> VesselTrack:
        if len(track.points) < 2:
            return track

        interval_seconds = interval_minutes * 60
        start_time = track.points[0].timestamp
        end_time = track.points[-1].timestamp
        total_seconds = (end_time - start_time).total_seconds()

        if total_seconds <= 0:
            return track

        n_intervals = int(total_seconds / interval_seconds) + 1
        new_points = []

        for i in range(n_intervals):
            target_dt = start_time + timedelta(seconds=i * interval_seconds)
            lat, lon, sog, cog, heading = self._interpolate_at_time(track, target_dt)
            if lat is not None:
                new_points.append(AISPoint(
                    mmsi=track.mmsi,
                    timestamp=target_dt,
                    latitude=lat,
                    longitude=lon,
                    sog=sog,
                    cog=cog,
                    heading=heading,
                    vessel_type=track.points[0].vessel_type if track.points else None,
                ))

        if new_points:
            return VesselTrack(
                mmsi=track.mmsi,
                points=new_points,
            )
        return track

    def _interpolate_at_time(
        self, track: VesselTrack, target_dt: datetime
    ) -> tuple[float | None, float | None, float | None, float | None, float | None]:
        points = track.points
        if target_dt <= points[0].timestamp:
            p = points[0]
            return p.latitude, p.longitude, p.sog, p.cog, p.heading
        if target_dt >= points[-1].timestamp:
            p = points[-1]
            return p.latitude, p.longitude, p.sog, p.cog, p.heading

        for i in range(len(points) - 1):
            t1 = points[i].timestamp
            t2 = points[i + 1].timestamp
            if t1 <= target_dt <= t2:
                frac = (target_dt - t1).total_seconds() / (t2 - t1).total_seconds()
                lat = points[i].latitude + frac * (points[i + 1].latitude - points[i].latitude)
                lon = points[i].longitude + frac * (points[i + 1].longitude - points[i].longitude)
                sog = None
                cog = None
                heading = None
                if points[i].sog is not None and points[i + 1].sog is not None:
                    sog1 = points[i].sog
                    sog2 = points[i + 1].sog
                    assert sog1 is not None and sog2 is not None
                    sog = sog1 + frac * (sog2 - sog1)
                if points[i].cog is not None and points[i + 1].cog is not None:
                    cog1 = points[i].cog
                    cog2 = points[i + 1].cog
                    assert cog1 is not None and cog2 is not None
                    cog = self._interpolate_bearing(cog1, cog2, frac)
                if points[i].heading is not None and points[i + 1].heading is not None:
                    h1 = points[i].heading
                    h2 = points[i + 1].heading
                    assert h1 is not None and h2 is not None
                    heading = self._interpolate_bearing(h1, h2, frac)
                return lat, lon, sog, cog, heading
        return None, None, None, None, None

    def _interpolate_bearing(self, b1: float, b2: float, frac: float) -> float:
        import math
        b1_rad = math.radians(b1)
        b2_rad = math.radians(b2)
        x1, y1 = math.cos(b1_rad), math.sin(b1_rad)
        x2, y2 = math.cos(b2_rad), math.sin(b2_rad)
        x = x1 + frac * (x2 - x1)
        y = y1 + frac * (y2 - y1)
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    def fill_gaps(
        self, track: VesselTrack, max_gap_minutes: float = 60.0
    ) -> VesselTrack:
        if len(track.points) < 2:
            return track

        max_gap_seconds = max_gap_minutes * 60
        new_points = [track.points[0]]

        for i in range(1, len(track.points)):
            gap = (track.points[i].timestamp - track.points[i - 1].timestamp).total_seconds()
            if gap <= max_gap_seconds:
                new_points.append(track.points[i])
            else:
                interval_seconds = min(600.0, max_gap_seconds / 2)
                n_new = int(gap / interval_seconds)
                for j in range(1, n_new + 1):
                    target_dt = track.points[i - 1].timestamp + timedelta(seconds=j * interval_seconds)
                    lat, lon, sog, cog, heading = self._interpolate_at_time(track, target_dt)
                    if lat is not None:
                        new_points.append(AISPoint(
                            mmsi=track.mmsi,
                            timestamp=target_dt,
                            latitude=lat,
                            longitude=lon,
                            sog=sog,
                            cog=cog,
                            heading=heading,
                            vessel_type=track.points[0].vessel_type if track.points else None,
                        ))
                new_points.append(track.points[i])

        return VesselTrack(
            mmsi=track.mmsi,
            points=new_points,
        )


class StatisticalAnomalyDetector(AnomalyDetector):
    """Statistical anomaly detection for vessel tracks."""

    def detect_stops(
        self, track: VesselTrack, speed_threshold_kn: float = 0.5, min_duration_minutes: float = 30.0
    ) -> list[tuple[int, int]]:
        stops = []
        in_stop = False
        start_idx = -1

        for i, point in enumerate(track.points):
            speed = point.sog or 0
            if speed < speed_threshold_kn:
                if not in_stop:
                    in_stop = True
                    start_idx = i
            else:
                if in_stop:
                    duration = (track.points[i - 1].timestamp - track.points[start_idx].timestamp).total_seconds() / 60
                    if duration >= min_duration_minutes:
                        stops.append((start_idx, i - 1))
                    in_stop = False

        if in_stop:
            duration = (track.points[-1].timestamp - track.points[start_idx].timestamp).total_seconds() / 60
            if duration >= min_duration_minutes:
                stops.append((start_idx, len(track.points) - 1))

        return stops

    def detect_loitering(
        self, track: VesselTrack, radius_km: float = 5.0, min_duration_minutes: float = 60.0
    ) -> list[tuple[int, int]]:
        loitering = []
        in_loiter = False
        start_idx = -1
        center_lat: float | None = None
        center_lon: float | None = None

        for i, point in enumerate(track.points):
            if center_lat is None:
                lat0 = point.latitude
                lon0 = point.longitude
                center_lat = lat0
                center_lon = lon0
                continue

            lat = point.latitude
            lon = point.longitude
            # center_lat/center_lon are guaranteed to be set after first iteration
            assert center_lat is not None and center_lon is not None
            dist = self._distance_km(center_lat, center_lon, lat, lon)
            if dist <= radius_km:
                if not in_loiter:
                    in_loiter = True
                    start_idx = i
            else:
                if in_loiter:
                    duration = (track.points[i - 1].timestamp - track.points[start_idx].timestamp).total_seconds() / 60
                    if duration >= min_duration_minutes:
                        loitering.append((start_idx, i - 1))
                    in_loiter = False
                lat = point.latitude
                lon = point.longitude
                center_lat = lat
                center_lon = lon

        if in_loiter:
            duration = (track.points[-1].timestamp - track.points[start_idx].timestamp).total_seconds() / 60
            if duration >= min_duration_minutes:
                loitering.append((start_idx, len(track.points) - 1))

        return loitering

    def detect_route_deviation(
        self, track: VesselTrack, expected_route: list[tuple[float, float]], threshold_km: float = 10.0
    ) -> list[tuple[int, int]]:
        if len(expected_route) < 2:
            return []

        deviations = []
        in_deviation = False
        start_idx = -1

        for i, point in enumerate(track.points):
            lat = point.latitude
            lon = point.longitude
            min_dist = min(
                self._distance_km(lat, lon, r[0], r[1])
                for r in expected_route
            )
            if min_dist > threshold_km:
                if not in_deviation:
                    in_deviation = True
                    start_idx = i
            else:
                if in_deviation:
                    deviations.append((start_idx, i - 1))
                    in_deviation = False

        if in_deviation:
            deviations.append((start_idx, len(track.points) - 1))

        return deviations

    def detect_speed_anomaly(
        self, track: VesselTrack, z_threshold: float = 3.0
    ) -> list[int]:
        speeds = [p.sog for p in track.points if p.sog is not None]
        if len(speeds) < 3:
            return []

        mean_speed = np.mean(speeds)
        std_speed = np.std(speeds)
        if std_speed == 0:
            return []

        anomalies = []
        for i, point in enumerate(track.points):
            if point.sog is not None:
                z = abs(point.sog - mean_speed) / std_speed
                if z > z_threshold:
                    anomalies.append(i)
        return anomalies

    def detect_course_change(
        self, track: VesselTrack, angle_threshold_deg: float = 45.0
    ) -> list[int]:
        if len(track.points) < 3:
            return []

        anomalies = []
        for i in range(1, len(track.points) - 1):
            p1 = track.points[i - 1]
            p2 = track.points[i]
            p3 = track.points[i + 1]

            if p1.cog is None or p2.cog is None or p3.cog is None:
                continue

            bearing1 = self._bearing(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
            bearing2 = self._bearing(p2.latitude, p2.longitude, p3.latitude, p3.longitude)

            change = abs((bearing2 - bearing1 + 180) % 360 - 180)
            if change > angle_threshold_deg:
                anomalies.append(i)

        return anomalies

    def _distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        from math import radians, cos, sin, sqrt, atan2
        R = 6371.0
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    def _bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        from math import radians, degrees, atan2, sin, cos
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        y = sin(dlon) * cos(lat2)
        x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
        return (degrees(atan2(y, x)) + 360) % 360