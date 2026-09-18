import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from oceantrace_common.models import AISPoint, VesselTrack

from oceantrace_ais.interfaces import AISDataset, AISIngestion


class AISCsvParquetIngestion(AISIngestion):
    REQUIRED_FIELDS = {"mmsi", "timestamp", "latitude", "longitude"}
    OPTIONAL_FIELDS = {"sog", "cog", "heading", "imo", "vessel_type"}

    def load_csv(self, csv_path: Path) -> AISDataset:
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        points = []
        rejected = 0

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for _row_num, row in enumerate(reader, start=1):
                try:
                    point = self._parse_row(row)
                    points.append(point)
                except Exception:
                    rejected += 1

        points = self.deduplicate(points)
        points.sort(key=lambda p: (p.mmsi, p.timestamp))
        tracks = self._build_tracks(points)

        return AISDataset(
            source_uri=str(csv_path),
            points=points,
            tracks=tracks,
            rejected_rows=rejected,
        )

    def load_parquet(self, parquet_path: Path) -> AISDataset:
        parquet_path = Path(parquet_path)
        if not parquet_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

        try:
            import pyarrow.parquet as pq
        except ImportError:
            raise ImportError("pyarrow required for Parquet support: pip install pyarrow") from None

        table = pq.read_table(parquet_path)
        df = table.to_pandas()

        points = []
        rejected = 0

        for _, row in df.iterrows():
            try:
                point = self._parse_row(row.to_dict())
                points.append(point)
            except Exception:
                rejected += 1

        points = self.deduplicate(points)
        points.sort(key=lambda p: (p.mmsi, p.timestamp))
        tracks = self._build_tracks(points)

        return AISDataset(
            source_uri=str(parquet_path),
            points=points,
            tracks=tracks,
            rejected_rows=rejected,
        )

    def validate_schema(
        self, data: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        valid = []
        invalid = []
        for record in data:
            missing = self.REQUIRED_FIELDS - set(record.keys())
            if missing:
                invalid.append({"record": record, "error": f"Missing required fields: {missing}"})
            else:
                try:
                    self._parse_row(record)
                    valid.append(record)
                except Exception as e:
                    invalid.append({"record": record, "error": str(e)})
        return valid, invalid

    def deduplicate(self, points: list[AISPoint]) -> list[AISPoint]:
        seen: set[tuple[str, datetime, float, float]] = set()
        unique = []
        for point in points:
            key = (point.mmsi, point.timestamp, round(point.latitude, 6), round(point.longitude, 6))
            if key not in seen:
                seen.add(key)
                unique.append(point)
        return unique

    def detect_gaps(self, track: VesselTrack, max_gap_hours: float = 6.0) -> list[tuple[int, int]]:
        gaps = []
        for i in range(1, len(track.points)):
            delta = (
                track.points[i].timestamp - track.points[i - 1].timestamp
            ).total_seconds() / 3600
            if delta > max_gap_hours:
                gaps.append((i - 1, i))
        return gaps

    def _parse_row(self, row: dict[str, Any]) -> AISPoint:
        mmsi = str(row["mmsi"]).strip()
        if not mmsi:
            raise ValueError("MMSI cannot be empty")

        timestamp = self._parse_timestamp(row["timestamp"])
        latitude = float(row["latitude"])
        longitude = float(row["longitude"])

        if not -90 <= latitude <= 90:
            raise ValueError(f"Invalid latitude: {latitude}")
        if not -180 <= longitude <= 180:
            raise ValueError(f"Invalid longitude: {longitude}")

        sog = self._parse_optional_float(row.get("sog"))
        cog = self._parse_optional_float(row.get("cog"))
        heading = self._parse_optional_float(row.get("heading"))
        imo = str(row["imo"]).strip() if row.get("imo") else None
        vessel_type = str(row["vessel_type"]).strip() if row.get("vessel_type") else None

        return AISPoint(
            mmsi=mmsi,
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            sog=sog,
            cog=cog,
            heading=heading,
            imo=imo,
            vessel_type=vessel_type,
        )

    def _parse_timestamp(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"):
            try:
                return datetime.strptime(str(value), fmt)
            except ValueError:
                continue
        raise ValueError(f"Cannot parse timestamp: {value}")

    def _parse_optional_float(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _build_tracks(self, points: list[AISPoint]) -> list[VesselTrack]:
        tracks: dict[str, list[AISPoint]] = {}
        for point in points:
            tracks.setdefault(point.mmsi, []).append(point)

        result = []
        for mmsi, track_points in tracks.items():
            if len(track_points) >= 2:
                track_points.sort(key=lambda p: p.timestamp)
                vessel_type = track_points[0].vessel_type
                result.append(VesselTrack(mmsi=mmsi, points=track_points, vessel_type=vessel_type))
        return result