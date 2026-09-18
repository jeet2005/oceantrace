from oceantrace_common.models import Evidence, VesselCandidate


class EvidenceService:
    def collect(self, candidates: list[VesselCandidate]) -> list[Evidence]:
        evidence = [
            Evidence(
                id="detection-001",
                source="Synthetic detector",
                title="SAR oil slick segmentation output",
                reference="data/samples/synthetic_sar_observation.json",
                excerpt=(
                    "The detector output forms an elongated slick polygon with "
                    "confidence metadata."
                ),
            ),
            Evidence(
                id="drift-ensemble-001",
                source="Baseline drift engine",
                title="Backward Monte Carlo origin estimate",
                reference="data/processed/demo_drift.json",
                excerpt=(
                    "A 250-particle ensemble places the probable release region "
                    "west-southwest of the observed slick."
                ),
            ),
            Evidence(
                id="guidance-001",
                source="Local maritime investigation notes",
                title="Attribution caution",
                reference="docs/ais-attribution.md",
                excerpt=(
                    "AIS gaps and behavioral anomalies are investigative features, "
                    "not proof of wrongdoing."
                ),
            ),
        ]
        for candidate in candidates:
            evidence.append(
                Evidence(
                    id=f"ais-{candidate.mmsi}",
                    source="Synthetic AIS fixture",
                    title=f"{candidate.vessel_name} track near reconstructed origin",
                    reference="data/samples/synthetic_ais.csv",
                    excerpt=(
                        f"{candidate.vessel_name} received an investigative score of "
                        f"{candidate.score.total}/100 from deterministic AIS features."
                    ),
                )
            )
        return evidence
