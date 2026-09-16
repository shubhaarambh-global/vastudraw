from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from ai_vastu.auth import (
    AuthConfigurationError,
    DevelopmentAccessTokenVerifier,
    create_access_token_verifier_from_environment,
)
from ai_vastu.projects import SqliteProjectRepository
from app.main import create_app

USER_A = UUID("aaaaaaaa-1111-1111-1111-111111111111")
USER_B = UUID("bbbbbbbb-2222-2222-2222-222222222222")
TOKEN_A = "test-token-a"
TOKEN_B = "test-token-b"


def _client(user_id: UUID, token: str, repository: SqliteProjectRepository) -> TestClient:
    return TestClient(
        create_app(
            repository,
            DevelopmentAccessTokenVerifier(token, user_id),
        )
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_project_endpoints_require_bearer_authentication() -> None:
    repository = SqliteProjectRepository(":memory:")
    client = _client(USER_A, TOKEN_A, repository)
    response = client.get("/projects")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_project_ownership_isolated_between_authenticated_users() -> None:
    repository = SqliteProjectRepository(":memory:")
    client_a = _client(USER_A, TOKEN_A, repository)
    project_id = UUID("cccccccc-3333-3333-3333-333333333333")
    created = client_a.post(
        "/projects",
        json={"name": "Owner A", "project_id": str(project_id)},
        headers=_auth(TOKEN_A),
    )
    assert created.status_code == 201

    # A second app instance shares the repository but authenticates a different user.
    client_b = _client(USER_B, TOKEN_B, repository)
    hidden = client_b.get(f"/projects/{project_id}", headers=_auth(TOKEN_B))
    assert hidden.status_code == 404
    listed = client_b.get("/projects", headers=_auth(TOKEN_B))
    assert listed.status_code == 200
    assert listed.json() == []

    owner_list = client_a.get("/projects", headers=_auth(TOKEN_A))
    assert owner_list.status_code == 200
    assert [item["project_id"] for item in owner_list.json()] == [str(project_id)]


def test_production_authentication_fails_closed_without_supabase_configuration() -> None:
    with pytest.raises(AuthConfigurationError):
        create_access_token_verifier_from_environment({"APP_ENV": "production"})


def test_production_forbids_development_authentication() -> None:
    with pytest.raises(AuthConfigurationError):
        create_access_token_verifier_from_environment(
            {
                "APP_ENV": "production",
                "AI_VASTU_AUTH_MODE": "development",
                "AI_VASTU_SUPABASE_URL": "https://example.supabase.co",
            }
        )
