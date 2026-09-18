from oceantrace_api.pipeline import build_demo_investigation


def test_demo_pipeline_ranks_ground_truth_first() -> None:
    result = build_demo_investigation()

    assert result.case.candidates
    assert result.ground_truth_mmsi == "419001247"
    assert result.case.candidates[0].mmsi == result.ground_truth_mmsi
    assert result.case.candidates[0].disclaimer.startswith("Investigative")


def test_demo_report_preserves_evidence_ids() -> None:
    result = build_demo_investigation()

    assert result.case.report is not None
    evidence_ids = {evidence.id for evidence in result.case.evidence}
    for claim in result.case.report.claims:
        assert set(claim["evidence_ids"]).issubset(evidence_ids)
