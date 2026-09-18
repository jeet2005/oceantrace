from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class DemoScenario:
    case_number: str
    observation_time: datetime
    release_time: datetime
    origin_latitude: float
    origin_longitude: float
    observed_latitude: float
    observed_longitude: float
    ground_truth_mmsi: str


def load_demo_scenario(case_number: str = "OT-2026-0001") -> DemoScenario:
    return DemoScenario(
        case_number=case_number,
        observation_time=datetime(2026, 8, 20, 16, 10, tzinfo=UTC),
        release_time=datetime(2026, 8, 20, 13, 40, tzinfo=UTC),
        origin_latitude=14.92,
        origin_longitude=73.08,
        observed_latitude=15.04,
        observed_longitude=73.33,
        ground_truth_mmsi="419001247",
    )

