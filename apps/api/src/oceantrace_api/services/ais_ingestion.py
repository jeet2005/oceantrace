import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from oceantrace_common.models import AISDataset, AISPoint, VesselTrack
from pydantic import ValidationError


class AISCsvIngestionService:
    required_columns = {"mmsi", "timestamp", "latitude", "longitude"}

    def load_csv(self, source: Path) -> AISDataset:
        points: list[AISPoint] = []
        rejected_rows = 0
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError("AIS CSV must include a header row.")
            columns = {name.strip().lower() for name in reader.fieldnames}
            missing = self.required_columns - columns
            if missing:
                raise ValueError(f"AIS CSV missing required columns: {', '.join(sorted(missing))}")

            for row in reader:
                try:
                    points.append(self._point(row))
                except (ValueError, ValidationError):
                    rejected_rows += 1

        points.sort(key=lambda point: (point.mmsi, point.timestamp))
        return AISDataset(
            source_uri=str(source),
            points=points,
            tracks=self.build_tracks(points),
            rejected_rows=rejected_rows,
        )

    def build_tracks(self, points: list[AISPoint]) -> list[VesselTrack]:
        grouped: dict[str, list[AISPoint]] = defaultdict(list)
        for point in points:
            grouped[point.mmsi].append(point)
        return [
            VesselTrack(mmsi=mmsi, points=sorted(items, key=lambda point: point.timestamp))
            for mmsi, items in sorted(grouped.items())
        ]

    def _point(self, row: dict[str, str]) -> AISPoint:
        normalized = {key.strip().lower(): value for key, value in row.items() if key}
        return AISPoint(
            mmsi=normalized["mmsi"],
            timestamp=datetime.fromisoformat(normalized["timestamp"].replace("Z", "+00:00")),
            latitude=float(normalized["latitude"]),
            longitude=float(normalized["longitude"]),
            sog=self._optional_float(normalized.get("sog")),
            cog=self._optional_float(normalized.get("cog")),
            heading=self._optional_float(normalized.get("heading")),
            imo=normalized.get("imo") or None,
            vessel_type=normalized.get("vessel_type") or None,
        )

    def _optional_float(self, value: str | None) -> float | None:
        if value is None or value == "":
            return None
        return float(value)

