from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from ai_vastu.auth import AuthenticatedUser, AuthenticationError
from ai_vastu.requirements.models import ConfirmedRequirements, Direction
from app import billing_routes, confirmed_generation_routes, requirements_routes
from app.main import create_app

USER = UUID("11111111-1111-1111-1111-111111111111")
OTHER = UUID("22222222-2222-2222-2222-222222222222")
PROJECT = UUID("33333333-3333-3333-3333-333333333333")
DRAFT = UUID("44444444-4444-4444-4444-444444444444")
AUTH = {"Authorization": "Bearer injected-token"}


def _client(*, owner: bool = True) -> tuple[TestClient, MagicMock, MagicMock]:
    repository = MagicMock()
    repository.is_project_owner.return_value = owner
    verifier = MagicMock()
    verifier.verify.return_value = AuthenticatedUser(user_id=USER, role="authenticated")
    client = TestClient(
        create_app(
            repository=repository,
            access_token_verifier=verifier,
            generation_intake_store=MagicMock(),
        )
    )
    return client, repository, verifier


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("get", "/projects", {}),
        ("get", "/billing/me", {}),
        ("get", f"/requirements/drafts/{DRAFT}", {}),
        (
            "post",
            f"/confirmed-generation/projects/{PROJECT}",
            {"json": {"draft_id": str(DRAFT), "accept_profile_defaults": True}},
        ),
    ],
)
@pytest.mark.parametrize("header", [{}, {"Authorization": "Bearer rejected"}])
def test_all_route_families_use_injected_verifier_and_bearer_challenge(
    method: str,
    path: str,
    kwargs: dict[str, object],
    header: dict[str, str],
) -> None:
    client, repository, verifier = _client()
    verifier.verify.side_effect = AuthenticationError("invalid claims")

    response = client.request(method, path, headers=header, **kwargs)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    if header:
        verifier.verify.assert_called_once_with("rejected")
    else:
        verifier.verify.assert_not_called()
    repository.is_project_owner.assert_not_called()


@pytest.mark.parametrize(
    ("method", "path", "kwargs", "factory"),
    [
        (
            "post",
            "/requirements/interpret",
            {"data": {"project_id": str(PROJECT), "prompt": "home"}},
            "requirements",
        ),
        ("post", f"/billing/projects/{PROJECT}/register", {}, "billing"),
        ("get", f"/billing/projects/{PROJECT}/generation-authorization", {}, "billing"),
        ("post", f"/billing/projects/{PROJECT}/generation-succeeded", {}, "billing"),
        (
            "post",
            f"/confirmed-generation/projects/{PROJECT}",
            {"json": {"draft_id": str(DRAFT), "accept_profile_defaults": True}},
            "confirmed",
        ),
    ],
)
def test_foreign_project_is_concealed_before_provider_storage_or_entitlements(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    kwargs: dict[str, object],
    factory: str,
) -> None:
    client, repository, verifier = _client(owner=False)
    unavailable = MagicMock(side_effect=AssertionError("side effect before ownership"))
    if factory == "requirements":
        monkeypatch.setattr(requirements_routes, "_service", unavailable)
    elif factory == "billing":
        monkeypatch.setattr(billing_routes, "_service", unavailable)
    else:
        monkeypatch.setattr(confirmed_generation_routes, "create_billing_repository", unavailable)

    response = client.request(method, path, headers=AUTH, **kwargs)

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]
    verifier.verify.assert_called_once_with("injected-token")
    repository.is_project_owner.assert_called_once_with(PROJECT, USER)
    unavailable.assert_not_called()


@pytest.mark.parametrize("path_suffix", ["", "/confirmed"])
@pytest.mark.parametrize("stored_user", [USER, OTHER])
@pytest.mark.parametrize("owner", [True, False])
def test_stored_requirement_reads_require_user_identity_and_current_project_ownership(
    monkeypatch: pytest.MonkeyPatch,
    path_suffix: str,
    stored_user: UUID,
    owner: bool,
) -> None:
    client, repository, _ = _client(owner=owner)
    record = SimpleNamespace(
        user_id=stored_user,
        project_id=PROJECT,
        ready_for_confirmation=True,
        model_dump=lambda **_kwargs: {"draft_id": str(DRAFT)},
    )
    store = MagicMock()
    store.get_draft.return_value = record
    store.get_confirmed.return_value = record
    monkeypatch.setattr(requirements_routes.RequirementsStore, "from_environment", lambda: store)

    response = client.get(f"/requirements/drafts/{DRAFT}{path_suffix}", headers=AUTH)

    assert response.status_code == (200 if owner and stored_user == USER else 404)
    if stored_user == USER:
        repository.is_project_owner.assert_called_once_with(PROJECT, USER)
    else:
        repository.is_project_owner.assert_not_called()


def test_confirmation_checks_current_project_owner_before_store_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, repository, _ = _client(owner=False)
    store = MagicMock()
    store.get_draft.return_value = SimpleNamespace(user_id=USER, project_id=PROJECT)
    unavailable = MagicMock(side_effect=AssertionError("provider created before ownership"))
    monkeypatch.setattr(requirements_routes.RequirementsStore, "from_environment", lambda: store)
    monkeypatch.setattr(requirements_routes, "_service", unavailable)
    confirmed = ConfirmedRequirements(
        draft_id=DRAFT,
        user_id=USER,
        project_id=PROJECT,
        user_confirmed=True,
        plot_width_mm=9144,
        plot_depth_mm=15240,
        north_rotation_deg=0,
        road_side=Direction.E,
        floor_count=1,
        bedroom_count=2,
    )

    response = client.post(
        f"/requirements/drafts/{DRAFT}/confirm",
        headers=AUTH,
        json=confirmed.model_dump(mode="json"),
    )

    assert response.status_code == 404
    repository.is_project_owner.assert_called_once_with(PROJECT, USER)
    unavailable.assert_not_called()


def test_public_catalog_and_signed_webhook_have_no_user_bearer_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, verifier = _client()
    catalog = client.get("/billing/catalog")
    monkeypatch.setattr(billing_routes, "_require_razorpay_gateway", lambda: None)
    webhook = client.post("/billing/webhooks/razorpay", json={})

    assert catalog.status_code == 200
    assert webhook.status_code == 400
    assert webhook.json()["detail"] == "Missing Razorpay signature."
    verifier.verify.assert_not_called()
