from fastapi.testclient import TestClient

from app.main import create_app


def test_release_readiness_endpoint_reports_ready_after_phase20b() -> None:
    client = TestClient(create_app())
    response = client.get("/system/release-readiness")
    assert response.status_code == 200
    payload = response.json()
    assert payload["disposition"] == "READY"
    assert payload["blocker_codes"] == []
    assert payload["blocker_count"] == 0
    assert payload["report_hash"] is not None
