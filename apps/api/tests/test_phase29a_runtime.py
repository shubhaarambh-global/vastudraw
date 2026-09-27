from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from ai_vastu.auth import AuthenticatedUser
from ai_vastu.production import middleware as production_middleware
from ai_vastu.production.settings import ProductionConfigurationError
from app import billing_routes, main


def _production_client(
    monkeypatch: pytest.MonkeyPatch,
    gateway: str = "disabled",
    *,
    rate_limiter: MagicMock | None = None,
) -> TestClient:
    settings = SimpleNamespace(
        allowed_origins=("https://app.example.test",),
        trusted_hosts=("api.example.test",),
        payment_gateway=gateway,
        database_url="postgresql://unused.example.test/vastu",
        rate_limit_interpret_per_hour=20,
        rate_limit_generation_per_hour=10,
        rate_limit_plan_analysis_per_hour=10,
        rate_limit_checkout_per_hour=20,
        hsts_seconds=31_536_000,
    )
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AI_VASTU_WEB_ORIGINS", "https://ignored.example.test")
    monkeypatch.setenv("AI_VASTU_PAYMENT_GATEWAY", gateway)
    monkeypatch.setattr(main, "load_production_settings", lambda: settings)
    monkeypatch.setattr(production_middleware, "load_production_settings", lambda: settings)
    monkeypatch.setattr(billing_routes, "load_production_settings", lambda: settings)
    monkeypatch.setattr(
        production_middleware,
        "consume_postgres_fixed_window",
        rate_limiter or (lambda **_kwargs: SimpleNamespace(allowed=True)),
    )
    verifier = MagicMock()
    verifier.verify.return_value = AuthenticatedUser(
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        role="authenticated",
    )
    return TestClient(
        main.create_app(
            repository=MagicMock(),
            access_token_verifier=verifier,
            generation_intake_store=MagicMock(),
        ),
        base_url="https://api.example.test",
    )


def test_production_rejects_invalid_configuration_before_repository_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_factory = MagicMock()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(main, "create_project_repository_from_environment", repository_factory)
    monkeypatch.setattr(
        main,
        "load_production_settings",
        MagicMock(side_effect=ProductionConfigurationError("invalid production configuration")),
    )

    with pytest.raises(ProductionConfigurationError, match="invalid production configuration"):
        main.create_app()

    repository_factory.assert_not_called()


def test_production_cors_and_trusted_hosts_use_validated_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _production_client(monkeypatch)
    preflight_headers = {
        "Origin": "https://app.example.test",
        "Access-Control-Request-Method": "GET",
    }

    allowed = client.options("/health", headers=preflight_headers)
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://app.example.test"

    disallowed_origin = client.options(
        "/health",
        headers={**preflight_headers, "Origin": "https://ignored.example.test"},
    )
    assert disallowed_origin.status_code == 400
    assert "access-control-allow-origin" not in disallowed_origin.headers

    disallowed_host = client.get("/health", headers={"Host": "other.example.test"})
    assert disallowed_host.status_code == 400
    assert client.get("/health").status_code == 200


def test_untrusted_host_is_rejected_before_rate_limit_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rate_limiter = MagicMock(return_value=SimpleNamespace(allowed=True))
    client = _production_client(monkeypatch, rate_limiter=rate_limiter)

    response = client.post(
        "/billing/checkout",
        headers={"Host": "evil.example.test"},
        json={"sku": "project_single"},
    )

    assert response.status_code == 400
    rate_limiter.assert_not_called()


def test_allowed_origin_receives_cors_on_plan_analysis_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rate_limiter = MagicMock(return_value=SimpleNamespace(allowed=False))
    client = _production_client(monkeypatch, rate_limiter=rate_limiter)

    response = client.post(
        "/projects/11111111-1111-1111-1111-111111111111/"
        "generation-intakes/22222222-2222-2222-2222-222222222222/plan-analysis",
        headers={"Origin": "https://app.example.test"},
    )

    assert response.status_code == 429
    assert response.headers["access-control-allow-origin"] == "https://app.example.test"
    rate_limiter.assert_called_once()
    assert rate_limiter.call_args.kwargs["scope"] == "plan_analysis"


def test_rotating_authorization_headers_do_not_create_new_rate_limit_buckets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rate_limiter = MagicMock(return_value=SimpleNamespace(allowed=False))
    client = _production_client(monkeypatch, rate_limiter=rate_limiter)

    for token in ("first-token", "rotated-token"):
        response = client.post(
            "/requirements/interpret",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 429

    assert rate_limiter.call_count == 2
    first_key = rate_limiter.call_args_list[0].kwargs["key_hash"]
    second_key = rate_limiter.call_args_list[1].kwargs["key_hash"]
    assert first_key == second_key


def test_allowed_origin_receives_cors_on_runtime_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _production_client(monkeypatch)
    monkeypatch.setattr(
        production_middleware,
        "load_production_settings",
        MagicMock(side_effect=ProductionConfigurationError("secret-shaped detail")),
    )

    response = client.get(
        "/health",
        headers={"Origin": "https://app.example.test"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Production configuration is invalid."}
    assert response.headers["access-control-allow-origin"] == "https://app.example.test"
    assert "secret-shaped detail" not in response.text


def test_allowed_origin_receives_cors_when_rate_limit_storage_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rate_limiter = MagicMock(side_effect=RuntimeError("storage-secret-shaped-detail"))
    client = _production_client(monkeypatch, rate_limiter=rate_limiter)

    response = client.post(
        "/projects/11111111-1111-1111-1111-111111111111/"
        "generation-intakes/22222222-2222-2222-2222-222222222222/plan-analysis",
        headers={"Origin": "https://app.example.test"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Rate-limit service unavailable."}
    assert response.headers["access-control-allow-origin"] == "https://app.example.test"
    assert "storage-secret-shaped-detail" not in response.text


def test_plan_analysis_get_and_confirmation_are_not_rate_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rate_limiter = MagicMock(return_value=SimpleNamespace(allowed=False))
    client = _production_client(monkeypatch, rate_limiter=rate_limiter)
    base_path = (
        "/projects/11111111-1111-1111-1111-111111111111/"
        "generation-intakes/22222222-2222-2222-2222-222222222222"
    )

    analysis = client.get(f"{base_path}/plan-analysis")
    confirmation = client.post(f"{base_path}/plan-confirmation", json={})

    assert analysis.status_code == 401
    assert confirmation.status_code == 401
    rate_limiter.assert_not_called()


@pytest.mark.parametrize("gateway", ["phonepe", "disabled"])
def test_unavailable_gateway_blocks_razorpay_before_provider_or_entitlement_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    gateway: str,
) -> None:
    client = _production_client(monkeypatch, gateway)
    provider_factory = MagicMock(side_effect=AssertionError("Razorpay must not be constructed"))
    billing_service = MagicMock(side_effect=AssertionError("Billing service must not be opened"))
    monkeypatch.setattr(billing_routes.RazorpayClient, "from_environment", provider_factory)
    monkeypatch.setattr(billing_routes, "_service", billing_service)

    checkout = client.post(
        "/billing/checkout",
        json={"sku": "project_credit"},
        headers={"Authorization": "Bearer injected-token"},
    )
    webhook = client.post(
        "/billing/webhooks/razorpay",
        json={"event": "payment_link.paid"},
        headers={"X-Razorpay-Signature": "unused"},
    )

    assert checkout.status_code == 503
    assert webhook.status_code == 503
    assert "Razorpay payments are unavailable" in checkout.json()["detail"]
    assert "Razorpay payments are unavailable" in webhook.json()["detail"]
    provider_factory.assert_not_called()
    billing_service.assert_not_called()
