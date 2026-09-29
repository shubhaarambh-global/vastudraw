from __future__ import annotations

from pathlib import Path

import pytest

from ai_vastu.openrouter_http import (
    FALLBACK_REASONING_MODEL,
    PRIMARY_ARCHITECTURAL_MODEL,
    VISION_PLAN_MODEL,
)
from ai_vastu.production.settings import (
    ProductionConfigurationError,
    load_production_settings,
)
from ai_vastu.provider_runtime import DEFAULT_GEMINI_BUDGET, DEFAULT_OPENROUTER_BUDGET


def base_environment(tmp_path: Path) -> dict[str, str]:
    return {
        "APP_ENV": "production",
        "AI_VASTU_AUTH_MODE": "supabase",
        "AI_VASTU_DATABASE_URL": "postgresql://user:pass@db.example.com:5432/vastu",
        "AI_VASTU_SUPABASE_URL": "https://example.supabase.co",
        "AI_VASTU_SUPABASE_JWT_AUDIENCE": "authenticated",
        "AI_VASTU_WEB_ORIGINS": "https://app.example.com",
        "AI_VASTU_TRUSTED_HOSTS": "api.example.com",
        "AI_VASTU_REQUIREMENTS_PATH": str((tmp_path / "requirements").resolve()),
        "AI_VASTU_GENERATION_UPLOAD_ROOT": str((tmp_path / "uploads").resolve()),
        "AI_VASTU_PAYMENT_GATEWAY": "phonepe",
        "AI_VASTU_PHONEPE_ENVIRONMENT": "production",
        "AI_VASTU_PHONEPE_CLIENT_ID": "phonepe-client-id",
        "AI_VASTU_PHONEPE_CLIENT_SECRET": "phonepe-client-secret",
        "AI_VASTU_PHONEPE_CLIENT_VERSION": "1",
        "AI_VASTU_PHONEPE_WEBHOOK_USERNAME": "phonepe-webhook-user",
        "AI_VASTU_PHONEPE_WEBHOOK_PASSWORD": "phonepe-webhook-password",
        "AI_VASTU_PHONEPE_REDIRECT_URL": "https://app.example.com/billing/return",
        "AI_VASTU_REQUIREMENTS_PROVIDER": "openrouter",
        "AI_VASTU_ARCHITECT_PROVIDER": "openrouter",
        "AI_VASTU_VASTU_PROVIDER": "openrouter",
        "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER": "openrouter",
        "AI_VASTU_REVISION_PROVIDER": "openrouter",
        "AI_VASTU_PLAN_RECOGNITION_PROVIDER": "gemini",
        "AI_VASTU_PLAN_RECOGNITION_MODEL": "gemini-3.1-flash-lite",
        "AI_VASTU_GEMINI_MODEL": "gemini-3.1-flash-lite",
        "AI_VASTU_OPENROUTER_PRIMARY_MODEL": PRIMARY_ARCHITECTURAL_MODEL,
        "AI_VASTU_OPENROUTER_VISION_MODEL": VISION_PLAN_MODEL,
        "AI_VASTU_OPENROUTER_FALLBACK_MODEL": FALLBACK_REASONING_MODEL,
        "AI_VASTU_OPENROUTER_ATTEMPT_TIMEOUT_SECONDS": "120",
        "AI_VASTU_OPENROUTER_TOTAL_TIMEOUT_SECONDS": "240",
        "AI_VASTU_OPENROUTER_RETRY_DELAY_SECONDS": "0",
        "AI_VASTU_OPENROUTER_MAX_RETRY_AFTER_SECONDS": "0",
        "AI_VASTU_GEMINI_ATTEMPT_TIMEOUT_SECONDS": "90",
        "AI_VASTU_GEMINI_TOTAL_TIMEOUT_SECONDS": "181",
        "AI_VASTU_GEMINI_RETRY_DELAY_SECONDS": "1",
        "AI_VASTU_GEMINI_MAX_RETRY_AFTER_SECONDS": "5",
        "OPENROUTER_API_KEY": "openrouter-test-secret",
        "GEMINI_API_KEY": "gemini-test-secret",
    }


def test_production_settings_accept_qualified_phonepe_configuration(tmp_path: Path) -> None:
    env = base_environment(tmp_path)
    settings = load_production_settings(env)

    assert settings.database_url == env["AI_VASTU_DATABASE_URL"]
    assert settings.supabase_jwt_audience == "authenticated"
    assert settings.allowed_origins == ("https://app.example.com",)
    assert settings.trusted_hosts == ("api.example.com",)
    assert settings.requirements_path == Path(env["AI_VASTU_REQUIREMENTS_PATH"])
    assert settings.generation_upload_root == Path(env["AI_VASTU_GENERATION_UPLOAD_ROOT"])
    assert settings.payment_gateway == "phonepe"
    assert settings.phonepe_environment == "production"
    assert settings.phonepe_redirect_url == "https://app.example.com/billing/return"
    assert settings.razorpay_key_id is None
    assert settings.rate_limit_generation_per_hour == 10
    assert settings.rate_limit_plan_analysis_per_hour == 10
    assert settings.rate_limit_payment_status_per_hour == 30
    assert settings.openrouter_budget == DEFAULT_OPENROUTER_BUDGET
    assert settings.gemini_budget == DEFAULT_GEMINI_BUDGET


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("AI_VASTU_OPENROUTER_ATTEMPT_TIMEOUT_SECONDS", "0"),
        ("AI_VASTU_OPENROUTER_TOTAL_TIMEOUT_SECONDS", "119"),
        ("AI_VASTU_OPENROUTER_RETRY_DELAY_SECONDS", "-1"),
        ("AI_VASTU_OPENROUTER_MAX_RETRY_AFTER_SECONDS", "nan"),
        ("AI_VASTU_GEMINI_ATTEMPT_TIMEOUT_SECONDS", "inf"),
        ("AI_VASTU_GEMINI_TOTAL_TIMEOUT_SECONDS", "89"),
        ("AI_VASTU_GEMINI_RETRY_DELAY_SECONDS", "-0.1"),
        ("AI_VASTU_GEMINI_MAX_RETRY_AFTER_SECONDS", "not-a-number"),
    ],
)
def test_production_settings_reject_invalid_provider_budgets(
    tmp_path: Path,
    name: str,
    value: str,
) -> None:
    env = base_environment(tmp_path)
    env[name] = value

    with pytest.raises(ProductionConfigurationError, match="Provider runtime budget"):
        load_production_settings(env)


def test_production_settings_use_shared_provider_budget_defaults(tmp_path: Path) -> None:
    env = base_environment(tmp_path)
    for prefix in ("AI_VASTU_OPENROUTER", "AI_VASTU_GEMINI"):
        for suffix in (
            "ATTEMPT_TIMEOUT_SECONDS",
            "TOTAL_TIMEOUT_SECONDS",
            "RETRY_DELAY_SECONDS",
            "MAX_RETRY_AFTER_SECONDS",
        ):
            env.pop(f"{prefix}_{suffix}")

    settings = load_production_settings(env)

    assert settings.openrouter_budget == DEFAULT_OPENROUTER_BUDGET
    assert settings.gemini_budget == DEFAULT_GEMINI_BUDGET


@pytest.mark.parametrize("mode", ["", "production", "development"])
def test_production_settings_require_supabase_auth(tmp_path: Path, mode: str) -> None:
    env = base_environment(tmp_path)
    env["AI_VASTU_AUTH_MODE"] = mode
    with pytest.raises(ProductionConfigurationError, match="AI_VASTU_AUTH_MODE"):
        load_production_settings(env)


@pytest.mark.parametrize("audience", ["", "anon", "authenticated,service_role"])
def test_production_settings_require_authenticated_audience(
    tmp_path: Path, audience: str
) -> None:
    env = base_environment(tmp_path)
    env["AI_VASTU_SUPABASE_JWT_AUDIENCE"] = audience
    with pytest.raises(ProductionConfigurationError, match="AI_VASTU_SUPABASE_JWT_AUDIENCE"):
        load_production_settings(env)


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", " TRUE "])
def test_production_settings_reject_development_billing_bypass(
    tmp_path: Path, value: str
) -> None:
    env = base_environment(tmp_path)
    env["AI_VASTU_DEV_BILLING_BYPASS"] = value
    with pytest.raises(ProductionConfigurationError, match="AI_VASTU_DEV_BILLING_BYPASS"):
        load_production_settings(env)


@pytest.mark.parametrize("value", ["", "sqlite:///tmp/test.db", "postgresql:///vastu"])
def test_production_settings_require_canonical_postgres_url(
    tmp_path: Path, value: str
) -> None:
    env = base_environment(tmp_path)
    env["AI_VASTU_DATABASE_URL"] = value
    env["DATABASE_URL"] = "postgresql://legacy.example.com/vastu"
    with pytest.raises(ProductionConfigurationError, match="AI_VASTU_DATABASE_URL"):
        load_production_settings(env)


@pytest.mark.parametrize(
    "origin",
    [
        "", "*", "http://app.example.com", "https://app.example.com/path",
        "https://app.example.com?x=1", "https://*.example.com",
        "https://app.example.com:invalid",
    ],
)
def test_production_settings_reject_non_explicit_https_origins(
    tmp_path: Path, origin: str
) -> None:
    env = base_environment(tmp_path)
    env["AI_VASTU_WEB_ORIGINS"] = origin
    env["AI_VASTU_ALLOWED_ORIGINS"] = "https://legacy.example.com"
    with pytest.raises(ProductionConfigurationError, match="AI_VASTU_WEB_ORIGINS"):
        load_production_settings(env)


@pytest.mark.parametrize(
    "hosts",
    ["", "*", "*.example.com", "https://api.example.com", "api.example.com/path"],
)
def test_production_settings_require_explicit_hosts(tmp_path: Path, hosts: str) -> None:
    env = base_environment(tmp_path)
    env["AI_VASTU_TRUSTED_HOSTS"] = hosts
    with pytest.raises(ProductionConfigurationError, match="AI_VASTU_TRUSTED_HOSTS"):
        load_production_settings(env)


@pytest.mark.parametrize(
    "url", ["https://example.supabase.co/path", "https://example.supabase.co?key=secret"]
)
def test_production_settings_require_supabase_project_origin(
    tmp_path: Path, url: str
) -> None:
    env = base_environment(tmp_path)
    env["AI_VASTU_SUPABASE_URL"] = url
    with pytest.raises(ProductionConfigurationError, match="AI_VASTU_SUPABASE_URL"):
        load_production_settings(env)


@pytest.mark.parametrize(
    "name", ["AI_VASTU_REQUIREMENTS_PATH", "AI_VASTU_GENERATION_UPLOAD_ROOT"]
)
def test_production_settings_require_absolute_durable_paths(
    tmp_path: Path, name: str
) -> None:
    env = base_environment(tmp_path)
    env[name] = ".local/data"
    with pytest.raises(ProductionConfigurationError, match=name):
        load_production_settings(env)


@pytest.mark.parametrize("gateway", ["", "automatic", "stripe"])
def test_production_settings_require_explicit_supported_gateway(
    tmp_path: Path, gateway: str
) -> None:
    env = base_environment(tmp_path)
    env["AI_VASTU_PAYMENT_GATEWAY"] = gateway
    with pytest.raises(ProductionConfigurationError, match="AI_VASTU_PAYMENT_GATEWAY"):
        load_production_settings(env)


def test_production_settings_accept_disabled_gateway_without_razorpay_credentials(
    tmp_path: Path,
) -> None:
    env = base_environment(tmp_path)
    env["AI_VASTU_PAYMENT_GATEWAY"] = "disabled"
    settings = load_production_settings(env)
    assert settings.payment_gateway == "disabled"
    assert settings.razorpay_key_secret is None
    assert settings.phonepe_client_secret is None


@pytest.mark.parametrize(
    "name",
    [
        "AI_VASTU_PHONEPE_ENVIRONMENT",
        "AI_VASTU_PHONEPE_CLIENT_ID",
        "AI_VASTU_PHONEPE_CLIENT_SECRET",
        "AI_VASTU_PHONEPE_CLIENT_VERSION",
        "AI_VASTU_PHONEPE_WEBHOOK_USERNAME",
        "AI_VASTU_PHONEPE_WEBHOOK_PASSWORD",
        "AI_VASTU_PHONEPE_REDIRECT_URL",
    ],
)
def test_production_settings_require_phonepe_fields_only_when_selected(
    tmp_path: Path, name: str
) -> None:
    env = base_environment(tmp_path)
    env.pop(name)

    with pytest.raises(ProductionConfigurationError, match=name):
        load_production_settings(env)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("AI_VASTU_PHONEPE_ENVIRONMENT", "sandbox"),
        ("AI_VASTU_PHONEPE_REDIRECT_URL", "http://app.example.com/billing/return"),
        ("AI_VASTU_PHONEPE_REDIRECT_URL", "https://other.example.com/billing/return"),
        ("AI_VASTU_PHONEPE_CONNECT_TIMEOUT_SECONDS", "0"),
        ("AI_VASTU_PHONEPE_CONNECT_TIMEOUT_SECONDS", "61"),
        ("AI_VASTU_PHONEPE_READ_TIMEOUT_SECONDS", "invalid"),
        ("AI_VASTU_PHONEPE_READ_TIMEOUT_SECONDS", "61"),
        ("AI_VASTU_PHONEPE_CLIENT_VERSION", "v1"),
        ("AI_VASTU_PHONEPE_CLIENT_VERSION", "0"),
        ("AI_VASTU_PHONEPE_CLIENT_SECRET", "x" * 513),
        ("AI_VASTU_PHONEPE_ORDER_EXPIRE_SECONDS", "299"),
        ("AI_VASTU_PHONEPE_ORDER_EXPIRE_SECONDS", "3601"),
    ],
)
def test_production_settings_reject_unsafe_phonepe_configuration(
    tmp_path: Path, name: str, value: str
) -> None:
    env = base_environment(tmp_path)
    env[name] = value

    with pytest.raises(ProductionConfigurationError, match=name):
        load_production_settings(env)


def test_production_settings_reject_test_razorpay_key(tmp_path: Path) -> None:
    env = base_environment(tmp_path)
    env.update(
        {
            "AI_VASTU_PAYMENT_GATEWAY": "razorpay",
            "AI_VASTU_RAZORPAY_KEY_ID": "rzp_test_example",
            "AI_VASTU_RAZORPAY_KEY_SECRET": "secret",
            "AI_VASTU_RAZORPAY_WEBHOOK_SECRET": "webhook-secret",
            "AI_VASTU_RAZORPAY_MONTHLY_PLAN_ID": "plan_month",
            "AI_VASTU_RAZORPAY_YEARLY_PLAN_ID": "plan_year",
        }
    )
    with pytest.raises(ProductionConfigurationError, match="test credentials"):
        load_production_settings(env)


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
def test_production_settings_require_razorpay_fields_only_when_selected(
    tmp_path: Path, name: str
) -> None:
    env = base_environment(tmp_path)
    env.update(
        {
            "AI_VASTU_PAYMENT_GATEWAY": "razorpay",
            "AI_VASTU_RAZORPAY_KEY_ID": "rzp_live_example",
            "AI_VASTU_RAZORPAY_KEY_SECRET": "secret",
            "AI_VASTU_RAZORPAY_WEBHOOK_SECRET": "webhook-secret",
            "AI_VASTU_RAZORPAY_MONTHLY_PLAN_ID": "plan_month",
            "AI_VASTU_RAZORPAY_YEARLY_PLAN_ID": "plan_year",
        }
    )
    assert load_production_settings(env).payment_gateway == "razorpay"
    env.pop(name)
    with pytest.raises(ProductionConfigurationError, match=name):
        load_production_settings(env)


def test_redacted_summary_excludes_secrets(tmp_path: Path) -> None:
    env = base_environment(tmp_path)
    env.update(
        {
            "AI_VASTU_PAYMENT_GATEWAY": "razorpay",
            "AI_VASTU_RAZORPAY_KEY_ID": "rzp_live_example",
            "AI_VASTU_RAZORPAY_KEY_SECRET": "razorpay-test-secret",
            "AI_VASTU_RAZORPAY_WEBHOOK_SECRET": "webhook-test-secret",
            "AI_VASTU_RAZORPAY_MONTHLY_PLAN_ID": "plan_month",
            "AI_VASTU_RAZORPAY_YEARLY_PLAN_ID": "plan_year",
        }
    )
    redacted = load_production_settings(env).redacted_summary()
    assert redacted["openrouter_attempt_timeout_seconds"] == 120.0
    assert redacted["openrouter_total_timeout_seconds"] == 240.0
    assert redacted["gemini_attempt_timeout_seconds"] == 90.0
    assert redacted["gemini_total_timeout_seconds"] == 181.0
    assert redacted["rate_limit_plan_analysis_per_hour"] == 10
    assert redacted["rate_limit_payment_status_per_hour"] == 30
    summary = str(redacted)
    for secret in (
        "user:pass", "openrouter-test-secret", "gemini-test-secret",
        "razorpay-test-secret", "webhook-test-secret", "rzp_live_example",
        "phonepe-client-secret", "phonepe-webhook-password",
    ):
        assert secret not in summary
