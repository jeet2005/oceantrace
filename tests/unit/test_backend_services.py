from oceantrace_api.services.ais import SyntheticAISService
from oceantrace_api.services.detection import SyntheticSatelliteDetectionService
from oceantrace_api.services.drift import BaselineDriftService
from oceantrace_api.services.scenario import load_demo_scenario
from oceantrace_api.services.scoring import TransparentCandidateScoringService


def test_services_compose_without_pipeline_shortcuts() -> None:
    scenario = load_demo_scenario()
    detector = SyntheticSatelliteDetectionService()
    observation = detector.create_observation(scenario)
    detection = detector.detect(observation, scenario)
    drift = BaselineDriftService().run_monte_carlo(detection, scenario)
    ais = SyntheticAISService()
    tracks = ais.build_tracks(scenario)
    candidates = TransparentCandidateScoringService().score_candidates(
        tracks,
        ais.vessel_names,
        scenario.origin_latitude,
        scenario.origin_longitude,
        scenario.observed_latitude,
        scenario.observed_longitude,
        scenario.release_time,
    )

    assert detection.confidence == 0.91
    assert drift.origin_region is not None
    assert len(tracks) == 3
    assert candidates[0].mmsi == scenario.ground_truth_mmsi
    assert candidates[0].score.total > candidates[-1].score.total


def test_candidate_scores_are_feature_bounded() -> None:
    scenario = load_demo_scenario()
    ais = SyntheticAISService()
    candidates = TransparentCandidateScoringService().score_candidates(
        ais.build_tracks(scenario),
        ais.vessel_names,
        scenario.origin_latitude,
        scenario.origin_longitude,
        scenario.observed_latitude,
        scenario.observed_longitude,
        scenario.release_time,
    )

    for candidate in candidates:
        score_values = candidate.score.model_dump().values()
        assert all(0 <= value <= 100 for value in score_values)
