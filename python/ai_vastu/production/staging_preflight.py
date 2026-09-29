from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .settings import ProductionConfigurationError, load_production_settings

_REQUIRED_CONFIGURATION = (
    "APP_ENV",
    "AI_VASTU_AUTH_MODE",
    "AI_VASTU_DB_POOL_MIN_SIZE",
    "AI_VASTU_DB_POOL_MAX_SIZE",
    "AI_VASTU_DB_POOL_TIMEOUT_SECONDS",
    "AI_VASTU_SUPABASE_URL",
    "AI_VASTU_SUPABASE_JWT_AUDIENCE",
    "AI_VASTU_WEB_ORIGINS",
    "AI_VASTU_TRUSTED_HOSTS",
    "AI_VASTU_REQUIREMENTS_PATH",
    "AI_VASTU_GENERATION_UPLOAD_ROOT",
    "AI_VASTU_PAYMENT_GATEWAY",
    "AI_VASTU_DEV_BILLING_BYPASS",
    "AI_VASTU_REQUIREMENTS_PROVIDER",
    "AI_VASTU_ARCHITECT_PROVIDER",
    "AI_VASTU_VASTU_PROVIDER",
    "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER",
    "AI_VASTU_REVISION_PROVIDER",
    "AI_VASTU_PLAN_RECOGNITION_PROVIDER",
    "AI_VASTU_PLAN_RECOGNITION_MODEL",
    "AI_VASTU_GEMINI_MODEL",
    "AI_VASTU_OPENROUTER_PRIMARY_MODEL",
    "AI_VASTU_OPENROUTER_VISION_MODEL",
    "AI_VASTU_OPENROUTER_FALLBACK_MODEL",
    "AI_VASTU_OPENROUTER_ATTEMPT_TIMEOUT_SECONDS",
    "AI_VASTU_OPENROUTER_TOTAL_TIMEOUT_SECONDS",
    "AI_VASTU_OPENROUTER_RETRY_DELAY_SECONDS",
    "AI_VASTU_OPENROUTER_MAX_RETRY_AFTER_SECONDS",
    "AI_VASTU_GEMINI_ATTEMPT_TIMEOUT_SECONDS",
    "AI_VASTU_GEMINI_TOTAL_TIMEOUT_SECONDS",
    "AI_VASTU_GEMINI_RETRY_DELAY_SECONDS",
    "AI_VASTU_GEMINI_MAX_RETRY_AFTER_SECONDS",
    "AI_VASTU_RATE_LIMIT_INTERPRET_PER_HOUR",
    "AI_VASTU_RATE_LIMIT_GENERATION_PER_HOUR",
    "AI_VASTU_RATE_LIMIT_PLAN_ANALYSIS_PER_HOUR",
    "AI_VASTU_RATE_LIMIT_CHECKOUT_PER_HOUR",
    "AI_VASTU_RATE_LIMIT_PAYMENT_STATUS_PER_HOUR",
    "AI_VASTU_RATE_LIMIT_PAYMENT_WEBHOOK_PER_HOUR",
    "AI_VASTU_HSTS_SECONDS",
    "FORWARDED_ALLOW_IPS",
    "NEXT_PUBLIC_AI_VASTU_API_BASE_URL",
    "NEXT_PUBLIC_AI_VASTU_AUTH_MODE",
    "NEXT_PUBLIC_SUPABASE_URL",
)

_REQUIRED_CREDENTIALS = (
    "AI_VASTU_DATABASE_URL",
    "OPENROUTER_API_KEY",
    "GEMINI_API_KEY",
    "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
)

_PAYMENT_PROVIDER_PREFIXES = ("AI_VASTU_PHONEPE_", "AI_VASTU_RAZORPAY_")
_PLACEHOLDER_MARKERS = (
    "changeme",
    "placeholder",
    "replace-me",
    "replace_me",
    "dummy",
    "todo",
    "${",
    "<secret>",
    "<replace",
)
_TRUTHY = frozenset({"1", "true", "yes", "on"})
_ALLOWED_STATUSES = frozenset(
    {
        "PASS_LOCAL",
        "PASS_LIVE",
        "BLOCKED_CREDENTIALS",
        "BLOCKED_HUMAN_ACTION",
        "BLOCKED_EXTERNAL_SERVICE",
        "FAIL",
    }
)
_EVIDENCE_GATE_IDS = frozenset(
    {
        "postgres_tls_migrations_grants_rls",
        "supabase_jwt_jwks_ownership_cors_rate_limit",
        "openrouter_text_reasoning",
        "gemini_jpg_png_pdf_recognition",
        "backup_database_requirements_uploads",
        "disposable_restore",
        "non_payment_end_to_end",
        "phonepe_razorpay_live",
    }
)
_PROHIBITED_EVIDENCE_KEY_PARTS = (
    "secret",
    "token",
    "credential",
    "authorization_header",
    "database_url",
    "connection_string",
    "raw_payload",
)


def _present(environment: Mapping[str, str], name: str) -> bool:
    return bool(environment.get(name, "").strip())


def _contains_placeholder(environment: Mapping[str, str], name: str) -> bool:
    normalized = environment.get(name, "").strip().lower()
    return any(marker in normalized for marker in _PLACEHOLDER_MARKERS)


def _https_origin(value: str) -> bool:
    parsed = urlparse(value)
    return bool(
        parsed.scheme == "https"
        and parsed.hostname
        and not parsed.username
        and not parsed.password
        and not parsed.path.rstrip("/")
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    )


def _database_uses_verified_tls(value: str) -> bool:
    parsed = urlparse(value)
    sslmode = parse_qs(parsed.query).get("sslmode", [])
    return parsed.scheme in {"postgres", "postgresql"} and sslmode == ["verify-full"]


def _safe_storage_roots(environment: Mapping[str, str]) -> bool:
    paths: list[Path] = []
    for name in ("AI_VASTU_REQUIREMENTS_PATH", "AI_VASTU_GENERATION_UPLOAD_ROOT"):
        try:
            path = Path(environment[name]).resolve(strict=True)
        except (KeyError, OSError, RuntimeError):
            return False
        if not path.is_dir() or path == Path(path.anchor):
            return False
        paths.append(path)
    first, second = paths
    return first != second and first not in second.parents and second not in first.parents


def _evidence_keys(document: object) -> list[str]:
    if isinstance(document, dict):
        keys = [str(key) for key in document]
        for value in document.values():
            keys.extend(_evidence_keys(value))
        return keys
    if isinstance(document, list):
        keys = []
        for value in document:
            keys.extend(_evidence_keys(value))
        return keys
    return []


def validate_staging_evidence(document: object) -> None:
    """Validate evidence structure without asserting that live evidence is true."""

    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("Phase 29E evidence schema is invalid.")
    if any(
        prohibited in key.lower()
        for key in _evidence_keys(document)
        for prohibited in _PROHIBITED_EVIDENCE_KEY_PARTS
    ):
        raise ValueError("Phase 29E evidence contains a prohibited field name.")
    gates = document.get("gates")
    if not isinstance(gates, list) or len(gates) != len(_EVIDENCE_GATE_IDS):
        raise ValueError("Phase 29E evidence gates are incomplete.")
    gate_ids = {gate.get("id") for gate in gates if isinstance(gate, dict)}
    if gate_ids != _EVIDENCE_GATE_IDS:
        raise ValueError("Phase 29E evidence gate identifiers are invalid.")

    for gate in gates:
        if not isinstance(gate, dict):
            raise ValueError("Phase 29E evidence gate is invalid.")
        status = gate.get("status")
        if status not in _ALLOWED_STATUSES:
            raise ValueError("Phase 29E evidence gate status is invalid.")
        if gate["id"] == "phonepe_razorpay_live" and status != "BLOCKED_HUMAN_ACTION":
            raise ValueError("Payment live qualification must remain human-blocked.")
        if status == "PASS_LIVE":
            top_level_required = (
                "checkpoint_commit",
                "qualification_run_id",
                "started_at_utc",
                "completed_at_utc",
                "deployment_artifact",
                "target_alias",
            )
            if any(not str(document.get(name, "")).strip() for name in top_level_required):
                raise ValueError("PASS_LIVE requires complete qualification identity.")
            if not document.get("reviewers"):
                raise ValueError("PASS_LIVE requires a reviewer.")
            for name in (
                "check_ids",
                "commands",
                "exit_codes",
                "artifact_paths",
                "artifact_sha256",
            ):
                if not gate.get(name):
                    raise ValueError("PASS_LIVE requires complete gate evidence.")
            if not str(gate.get("evidence_collected_at_utc", "")).strip():
                raise ValueError("PASS_LIVE requires an evidence timestamp.")
            if not str(gate.get("operator", "")).strip():
                raise ValueError("PASS_LIVE requires an operator.")


def evaluate_staging_preflight(environment: Mapping[str, str]) -> dict[str, Any]:
    """Inspect staging configuration without performing I/O beyond local paths.

    The returned report intentionally contains variable names and fixed messages
    only. It never contains configured values and can never claim PASS_LIVE.
    """

    missing_configuration = [
        name for name in _REQUIRED_CONFIGURATION if not _present(environment, name)
    ]
    missing_credentials = [
        name for name in _REQUIRED_CREDENTIALS if not _present(environment, name)
    ]
    configured_payment_variables = sorted(
        name
        for name, value in environment.items()
        if value.strip() and name.startswith(_PAYMENT_PROVIDER_PREFIXES)
    )
    placeholder_credentials = [
        name
        for name in _REQUIRED_CREDENTIALS
        if _present(environment, name) and _contains_placeholder(environment, name)
    ]

    failures: list[str] = []
    if environment.get("AI_VASTU_PAYMENT_GATEWAY", "").strip().lower() not in {
        "",
        "disabled",
    }:
        failures.append("payment_gateway_not_disabled")
    if environment.get("AI_VASTU_DEV_BILLING_BYPASS", "").strip().lower() in _TRUTHY:
        failures.append("development_billing_bypass_enabled")
    if configured_payment_variables:
        failures.append("payment_provider_configuration_present")
    if placeholder_credentials:
        failures.append("credential_placeholder_present")

    if not missing_configuration and not missing_credentials and not failures:
        try:
            load_production_settings(dict(environment))
        except ProductionConfigurationError:
            failures.append("production_configuration_contract_invalid")

        if not _database_uses_verified_tls(environment["AI_VASTU_DATABASE_URL"]):
            failures.append("database_tls_verification_not_explicit")
        if not _safe_storage_roots(environment):
            failures.append("durable_storage_roots_unsafe")
        if environment["FORWARDED_ALLOW_IPS"].strip() == "*":
            failures.append("forwarded_proxy_trust_is_wildcard")
        if environment["NEXT_PUBLIC_AI_VASTU_AUTH_MODE"].strip().lower() != "supabase":
            failures.append("browser_auth_mode_not_supabase")
        if environment["NEXT_PUBLIC_SUPABASE_URL"].strip().rstrip("/") != environment[
            "AI_VASTU_SUPABASE_URL"
        ].strip().rstrip("/"):
            failures.append("browser_supabase_target_mismatch")
        if not _https_origin(environment["NEXT_PUBLIC_AI_VASTU_API_BASE_URL"].strip()):
            failures.append("browser_api_origin_not_https")

    if failures:
        status = "FAIL"
    elif missing_credentials:
        status = "BLOCKED_CREDENTIALS"
    elif missing_configuration:
        status = "BLOCKED_HUMAN_ACTION"
    else:
        status = "PASS_LOCAL"

    return {
        "schema_version": 1,
        "mode": "offline_no_egress",
        "scope": "configuration_structure_only",
        "preflight_status": status,
        "missing_configuration": missing_configuration,
        "missing_credentials": missing_credentials,
        "configured_payment_variables": configured_payment_variables,
        "failures": failures,
        "live_gates": {
            "database_supabase": "BLOCKED_CREDENTIALS",
            "openrouter": "BLOCKED_CREDENTIALS",
            "gemini": "BLOCKED_CREDENTIALS",
            "backup": "BLOCKED_CREDENTIALS",
            "restore_deployment": "BLOCKED_HUMAN_ACTION",
            "payments": "BLOCKED_HUMAN_ACTION",
            "target_isolation_and_test_identities": "BLOCKED_HUMAN_ACTION",
        },
        "pass_live": False,
        "network_calls_performed": False,
    }
