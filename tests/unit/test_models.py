from datetime import UTC, datetime

import pytest
from oceantrace_common.models import AISPoint
from pydantic import ValidationError


def test_ais_point_rejects_invalid_coordinates() -> None:
    with pytest.raises(ValidationError):
        AISPoint(mmsi="123456789", timestamp=datetime.now(tz=UTC), latitude=99, longitude=73)


def test_ais_point_normalizes_mmsi() -> None:
    point = AISPoint(mmsi=" 123456789 ", timestamp=datetime.now(tz=UTC), latitude=12, longitude=73)

    assert point.mmsi == "123456789"

