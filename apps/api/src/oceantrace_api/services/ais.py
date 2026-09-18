from datetime import timedelta

from oceantrace_common.models import AISPoint, VesselTrack

from oceantrace_api.services.scenario import DemoScenario


class SyntheticAISService:
    vessel_names = {
        "419001247": "MT Samudra",
        "419004118": "MV Konkan Star",
        "419007640": "MT Blue Kaveri",
    }

    def build_tracks(self, scenario: DemoScenario) -> list[VesselTrack]:
        return [
            self._track(
                "419001247",
                1,
                [(14.84, 72.90, 12, 80), (14.91, 73.06, 3, 210), (15.01, 73.25, 13, 360)],
                scenario,
            ),
            self._track(
                "419004118",
                2,
                [(14.77, 73.12, 11, 75), (14.88, 73.16, 10, 230), (15.11, 73.19, 11, 365)],
                scenario,
            ),
            self._track(
                "419007640",
                3,
                [(15.18, 72.98, 14, 65), (15.07, 73.01, 15, 260), (14.96, 73.04, 15, 355)],
                scenario,
            ),
        ]

    def _track(
        self,
        mmsi: str,
        name_seed: int,
        points: list[tuple[float, float, float, int]],
        scenario: DemoScenario,
    ) -> VesselTrack:
        base = scenario.observation_time - timedelta(hours=6, minutes=10)
        return VesselTrack(
            mmsi=mmsi,
            points=[
                AISPoint(
                    mmsi=mmsi,
                    timestamp=base + timedelta(minutes=offset),
                    latitude=lat,
                    longitude=lon,
                    sog=sog,
                    cog=90 + name_seed,
                    heading=90 + name_seed,
                    vessel_type="tanker" if name_seed != 3 else "cargo",
                )
                for lat, lon, sog, offset in points
            ],
        )

