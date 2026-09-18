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


def _environment(tmp_path: Path) -> dict[str, str]:
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
        "AI_VASTU_REQUIREMENTS_PROVIDER": "openrouter",
        "OPENROUTER_API_KEY": "test-openrouter-key",
        "AI_VASTU_OPENROUTER_PRIMARY_MODEL": PRIMARY_ARCHITECTURAL_MODEL,
        "AI_VASTU_OPENROUTER_VISION_MODEL": VISION_PLAN_MODEL,
        "AI_VASTU_OPENROUTER_FALLBACK_MODEL": FALLBACK_REASONING_MODEL,
    }


def test_production_settings_accept_pinned_openrouter_free_stack(
    tmp_path: Path,
) -> None:
    settings = load_production_settings(_environment(tmp_path))

    assert settings.requirements_provider == "openrouter"
    assert settings.openrouter_primary_model == PRIMARY_ARCHITECTURAL_MODEL
    assert settings.openrouter_vision_model == VISION_PLAN_MODEL
    assert settings.openrouter_fallback_model == FALLBACK_REASONING_MODEL
    assert settings.openai_model is None
    assert settings.gemini_model is None


def test_production_settings_reject_paid_model_substitution(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    env["AI_VASTU_OPENROUTER_PRIMARY_MODEL"] = "deepseek/deepseek-v4-flash-0731"

    with pytest.raises(ProductionConfigurationError):
        load_production_settings(env)
