from uuid import uuid4

from oceantrace_common.models import (
    CaseStatus,
    InvestigationCase,
    InvestigationRequest,
    InvestigationResult,
    PipelineStep,
)

from oceantrace_api.services.ais import SyntheticAISService
from oceantrace_api.services.detection import SyntheticSatelliteDetectionService
from oceantrace_api.services.drift import BaselineDriftService
from oceantrace_api.services.evidence import EvidenceService
from oceantrace_api.services.reporting import EvidenceGroundedReportService
from oceantrace_api.services.scenario import load_demo_scenario
from oceantrace_api.services.scoring import TransparentCandidateScoringService


class InvestigationPipelineService:
    def __init__(self) -> None:
        self.detection_service = SyntheticSatelliteDetectionService()
        self.drift_service = BaselineDriftService()
        self.ais_service = SyntheticAISService()
        self.scoring_service = TransparentCandidateScoringService()
        self.evidence_service = EvidenceService()
        self.reporting_service = EvidenceGroundedReportService()

    def run_demo(self, case_number: str = "OT-2026-0001") -> InvestigationResult:
        scenario = load_demo_scenario(case_number)
        observation = self.detection_service.create_observation(scenario)
        detection = self.detection_service.detect(observation, scenario)
        drift = self.drift_service.run_monte_carlo(detection, scenario)
        tracks = self.ais_service.build_tracks(scenario)
        candidates = self.scoring_service.score_candidates(
            tracks,
            self.ais_service.vessel_names,
            scenario.origin_latitude,
            scenario.origin_longitude,
            scenario.observed_latitude,
            scenario.observed_longitude,
            scenario.release_time,
        )
        evidence = self.evidence_service.collect(candidates)
        case_id = uuid4()
        report = self.reporting_service.generate(case_id, candidates, evidence)
        case = InvestigationCase(
            id=case_id,
            case_number=scenario.case_number,
            status=CaseStatus.COMPLETE,
            observation=observation,
            detections=[detection],
            drift_simulations=[drift],
            candidates=candidates,
            evidence=evidence,
            report=report,
        )
        return InvestigationResult(
            case=case,
            steps=self._steps(candidates_count=len(candidates), evidence_count=len(evidence)),
            tracks=tracks,
            ground_truth_mmsi=scenario.ground_truth_mmsi,
        )

    def run_investigation(self, request: InvestigationRequest) -> InvestigationResult:
        scenario = load_demo_scenario(request.case_number)
        detection = self.detection_service.detect(request.observation, scenario)
        drift = self.drift_service.run_monte_carlo(detection, scenario)
        tracks = request.ais_dataset.tracks if request.ais_dataset is not None else []
        candidates = self.scoring_service.score_candidates(
            tracks,
            self.ais_service.vessel_names,
            scenario.origin_latitude,
            scenario.origin_longitude,
            scenario.observed_latitude,
            scenario.observed_longitude,
            scenario.release_time,
        )
        evidence = self.evidence_service.collect(candidates)
        case_id = uuid4()
        report = self.reporting_service.generate(case_id, candidates, evidence)
        case = InvestigationCase(
            id=case_id,
            case_number=request.case_number,
            status=CaseStatus.COMPLETE,
            observation=request.observation,
            detections=[detection],
            drift_simulations=[drift],
            candidates=candidates,
            evidence=evidence,
            report=report,
        )
        return InvestigationResult(
            case=case,
            steps=self._steps(candidates_count=len(candidates), evidence_count=len(evidence)),
            tracks=tracks,
        )

    def _steps(self, candidates_count: int, evidence_count: int) -> list[PipelineStep]:
        return [
            PipelineStep(
                name="Satellite processed",
                status="complete",
                detail="Synthetic SAR fixture loaded.",
            ),
            PipelineStep(
                name="Spill detected",
                status="complete",
                detail="Segmentation contract returned mask geometry.",
            ),
            PipelineStep(
                name="Drift simulation complete",
                status="complete",
                detail="Backward and forecast regions estimated.",
            ),
            PipelineStep(
                name="AIS candidates found",
                status="complete",
                detail=f"{candidates_count} vessel tracks scored.",
            ),
            PipelineStep(
                name="Evidence retrieved",
                status="complete",
                detail=f"{evidence_count} cited evidence records attached.",
            ),
            PipelineStep(
                name="Report generated",
                status="complete",
                detail="Claims include evidence IDs and uncertainty.",
            ),
        ]
