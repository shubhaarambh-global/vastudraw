from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from ai_vastu.openrouter_http import (
    OpenRouterConfigurationError,
    OpenRouterModelPolicy,
)

EXPECTED_VASTU_BUNDLE_HASH = "b11b66be61d6436fcaa43c1c5b743c0090051154146d91caf904eb5108546667"
QUALIFIED_GEMINI_PLAN_MODEL = "gemini-3.1-flash-lite"
_OPENROUTER_PROVIDER_SWITCHES = (
    "AI_VASTU_REQUIREMENTS_PROVIDER",
    "AI_VASTU_ARCHITECT_PROVIDER",
    "AI_VASTU_VASTU_PROVIDER",
    "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER",
    "AI_VASTU_REVISION_PROVIDER",
)


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
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or "*" in parsed.netloc
        or "%" in parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ProductionConfigurationError(f"{name} must be an absolute HTTPS URL.")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ProductionConfigurationError(f"{name} has an invalid port.") from exc
    return value.rstrip("/")


def _absolute_path(environment: dict[str, str], name: str) -> Path:
    path = Path(_required(environment, name))
    if not path.is_absolute():
        raise ProductionConfigurationError(f"{name} must be absolute in production.")
    return path


def _qualified_provider(environment: dict[str, str], name: str, expected: str) -> str:
    value = _required(environment, name).lower()
    if value != expected:
        raise ProductionConfigurationError(f"{name} must be {expected} in production.")
    return value


@dataclass(frozen=True, slots=True)
class ProductionSettings:
    database_url: str
    supabase_url: str
    supabase_jwt_audience: str
    allowed_origins: tuple[str, ...]
    trusted_hosts: tuple[str, ...]
    requirements_path: Path
    generation_upload_root: Path
    payment_gateway: str
    razorpay_key_id: str | None
    razorpay_key_secret: str | None
    razorpay_webhook_secret: str | None
    razorpay_monthly_plan_id: str | None
    razorpay_yearly_plan_id: str | None
    requirements_provider: str
    architect_provider: str
    vastu_provider: str
    architectural_brain_provider: str
    revision_provider: str
    plan_recognition_provider: str
    plan_recognition_model: str
    openai_model: str | None
    gemini_model: str | None
    openrouter_primary_model: str | None
    openrouter_vision_model: str | None
    openrouter_fallback_model: str | None
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
            "requirements_path": "configured_absolute",
            "generation_upload_root": "configured_absolute",
            "payment_gateway": self.payment_gateway,
            "requirements_provider": self.requirements_provider,
            "architect_provider": self.architect_provider,
            "vastu_provider": self.vastu_provider,
            "architectural_brain_provider": self.architectural_brain_provider,
            "revision_provider": self.revision_provider,
            "plan_recognition_provider": self.plan_recognition_provider,
            "plan_recognition_model": self.plan_recognition_model,
            "openai_model": self.openai_model,
            "gemini_model": self.gemini_model,
            "openrouter_primary_model": self.openrouter_primary_model,
            "openrouter_vision_model": self.openrouter_vision_model,
            "openrouter_fallback_model": self.openrouter_fallback_model,
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
    if auth_mode != "supabase":
        raise ProductionConfigurationError("AI_VASTU_AUTH_MODE must be supabase in production.")

    if env.get("AI_VASTU_DEV_BILLING_BYPASS", "").strip().lower() in {
        "1", "true", "yes", "on",
    }:
        raise ProductionConfigurationError(
            "AI_VASTU_DEV_BILLING_BYPASS cannot be enabled in production."
        )

    database_url = _required(env, "AI_VASTU_DATABASE_URL")
    parsed_database = urlparse(database_url)
    if parsed_database.scheme not in {"postgres", "postgresql"} or not parsed_database.hostname:
        raise ProductionConfigurationError(
            "AI_VASTU_DATABASE_URL must be an absolute PostgreSQL URL in production."
        )
    try:
        _ = parsed_database.port
    except ValueError as exc:
        raise ProductionConfigurationError(
            "AI_VASTU_DATABASE_URL has an invalid port."
        ) from exc

    supabase_url = _https_url(
        _required(env, "AI_VASTU_SUPABASE_URL"),
        "AI_VASTU_SUPABASE_URL",
    )
    parsed_supabase = urlparse(supabase_url)
    if (
        parsed_supabase.path
        or parsed_supabase.query
        or parsed_supabase.fragment
    ):
        raise ProductionConfigurationError(
            "AI_VASTU_SUPABASE_URL must be a project HTTPS origin."
        )
    audience = _required(env, "AI_VASTU_SUPABASE_JWT_AUDIENCE")
    if audience != "authenticated":
        raise ProductionConfigurationError(
            "AI_VASTU_SUPABASE_JWT_AUDIENCE must be authenticated."
        )

    origins = _csv(_required(env, "AI_VASTU_WEB_ORIGINS"))
    if not origins or "*" in origins:
        raise ProductionConfigurationError(
            "AI_VASTU_WEB_ORIGINS must contain explicit HTTPS origins."
        )
    for origin in origins:
        _https_url(origin, "AI_VASTU_WEB_ORIGINS")
        parsed_origin = urlparse(origin)
        if any(
            (parsed_origin.path, parsed_origin.params, parsed_origin.query, parsed_origin.fragment)
        ):
            raise ProductionConfigurationError(
                "AI_VASTU_WEB_ORIGINS entries must be origins without paths or queries."
            )

    trusted_hosts = _csv(_required(env, "AI_VASTU_TRUSTED_HOSTS"))
    if not trusted_hosts or "*" in trusted_hosts:
        raise ProductionConfigurationError(
            "AI_VASTU_TRUSTED_HOSTS must contain explicit hostnames."
        )
    if any(
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", host) is None
        for host in trusted_hosts
    ):
        raise ProductionConfigurationError("AI_VASTU_TRUSTED_HOSTS entries must be hostnames only.")

    requirements_path = _absolute_path(env, "AI_VASTU_REQUIREMENTS_PATH")
    generation_upload_root = _absolute_path(env, "AI_VASTU_GENERATION_UPLOAD_ROOT")

    payment_gateway = _required(env, "AI_VASTU_PAYMENT_GATEWAY").lower()
    if payment_gateway not in {"phonepe", "razorpay", "disabled"}:
        raise ProductionConfigurationError(
            "AI_VASTU_PAYMENT_GATEWAY must be phonepe, razorpay, or disabled."
        )
    key_id: str | None = None
    key_secret: str | None = None
    webhook_secret: str | None = None
    monthly_plan_id: str | None = None
    yearly_plan_id: str | None = None
    if payment_gateway == "razorpay":
        key_id = _required(env, "AI_VASTU_RAZORPAY_KEY_ID")
        if key_id.startswith("rzp_test_"):
            raise ProductionConfigurationError(
                "Razorpay test credentials cannot pass the production launch gate."
            )
        key_secret = _required(env, "AI_VASTU_RAZORPAY_KEY_SECRET")
        webhook_secret = _required(env, "AI_VASTU_RAZORPAY_WEBHOOK_SECRET")
        monthly_plan_id = _required(env, "AI_VASTU_RAZORPAY_MONTHLY_PLAN_ID")
        yearly_plan_id = _required(env, "AI_VASTU_RAZORPAY_YEARLY_PLAN_ID")

    for name in _OPENROUTER_PROVIDER_SWITCHES:
        _qualified_provider(env, name, "openrouter")
    _qualified_provider(env, "AI_VASTU_PLAN_RECOGNITION_PROVIDER", "gemini")
    plan_recognition_model = _required(env, "AI_VASTU_PLAN_RECOGNITION_MODEL")
    if plan_recognition_model != QUALIFIED_GEMINI_PLAN_MODEL:
        raise ProductionConfigurationError(
            f"AI_VASTU_PLAN_RECOGNITION_MODEL must be {QUALIFIED_GEMINI_PLAN_MODEL}."
        )
    gemini_model = _required(env, "AI_VASTU_GEMINI_MODEL")
    if gemini_model != QUALIFIED_GEMINI_PLAN_MODEL:
        raise ProductionConfigurationError(
            f"AI_VASTU_GEMINI_MODEL must be {QUALIFIED_GEMINI_PLAN_MODEL}."
        )
    _required(env, "OPENROUTER_API_KEY")
    _required(env, "GEMINI_API_KEY")

    openai_model: str | None = None
    openrouter_primary_model: str | None = None
    openrouter_vision_model: str | None = None
    openrouter_fallback_model: str | None = None

    policy = OpenRouterModelPolicy(
        primary=_required(env, "AI_VASTU_OPENROUTER_PRIMARY_MODEL"),
        vision=_required(env, "AI_VASTU_OPENROUTER_VISION_MODEL"),
        fallback=_required(env, "AI_VASTU_OPENROUTER_FALLBACK_MODEL"),
    )
    try:
        policy.validate()
    except OpenRouterConfigurationError as exc:
        raise ProductionConfigurationError("OpenRouter model policy is invalid.") from exc
    openrouter_primary_model = policy.primary
    openrouter_vision_model = policy.vision
    openrouter_fallback_model = policy.fallback

    return ProductionSettings(
        database_url=database_url,
        supabase_url=supabase_url,
        supabase_jwt_audience=audience,
        allowed_origins=origins,
        trusted_hosts=trusted_hosts,
        requirements_path=requirements_path,
        generation_upload_root=generation_upload_root,
        payment_gateway=payment_gateway,
        razorpay_key_id=key_id,
        razorpay_key_secret=key_secret,
        razorpay_webhook_secret=webhook_secret,
        razorpay_monthly_plan_id=monthly_plan_id,
        razorpay_yearly_plan_id=yearly_plan_id,
        requirements_provider="openrouter",
        architect_provider="openrouter",
        vastu_provider="openrouter",
        architectural_brain_provider="openrouter",
        revision_provider="openrouter",
        plan_recognition_provider="gemini",
        plan_recognition_model=plan_recognition_model,
        openai_model=openai_model,
        gemini_model=gemini_model,
        openrouter_primary_model=openrouter_primary_model,
        openrouter_vision_model=openrouter_vision_model,
        openrouter_fallback_model=openrouter_fallback_model,
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
