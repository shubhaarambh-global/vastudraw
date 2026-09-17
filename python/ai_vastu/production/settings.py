from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

EXPECTED_VASTU_BUNDLE_HASH = "b11b66be61d6436fcaa43c1c5b743c0090051154146d91caf904eb5108546667"


class ProductionConfigurationError(RuntimeError):
    pass


def _required(environment: dict[str, str], name: str) -> str:
    value = environment.get(name, "").strip()
    if not value:
        raise ProductionConfigurationError(f"Missing required environment variable: {name}")
    return value


def _positive_int(
    environment: dict[str, str],
    name: str,
    *,
    default: int,
) -> int:
    raw = environment.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ProductionConfigurationError(f"{name} must be an integer.") from exc
    if value <= 0:
        raise ProductionConfigurationError(f"{name} must be greater than zero.")
    return value


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _https_url(value: str, name: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ProductionConfigurationError(f"{name} must be an absolute HTTPS URL.")
    return value.rstrip("/")


@dataclass(frozen=True, slots=True)
class ProductionSettings:
    database_url: str
    supabase_url: str
    supabase_jwt_audience: str
    allowed_origins: tuple[str, ...]
    trusted_hosts: tuple[str, ...]
    requirements_path: Path
    razorpay_key_id: str
    razorpay_key_secret: str
    razorpay_webhook_secret: str
    razorpay_monthly_plan_id: str
    razorpay_yearly_plan_id: str
    requirements_provider: str
    openai_model: str | None
    gemini_model: str | None
    rate_limit_interpret_per_hour: int
    rate_limit_generation_per_hour: int
    rate_limit_checkout_per_hour: int
    hsts_seconds: int

    def redacted_summary(self) -> dict[str, object]:
        return {
            "database": "postgresql",
            "supabase_url": self.supabase_url,
            "supabase_jwt_audience": self.supabase_jwt_audience,
            "allowed_origins": self.allowed_origins,
            "trusted_hosts": self.trusted_hosts,
            "requirements_path": str(self.requirements_path),
            "razorpay_key_id_prefix": self.razorpay_key_id[:8],
            "requirements_provider": self.requirements_provider,
            "openai_model": self.openai_model,
            "gemini_model": self.gemini_model,
            "rate_limit_interpret_per_hour": self.rate_limit_interpret_per_hour,
            "rate_limit_generation_per_hour": self.rate_limit_generation_per_hour,
            "rate_limit_checkout_per_hour": self.rate_limit_checkout_per_hour,
            "hsts_seconds": self.hsts_seconds,
        }


def load_production_settings(
    environment: dict[str, str] | None = None,
) -> ProductionSettings:
    env = dict(os.environ if environment is None else environment)

    app_env = env.get("APP_ENV", "").strip().lower()
    if app_env != "production":
        raise ProductionConfigurationError("APP_ENV must be production.")

    auth_mode = env.get("AI_VASTU_AUTH_MODE", "").strip().lower()
    if auth_mode != "production":
        raise ProductionConfigurationError("AI_VASTU_AUTH_MODE must be production.")

    database_url = _required(env, "DATABASE_URL")
    parsed_database = urlparse(database_url)
    if parsed_database.scheme not in {"postgres", "postgresql"}:
        raise ProductionConfigurationError("DATABASE_URL must use PostgreSQL in production.")

    supabase_url = _https_url(
        _required(env, "AI_VASTU_SUPABASE_URL"),
        "AI_VASTU_SUPABASE_URL",
    )
    audience = _required(env, "AI_VASTU_SUPABASE_JWT_AUDIENCE")

    origins = _csv(_required(env, "AI_VASTU_ALLOWED_ORIGINS"))
    if not origins or "*" in origins:
        raise ProductionConfigurationError(
            "AI_VASTU_ALLOWED_ORIGINS must contain explicit HTTPS origins."
        )
    for origin in origins:
        _https_url(origin, "AI_VASTU_ALLOWED_ORIGINS")

    trusted_hosts = _csv(_required(env, "AI_VASTU_TRUSTED_HOSTS"))
    if not trusted_hosts or "*" in trusted_hosts:
        raise ProductionConfigurationError(
            "AI_VASTU_TRUSTED_HOSTS must contain explicit hostnames."
        )
    if any("://" in host or "/" in host for host in trusted_hosts):
        raise ProductionConfigurationError("AI_VASTU_TRUSTED_HOSTS entries must be hostnames only.")

    requirements_path = Path(_required(env, "AI_VASTU_REQUIREMENTS_PATH")).expanduser()
    if not requirements_path.is_absolute():
        raise ProductionConfigurationError(
            "AI_VASTU_REQUIREMENTS_PATH must be absolute in production."
        )

    key_id = _required(env, "AI_VASTU_RAZORPAY_KEY_ID")
    if key_id.startswith("rzp_test_"):
        raise ProductionConfigurationError(
            "Razorpay test credentials cannot pass the production launch gate."
        )

    provider = (
        env.get(
            "AI_VASTU_REQUIREMENTS_PROVIDER",
            "fixture",
        )
        .strip()
        .lower()
    )
    if provider not in {"openai", "gemini"}:
        raise ProductionConfigurationError(
            "Commercial launch requires a supported live requirements provider."
        )

    openai_model: str | None = None
    gemini_model: str | None = None
    if provider == "openai":
        _required(env, "OPENAI_API_KEY")
        openai_model = _required(env, "AI_VASTU_OPENAI_MODEL")
    else:
        _required(env, "GEMINI_API_KEY")
        gemini_model = _required(env, "AI_VASTU_GEMINI_MODEL")

    return ProductionSettings(
        database_url=database_url,
        supabase_url=supabase_url,
        supabase_jwt_audience=audience,
        allowed_origins=origins,
        trusted_hosts=trusted_hosts,
        requirements_path=requirements_path,
        razorpay_key_id=key_id,
        razorpay_key_secret=_required(env, "AI_VASTU_RAZORPAY_KEY_SECRET"),
        razorpay_webhook_secret=_required(
            env,
            "AI_VASTU_RAZORPAY_WEBHOOK_SECRET",
        ),
        razorpay_monthly_plan_id=_required(
            env,
            "AI_VASTU_RAZORPAY_MONTHLY_PLAN_ID",
        ),
        razorpay_yearly_plan_id=_required(
            env,
            "AI_VASTU_RAZORPAY_YEARLY_PLAN_ID",
        ),
        requirements_provider=provider,
        openai_model=openai_model,
        gemini_model=gemini_model,
        rate_limit_interpret_per_hour=_positive_int(
            env,
            "AI_VASTU_RATE_LIMIT_INTERPRET_PER_HOUR",
            default=20,
        ),
        rate_limit_generation_per_hour=_positive_int(
            env,
            "AI_VASTU_RATE_LIMIT_GENERATION_PER_HOUR",
            default=10,
        ),
        rate_limit_checkout_per_hour=_positive_int(
            env,
            "AI_VASTU_RATE_LIMIT_CHECKOUT_PER_HOUR",
            default=20,
        ),
        hsts_seconds=_positive_int(
            env,
            "AI_VASTU_HSTS_SECONDS",
            default=31_536_000,
        ),
    )
