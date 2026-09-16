from fastapi.testclient import TestClient

from app.main import create_app


def test_local_web_origin_is_allowed_for_project_posts() -> None:
    response = TestClient(create_app()).options(
        "/projects",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_authorization_header_is_allowed_by_cors() -> None:
    response = TestClient(create_app()).options(
        "/projects",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
