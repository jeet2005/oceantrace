import json
from datetime import datetime
from pathlib import Path
from typing import Any

from oceantrace_common.models import SatelliteObservation


class SatelliteObservationIngestionService:
    def load_metadata(self, source: Path) -> SatelliteObservation:
        payload = json.loads(source.read_text(encoding="utf-8"))
        bbox = payload.get("bbox")
        return SatelliteObservation(
            captured_at=datetime.fromisoformat(str(payload["captured_at"]).replace("Z", "+00:00")),
            sensor=str(payload["sensor"]),
            source_uri=str(payload.get("source_uri", source)),
            bbox=tuple(bbox) if bbox is not None else None,
            metadata=self._metadata(payload),
        )

    def _metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in payload.items()
            if key not in {"captured_at", "sensor", "source_uri", "bbox"}
        }

