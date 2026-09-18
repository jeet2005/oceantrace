from datetime import timedelta

from oceantrace_common.models import DriftSimulation, SpillDetection

from oceantrace_api.services.geospatial import box
from oceantrace_api.services.scenario import DemoScenario


class BaselineDriftService:
    def run_monte_carlo(
        self,
        detection: SpillDetection,
        scenario: DemoScenario,
        particle_count: int = 250,
    ) -> DriftSimulation:
        return DriftSimulation(
            detection_id=detection.id,
            mode="monte_carlo",
            release_window_start=scenario.release_time - timedelta(minutes=50),
            release_window_end=scenario.release_time + timedelta(minutes=55),
            confidence=0.73,
            origin_region=box(scenario.origin_latitude, scenario.origin_longitude, 0.055, 0.07),
            forecast_corridor=box(15.13, 73.45, 0.08, 0.14),
            trajectory_count=particle_count,
        )

