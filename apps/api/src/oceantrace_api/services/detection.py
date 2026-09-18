from oceantrace_common.models import SatelliteObservation, SpillDetection, SpillGeometry

from oceantrace_api.services.geospatial import box
from oceantrace_api.services.scenario import DemoScenario


class SyntheticSatelliteDetectionService:
    def create_observation(self, scenario: DemoScenario) -> SatelliteObservation:
        return SatelliteObservation(
            captured_at=scenario.observation_time,
            sensor="Synthetic Sentinel-1 SAR fixture",
            source_uri="data/samples/synthetic_sar_observation.json",
            bbox=(72.8, 14.7, 73.5, 15.2),
        )

    def detect(self, observation: SatelliteObservation, scenario: DemoScenario) -> SpillDetection:
        geometry = SpillGeometry(
            polygon=box(scenario.observed_latitude, scenario.observed_longitude, 0.035, 0.085),
            centroid=(scenario.observed_latitude, scenario.observed_longitude),
            area_km2=11.8,
            perimeter_km=18.6,
            length_km=17.9,
            width_km=7.4,
        )
        return SpillDetection(
            observation_id=observation.id,
            confidence=0.91,
            uncertainty="medium; synthetic SAR fixture with look-alike checks pending",
            geometry=geometry,
            estimated_age_hours=2.5,
        )

