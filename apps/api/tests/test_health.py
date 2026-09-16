from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "phase": "19",
        "plan_schema_version": "1.0.0",
    }
