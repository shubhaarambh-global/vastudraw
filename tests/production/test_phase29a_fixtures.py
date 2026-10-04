from __future__ import annotations

from pathlib import Path

import pytest
from tests.production.test_settings import base_environment

from ai_vastu.production.settings import (
    ProductionConfigurationError,
    load_production_settings,
)


@pytest.fixture
def qualified_production_environment(tmp_path: Path) -> dict[str, str]:
    """Small, secret-free baseline for production configuration boundary cases."""
    return base_environment(tmp_path)


@pytest.mark.parametrize(
    "name",
    [
        "AI_VASTU_RATE_LIMIT_INTERPRET_PER_HOUR",
        "AI_VASTU_RATE_LIMIT_GENERATION_PER_HOUR",
        "AI_VASTU_RATE_LIMIT_PLAN_ANALYSIS_PER_HOUR",
        "AI_VASTU_RATE_LIMIT_CHECKOUT_PER_HOUR",
        "AI_VASTU_RATE_LIMIT_PAYMENT_STATUS_PER_HOUR",
        "AI_VASTU_RATE_LIMIT_PAYMENT_WEBHOOK_PER_HOUR",
        "AI_VASTU_HSTS_SECONDS",
    ],
)
@pytest.mark.parametrize("value", ["0", "-1", "not-a-number", "1.5"])
def test_production_rejects_nonpositive_or_noninteger_limits(
    qualified_production_environment: dict[str, str], name: str, value: str
) -> None:
    qualified_production_environment[name] = value

    with pytest.raises(ProductionConfigurationError, match=name):
        load_production_settings(qualified_production_environment)


def test_phonepe_selection_ignores_configured_razorpay_secrets(
    qualified_production_environment: dict[str, str],
) -> None:
    env = qualified_production_environment
    env.update(
        {
            "AI_VASTU_PAYMENT_GATEWAY": "phonepe",
            "AI_VASTU_RAZORPAY_KEY_ID": "rzp_live_unused",
            "AI_VASTU_RAZORPAY_KEY_SECRET": "razorpay-unused-secret",
            "AI_VASTU_RAZORPAY_WEBHOOK_SECRET": "webhook-unused-secret",
            "AI_VASTU_RAZORPAY_MONTHLY_PLAN_ID": "unused-monthly-plan",
            "AI_VASTU_RAZORPAY_YEARLY_PLAN_ID": "unused-yearly-plan",
        }
    )

    settings = load_production_settings(env)

    assert settings.payment_gateway == "phonepe"
    assert settings.razorpay_key_id is None
    assert settings.razorpay_key_secret is None
    assert settings.razorpay_webhook_secret is None
    assert settings.razorpay_monthly_plan_id is None
    assert settings.razorpay_yearly_plan_id is None
    summary = str(settings.redacted_summary())
    for secret in ("rzp_live_unused", "razorpay-unused-secret", "webhook-unused-secret"):
        assert secret not in summary


@pytest.mark.parametrize(
    "name",
    [
        "AI_VASTU_RAZORPAY_KEY_ID",
        "AI_VASTU_RAZORPAY_KEY_SECRET",
        "AI_VASTU_RAZORPAY_WEBHOOK_SECRET",
        "AI_VASTU_RAZORPAY_MONTHLY_PLAN_ID",
        "AI_VASTU_RAZORPAY_YEARLY_PLAN_ID",
    ],
)
def test_selected_razorpay_rejects_whitespace_only_credentials(
    qualified_production_environment: dict[str, str], name: str
) -> None:
    env = qualified_production_environment
    env.update(
        {
            "AI_VASTU_PAYMENT_GATEWAY": "razorpay",
            "AI_VASTU_RAZORPAY_KEY_ID": "rzp_live_fixture",
            "AI_VASTU_RAZORPAY_KEY_SECRET": "fixture-secret",
            "AI_VASTU_RAZORPAY_WEBHOOK_SECRET": "fixture-webhook-secret",
            "AI_VASTU_RAZORPAY_MONTHLY_PLAN_ID": "fixture-monthly",
            "AI_VASTU_RAZORPAY_YEARLY_PLAN_ID": "fixture-yearly",
        }
    )
    env[name] = "   "

    with pytest.raises(ProductionConfigurationError, match=name):
        load_production_settings(env)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("AI_VASTU_SUPABASE_URL", "https://:@project.supabase.co"),
        ("AI_VASTU_SUPABASE_URL", "https://%65xample.supabase.co"),
        ("AI_VASTU_WEB_ORIGINS", "https://:@app.example.com"),
        ("AI_VASTU_WEB_ORIGINS", "https://%65xample.example.com"),
        ("AI_VASTU_DATABASE_URL", "postgresql://db.example.com:99999/vastu"),
    ],
)
def test_production_rejects_malformed_authority_components(
    qualified_production_environment: dict[str, str], name: str, value: str
) -> None:
    qualified_production_environment[name] = value

    with pytest.raises(ProductionConfigurationError, match=name):
        load_production_settings(qualified_production_environment)


@pytest.mark.parametrize(
    "name", ["AI_VASTU_REQUIREMENTS_PATH", "AI_VASTU_GENERATION_UPLOAD_ROOT"]
)
def test_production_rejects_home_relative_storage_roots(
    qualified_production_environment: dict[str, str], name: str
) -> None:
    qualified_production_environment[name] = "~/durable-store"

    with pytest.raises(ProductionConfigurationError, match=name):
        load_production_settings(qualified_production_environment)


def test_invalid_model_policy_error_does_not_echo_environment_value(
    qualified_production_environment: dict[str, str],
) -> None:
    secret_shaped_value = "secret-shaped-invalid-model"
    qualified_production_environment["AI_VASTU_NVIDIA_PRIMARY_MODEL"] = (
        secret_shaped_value
    )

    with pytest.raises(ProductionConfigurationError) as captured:
        load_production_settings(qualified_production_environment)

    assert secret_shaped_value not in str(captured.value)
