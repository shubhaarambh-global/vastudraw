from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from ai_vastu.architectural_brain.errors import (
    ArchitecturalBrainConfigurationError,
    ArchitecturalBrainProviderError,
)
from ai_vastu.architectural_intelligence import ArchitecturalIntelligenceProviderError
from ai_vastu.auth import AuthenticatedUser
from ai_vastu.multi_candidate import MultiCandidateGenerationError
from ai_vastu.provider_runtime import ProviderFailureCategory
from ai_vastu.requirements.errors import (
    RequirementsConfigurationError,
    RequirementsProviderError,
)
from ai_vastu.vastu_reasoning import VastuReasoningProviderError
from app import confirmed_generation_routes, requirements_routes
from app.main import create_app

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = UUID("33333333-3333-3333-3333-333333333333")
AUTH = {"Authorization": "Bearer phase29c-token"}


def _client() -> tuple[TestClient, MagicMock]:
    repository = MagicMock()
    repository.is_project_owner.return_value = True
    verifier = MagicMock()
    verifier.verify.return_value = AuthenticatedUser(
        user_id=USER_ID,
        role="authenticated",
    )
    return (
        TestClient(
            create_app(
                repository=repository,
                access_token_verifier=verifier,
                generation_intake_store=MagicMock(),
            )
        ),
        repository,
    )


@pytest.mark.parametrize(
    ("category", "status_code", "detail"),
    [
        (
            ProviderFailureCategory.AUTHENTICATION,
            503,
            "AI provider is unavailable.",
        ),
        (
            ProviderFailureCategory.RATE_LIMITED,
            503,
            "AI provider is unavailable.",
        ),
        (
            ProviderFailureCategory.UNAVAILABLE,
            503,
            "AI provider is unavailable.",
        ),
        (ProviderFailureCategory.TIMEOUT, 504, "AI provider timed out."),
        (
            ProviderFailureCategory.INVALID_RESPONSE,
            502,
            "AI provider returned an invalid response.",
        ),
        (
            ProviderFailureCategory.REQUEST_REJECTED,
            502,
            "AI provider returned an invalid response.",
        ),
    ],
)
def test_requirements_provider_errors_are_fixed_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    category: ProviderFailureCategory,
    status_code: int,
    detail: str,
) -> None:
    client, _ = _client()
    service = MagicMock()
    service.interpret.side_effect = RequirementsProviderError(category)
    monkeypatch.setattr(requirements_routes, "_service", lambda: service)

    response = client.post(
        "/requirements/interpret",
        headers=AUTH,
        data={"project_id": str(PROJECT_ID), "prompt": "private provider payload"},
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "private provider payload" not in response.text


def test_requirements_configuration_failure_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = _client()
    monkeypatch.setattr(
        requirements_routes,
        "_service",
        MagicMock(side_effect=RequirementsConfigurationError("secret setting")),
    )

    response = client.post(
        "/requirements/interpret",
        headers=AUTH,
        data={"project_id": str(PROJECT_ID), "prompt": "home"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "AI provider is not configured."}
    assert "secret setting" not in response.text


def test_requirements_provider_call_uses_threadpool_after_async_request_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = _client()
    service = MagicMock()
    draft = SimpleNamespace(
        ready_for_confirmation=False,
        model_dump=lambda **_kwargs: {"draft_id": str(DRAFT_ID)},
    )
    run_in_threadpool = AsyncMock(return_value=draft)
    monkeypatch.setattr(requirements_routes, "_service", lambda: service)
    monkeypatch.setattr(requirements_routes, "run_in_threadpool", run_in_threadpool)

    response = client.post(
        "/requirements/interpret",
        headers=AUTH,
        data={"project_id": str(PROJECT_ID), "prompt": "home"},
    )

    assert response.status_code == 200
    run_in_threadpool.assert_awaited_once_with(
        service.interpret,
        user_id=USER_ID,
        project_id=PROJECT_ID,
        prompt="home",
        references=(),
    )


@pytest.mark.parametrize(
    ("failure", "status_code", "detail"),
    [
        (
            ArchitecturalBrainConfigurationError("secret key missing"),
            503,
            "AI provider is not configured.",
        ),
        (
            ArchitecturalBrainProviderError(ProviderFailureCategory.TIMEOUT),
            504,
            "AI provider timed out.",
        ),
        (
            ArchitecturalIntelligenceProviderError(
                ProviderFailureCategory.INVALID_RESPONSE
            ),
            502,
            "AI provider returned an invalid response.",
        ),
        (
            VastuReasoningProviderError(ProviderFailureCategory.UNAVAILABLE),
            503,
            "AI provider is unavailable.",
        ),
    ],
)
def test_confirmed_generation_provider_failures_do_not_persist_or_bill(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    status_code: int,
    detail: str,
) -> None:
    client, project_repository = _client()
    billing_repository = MagicMock()
    monkeypatch.setattr(
        confirmed_generation_routes,
        "create_billing_repository",
        lambda: billing_repository,
    )
    monkeypatch.setattr(
        "app.confirmed_generation_routes.CandidateGenerationOrchestrator.preview",
        MagicMock(side_effect=failure),
    )

    response = client.post(
        f"/confirmed-generation/projects/{PROJECT_ID}/alternatives",
        headers=AUTH,
        json={
            "draft_id": str(DRAFT_ID),
            "accept_profile_defaults": True,
            "max_alternatives": 2,
        },
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "secret" not in response.text
    project_repository.append_revision.assert_not_called()
    billing_repository.record_successful_generation.assert_not_called()
    billing_repository.close.assert_called_once_with()


def test_deterministic_candidate_rejection_remains_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = _client()
    billing_repository = MagicMock()
    monkeypatch.setattr(
        confirmed_generation_routes,
        "create_billing_repository",
        lambda: billing_repository,
    )
    monkeypatch.setattr(
        "app.confirmed_generation_routes.CandidateGenerationOrchestrator.preview",
        MagicMock(side_effect=MultiCandidateGenerationError("candidate rejected")),
    )

    response = client.post(
        f"/confirmed-generation/projects/{PROJECT_ID}/alternatives",
        headers=AUTH,
        json={
            "draft_id": str(DRAFT_ID),
            "accept_profile_defaults": True,
            "max_alternatives": 2,
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "candidate rejected"}
    billing_repository.record_successful_generation.assert_not_called()
