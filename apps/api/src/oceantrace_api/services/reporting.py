from uuid import UUID

from oceantrace_common.models import Evidence, InvestigationReport, VesselCandidate


class EvidenceGroundedReportService:
    def generate(
        self,
        case_id: UUID,
        candidates: list[VesselCandidate],
        evidence: list[Evidence],
    ) -> InvestigationReport:
        top_candidate = candidates[0] if candidates else None
        candidate_claim = (
            f"{top_candidate.vessel_name} is the highest-ranked investigative candidate."
            if top_candidate is not None
            else "No AIS vessel candidates were available for ranking."
        )
        candidate_evidence = (
            [f"ais-{top_candidate.mmsi}", "drift-ensemble-001"]
            if top_candidate is not None
            else ["drift-ensemble-001"]
        )
        candidate_confidence = top_candidate.score.total / 100 if top_candidate is not None else 0
        return InvestigationReport(
            case_id=case_id,
            executive_summary=(
                "The demo pipeline detected a synthetic slick, reconstructed a probable "
                "release window, ranked nearby AIS tracks, and produced evidence-linked "
                "investigative findings. The top candidate is not a definitive attribution."
            ),
            evidence_ids=[item.id for item in evidence],
            claims=[
                {
                    "claim": "A slick-like polygon was detected in the synthetic SAR fixture.",
                    "evidence_ids": ["detection-001"],
                    "confidence": 0.91,
                },
                {
                    "claim": (
                        "The origin estimate is a region and time window, not an exact coordinate."
                    ),
                    "evidence_ids": ["drift-ensemble-001"],
                    "confidence": 0.73,
                },
                {
                    "claim": candidate_claim,
                    "evidence_ids": candidate_evidence,
                    "confidence": candidate_confidence,
                },
            ],
        )
