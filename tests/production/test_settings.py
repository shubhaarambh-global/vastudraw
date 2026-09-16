from pathlib import Path

import pytest

from ai_vastu.production.settings import (
    ProductionConfigurationError,
    load_production_settings,
)


def base_environment(tmp_path: Path) -> dict[str, str]:
    return {
        "APP_ENV": "production",
        "AI_VASTU_AUTH_MODE": "production",
        "DATABASE_URL": "postgresql://user:pass@db.example.com:5432/vastu",
        "AI_VASTU_SUPABASE_URL": "https://example.supabase.co",
        "AI_VASTU_SUPABASE_JWT_AUDIENCE": "authenticated",
        "AI_VASTU_ALLOWED_ORIGINS": "https://app.example.com",
        "AI_VASTU_TRUSTED_HOSTS": "api.example.com",
        "AI_VASTU_REQUIREMENTS_PATH": str(tmp_path.resolve()),
        "AI_VASTU_RAZORPAY_KEY_ID": "rzp_live_example",
        "AI_VASTU_RAZORPAY_KEY_SECRET": "secret",
        "AI_VASTU_RAZORPAY_WEBHOOK_SECRET": "webhook-secret",
        "AI_VASTU_RAZORPAY_MONTHLY_PLAN_ID": "plan_month",
        "AI_VASTU_RAZORPAY_YEARLY_PLAN_ID": "plan_year",
        "AI_VASTU_REQUIREMENTS_PROVIDER": "openai",
        "OPENAI_API_KEY": "test-key",
        "AI_VASTU_OPENAI_MODEL": "configured-at-deploy",
    }


def test_production_settings_accept_explicit_secure_configuration(
    tmp_path: Path,
) -> None:
    settings = load_production_settings(base_environment(tmp_path))
    assert settings.allowed_origins == ("https://app.example.com",)
    assert settings.trusted_hosts == ("api.example.com",)
    assert settings.rate_limit_generation_per_hour == 10


def test_production_settings_reject_development_auth(tmp_path: Path) -> None:
    environment = base_environment(tmp_path)
    environment["AI_VASTU_AUTH_MODE"] = "development"
    with pytest.raises(ProductionConfigurationError):
        load_production_settings(environment)


def test_production_settings_reject_wildcard_origin(tmp_path: Path) -> None:
    environment = base_environment(tmp_path)
    environment["AI_VASTU_ALLOWED_ORIGINS"] = "*"
    with pytest.raises(ProductionConfigurationError):
        load_production_settings(environment)


def test_production_settings_reject_test_razorpay_key(tmp_path: Path) -> None:
    environment = base_environment(tmp_path)
    environment["AI_VASTU_RAZORPAY_KEY_ID"] = "rzp_test_example"
    with pytest.raises(ProductionConfigurationError):
        load_production_settings(environment)
