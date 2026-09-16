from pathlib import Path

from ai_vastu.production.settings import load_production_settings


def _base_environment(tmp_path: Path) -> dict[str, str]:
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
        "AI_VASTU_REQUIREMENTS_PROVIDER": "gemini",
        "GEMINI_API_KEY": "test-gemini-key",
        "AI_VASTU_GEMINI_MODEL": "gemini-2.5-flash",
    }


def test_production_settings_accept_gemini_provider(tmp_path: Path) -> None:
    settings = load_production_settings(_base_environment(tmp_path))

    assert settings.requirements_provider == "gemini"
    assert settings.gemini_model == "gemini-2.5-flash"
    assert settings.openai_model is None
