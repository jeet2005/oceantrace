from datetime import datetime
from math import exp

from oceantrace_common.models import CandidateScore, VesselCandidate, VesselTrack

from oceantrace_api.services.geospatial import bearing_degrees, distance_km


class TransparentCandidateScoringService:
    weights = {
        "proximity": 0.25,
        "temporal_overlap": 0.25,
        "trajectory_consistency": 0.20,
        "drift_consistency": 0.20,
        "behavioral_anomaly": 0.10,
    }

    def score_candidates(
        self,
        tracks: list[VesselTrack],
        vessel_names: dict[str, str],
        origin_latitude: float,
        origin_longitude: float,
        observed_latitude: float,
        observed_longitude: float,
        release_time: datetime,
    ) -> list[VesselCandidate]:
        candidates = [
            self._candidate(
                track,
                vessel_names,
                origin_latitude,
                origin_longitude,
                observed_latitude,
                observed_longitude,
                release_time,
            )
            for track in tracks
        ]
        return sorted(candidates, key=lambda candidate: candidate.score.total, reverse=True)

    def _candidate(
        self,
        track: VesselTrack,
        vessel_names: dict[str, str],
        origin_latitude: float,
        origin_longitude: float,
        observed_latitude: float,
        observed_longitude: float,
        release_time: datetime,
    ) -> VesselCandidate:
        score = self._score_track(
            track,
            origin_latitude,
            origin_longitude,
            observed_latitude,
            observed_longitude,
            release_time,
        )
        vessel_name = vessel_names.get(track.mmsi, f"Vessel {track.mmsi}")
        return VesselCandidate(
            mmsi=track.mmsi,
            vessel_name=vessel_name,
            score=score,
            explanation=(
                f"{vessel_name} scored {score.total}/100 from proximity, release-window "
                "overlap, track direction, drift consistency, and behavioral signals."
            ),
            evidence_ids=[f"ais-{track.mmsi}", "drift-ensemble-001"],
        )

    def _score_track(
        self,
        track: VesselTrack,
        origin_latitude: float,
        origin_longitude: float,
        observed_latitude: float,
        observed_longitude: float,
        release_time: datetime,
    ) -> CandidateScore:
        distances = [
            distance_km(point.latitude, point.longitude, origin_latitude, origin_longitude)
            for point in track.points
        ]
        min_distance = min(distances)
        proximity = max(0.0, 100.0 * exp(-min_distance / 18.0))

        time_deltas = [
            abs((point.timestamp - release_time).total_seconds()) / 3600 for point in track.points
        ]
        temporal = max(0.0, 100.0 * exp(-min(time_deltas) / 2.5))

        first = track.points[0]
        last = track.points[-1]
        vessel_bearing = bearing_degrees(
            first.latitude,
            first.longitude,
            last.latitude,
            last.longitude,
        )
        target_bearing = bearing_degrees(
            origin_latitude,
            origin_longitude,
            observed_latitude,
            observed_longitude,
        )
        bearing_delta = abs((vessel_bearing - target_bearing + 180) % 360 - 180)
        trajectory = max(0.0, 100.0 * (1 - bearing_delta / 180))

        drift = max(0.0, 100.0 - min_distance * 4)
        speed_values = [point.sog or 0 for point in track.points]
        speed_range = max(speed_values) - min(speed_values)
        behavior = min(100.0, speed_range * 8)

        total = sum(
            [
                self.weights["proximity"] * proximity,
                self.weights["temporal_overlap"] * temporal,
                self.weights["trajectory_consistency"] * trajectory,
                self.weights["drift_consistency"] * drift,
                self.weights["behavioral_anomaly"] * behavior,
            ]
        )
        return CandidateScore(
            proximity=round(proximity, 2),
            temporal_overlap=round(temporal, 2),
            trajectory_consistency=round(trajectory, 2),
            drift_consistency=round(drift, 2),
            behavioral_anomaly=round(behavior, 2),
            total=round(total, 2),
        )
