from fastapi.testclient import TestClient
from oceantrace_api.main import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_investigation() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v1/investigations", json={"case_number": "OT-2026-0001"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_number"] == "OT-2026-0001"
    assert payload["status"] == "complete"


def test_fixture_investigation_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/dev/fixtures/investigations")

    assert response.status_code == 200
    payload = response.json()
    assert payload["case"]["status"] == "complete"
    assert payload["case"]["candidates"][0]["mmsi"] == payload["ground_truth_mmsi"]


def test_demo_job_and_case_lookup() -> None:
    client = TestClient(create_app())
    job_response = client.post("/api/v1/dev/fixtures/investigations/jobs")

    assert job_response.status_code == 200
    job = job_response.json()
    assert job["status"] == "complete"

    case_response = client.get(f"/api/v1/investigations/{job['case_id']}")
    assert case_response.status_code == 200
    assert case_response.json()["case"]["id"] == job["case_id"]


def test_candidate_detail_and_ask_are_evidence_grounded() -> None:
    client = TestClient(create_app())
    result = client.post("/api/v1/dev/fixtures/investigations").json()
    case_id = result["case"]["id"]
    mmsi = result["case"]["candidates"][0]["mmsi"]

    candidate_response = client.get(f"/api/v1/investigations/{case_id}/candidates/{mmsi}")
    assert candidate_response.status_code == 200
    assert candidate_response.json()["evidence"]

    ask_response = client.post(
        f"/api/v1/investigations/{case_id}/ask",
        json={"question": "Why is the top vessel ranked first?"},
    )
    assert ask_response.status_code == 200
    assert ask_response.json()["evidence_ids"]


def test_run_investigation_from_structured_payload() -> None:
    client = TestClient(create_app())
    fixture = client.get("/api/v1/dev/fixtures/investigations").json()
    response = client.post(
        "/api/v1/investigations/run",
        json={
            "case_number": "OT-2026-0099",
            "observation": fixture["case"]["observation"],
            "ais_dataset": {
                "source_uri": "memory://fixture",
                "points": [point for track in fixture["tracks"] for point in track["points"]],
                "tracks": fixture["tracks"],
                "rejected_rows": 0,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["case"]["case_number"] == "OT-2026-0099"
    assert len(payload["case"]["candidates"]) == 3
