from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path

import httpx
import psycopg
import pytest

from ai_vastu.nvidia_nim_http import (
    NVIDIA_NIM_API_BASE,
    PRIMARY_REASONING_MODEL,
    VISION_PLAN_MODEL,
)
from ai_vastu.production.staging_preflight import (
    evaluate_staging_preflight,
    validate_staging_evidence,
)

ROOT = Path(__file__).resolve().parents[2]


def _environment(tmp_path: Path) -> dict[str, str]:
    requirements = tmp_path / "requirements"
    uploads = tmp_path / "uploads"
    requirements.mkdir()
    uploads.mkdir()
    return {
        "APP_ENV": "production",
        "AI_VASTU_AUTH_MODE": "supabase",
        "AI_VASTU_DATABASE_URL": (
            "postgresql://staging-user:sentinel-database-secret@db.staging.invalid/"
            "vastu?sslmode=verify-full"
        ),
        "AI_VASTU_DB_POOL_MIN_SIZE": "1",
        "AI_VASTU_DB_POOL_MAX_SIZE": "2",
        "AI_VASTU_DB_POOL_TIMEOUT_SECONDS": "10",
        "AI_VASTU_SUPABASE_URL": "https://phase29e-staging.supabase.invalid",
        "AI_VASTU_SUPABASE_JWT_AUDIENCE": "authenticated",
        "AI_VASTU_WEB_ORIGINS": "https://app.staging.invalid",
        "AI_VASTU_TRUSTED_HOSTS": "api.staging.invalid",
        "AI_VASTU_REQUIREMENTS_PATH": str(requirements.resolve()),
        "AI_VASTU_GENERATION_UPLOAD_ROOT": str(uploads.resolve()),
        "AI_VASTU_PAYMENT_GATEWAY": "disabled",
        "AI_VASTU_DEV_BILLING_BYPASS": "0",
        "AI_VASTU_REQUIREMENTS_PROVIDER": "nvidia_nim",
        "AI_VASTU_ARCHITECT_PROVIDER": "nvidia_nim",
        "AI_VASTU_VASTU_PROVIDER": "nvidia_nim",
        "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER": "nvidia_nim",
        "AI_VASTU_REVISION_PROVIDER": "nvidia_nim",
        "AI_VASTU_PLAN_RECOGNITION_PROVIDER": "nvidia_nim",
        "AI_VASTU_NVIDIA_BASE_URL": NVIDIA_NIM_API_BASE,
        "AI_VASTU_NVIDIA_PRIMARY_MODEL": PRIMARY_REASONING_MODEL,
        "AI_VASTU_NVIDIA_VISION_MODEL": VISION_PLAN_MODEL,
        "AI_VASTU_NVIDIA_ATTEMPT_TIMEOUT_SECONDS": "120",
        "AI_VASTU_NVIDIA_TOTAL_TIMEOUT_SECONDS": "240",
        "AI_VASTU_NVIDIA_RETRY_DELAY_SECONDS": "0",
        "AI_VASTU_NVIDIA_MAX_RETRY_AFTER_SECONDS": "0",
        "AI_VASTU_RATE_LIMIT_INTERPRET_PER_HOUR": "20",
        "AI_VASTU_RATE_LIMIT_GENERATION_PER_HOUR": "10",
        "AI_VASTU_RATE_LIMIT_PLAN_ANALYSIS_PER_HOUR": "10",
        "AI_VASTU_RATE_LIMIT_CHECKOUT_PER_HOUR": "20",
        "AI_VASTU_RATE_LIMIT_PAYMENT_STATUS_PER_HOUR": "30",
        "AI_VASTU_RATE_LIMIT_PAYMENT_WEBHOOK_PER_HOUR": "240",
        "AI_VASTU_HSTS_SECONDS": "31536000",
        "FORWARDED_ALLOW_IPS": "192.0.2.10",
        "NEXT_PUBLIC_AI_VASTU_API_BASE_URL": "https://api.staging.invalid",
        "NEXT_PUBLIC_AI_VASTU_AUTH_MODE": "supabase",
        "NEXT_PUBLIC_SUPABASE_URL": "https://phase29e-staging.supabase.invalid",
        "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY": "sentinel-publishable-key",
        "NVIDIA_API_KEY": "sentinel-nvidia-secret",
    }


def test_missing_credentials_are_blocked_without_egress() -> None:
    report = evaluate_staging_preflight({"APP_ENV": "development"})

    assert report["preflight_status"] == "BLOCKED_CREDENTIALS"
    assert report["network_calls_performed"] is False
    assert report["pass_live"] is False
    assert report["live_gates"]["payments"] == "BLOCKED_HUMAN_ACTION"


def test_complete_structural_configuration_is_pass_local_and_redacted(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)

    report = evaluate_staging_preflight(environment)
    serialized = json.dumps(report, sort_keys=True)

    assert report["preflight_status"] == "PASS_LOCAL"
    assert report["pass_live"] is False
    assert report["network_calls_performed"] is False
    for sentinel in (
        "sentinel-database-secret",
        "sentinel-publishable-key",
        "sentinel-nvidia-secret",
    ):
        assert sentinel not in serialized


def test_complete_preflight_attempts_no_network_or_database_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_call(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Offline preflight attempted external I/O.")

    monkeypatch.setattr(socket, "socket", unexpected_call)
    monkeypatch.setattr(socket, "getaddrinfo", unexpected_call)
    monkeypatch.setattr(httpx, "Client", unexpected_call)
    monkeypatch.setattr(psycopg, "connect", unexpected_call)

    report = evaluate_staging_preflight(_environment(tmp_path))

    assert report["preflight_status"] == "PASS_LOCAL"
    assert report["network_calls_performed"] is False


@pytest.mark.parametrize(
    ("name", "value", "failure"),
    [
        ("AI_VASTU_PAYMENT_GATEWAY", "phonepe", "payment_gateway_not_disabled"),
        ("AI_VASTU_DEV_BILLING_BYPASS", "true", "development_billing_bypass_enabled"),
        (
            "AI_VASTU_PHONEPE_CLIENT_SECRET",
            "sentinel-payment-secret",
            "payment_provider_configuration_present",
        ),
        (
            "AI_VASTU_DATABASE_URL",
            "postgresql://user:secret@db.staging.invalid/vastu?sslmode=require",
            "database_tls_verification_not_explicit",
        ),
        (
            "AI_VASTU_DATABASE_URL",
            "postgresql://user:secret@db.staging.invalid/vastu"
            "?sslmode=verify-full&sslmode=disable",
            "database_tls_verification_not_explicit",
        ),
        ("FORWARDED_ALLOW_IPS", "*", "forwarded_proxy_trust_is_wildcard"),
    ],
)
def test_preflight_fails_closed_without_echoing_values(
    tmp_path: Path,
    name: str,
    value: str,
    failure: str,
) -> None:
    environment = _environment(tmp_path)
    environment[name] = value

    report = evaluate_staging_preflight(environment)
    serialized = json.dumps(report, sort_keys=True)

    assert report["preflight_status"] == "FAIL"
    assert failure in report["failures"]
    assert value not in serialized


def test_preflight_rejects_overlapping_storage_roots(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    environment["AI_VASTU_GENERATION_UPLOAD_ROOT"] = str(
        (Path(environment["AI_VASTU_REQUIREMENTS_PATH"]) / "uploads").resolve()
    )
    Path(environment["AI_VASTU_GENERATION_UPLOAD_ROOT"]).mkdir()

    report = evaluate_staging_preflight(environment)

    assert report["preflight_status"] == "FAIL"
    assert "durable_storage_roots_unsafe" in report["failures"]


def test_evidence_template_defaults_live_gates_to_blocked() -> None:
    template_path = (
        ROOT / "docs" / "exec-plans" / "templates" / "phase29e-staging-evidence.json"
    )
    template = json.loads(template_path.read_text(encoding="utf-8"))
    statuses = {gate["status"] for gate in template["gates"]}

    assert statuses <= {"BLOCKED_CREDENTIALS", "BLOCKED_HUMAN_ACTION"}
    assert "PASS_LIVE" not in statuses
    assert {gate["id"] for gate in template["gates"]} == {
        "postgres_tls_migrations_grants_rls",
        "supabase_jwt_jwks_ownership_cors_rate_limit",
        "nvidia_text",
        "nvidia_vision",
        "nvidia_nim_production_entitlement",
        "backup_database_requirements_uploads",
        "disposable_restore",
        "non_payment_end_to_end",
        "phonepe_razorpay_live",
    }
    assert "secret" not in template_path.read_text(encoding="utf-8").lower()
    validate_staging_evidence(template)


def test_evidence_validator_rejects_unsupported_live_claim() -> None:
    template_path = (
        ROOT / "docs" / "exec-plans" / "templates" / "phase29e-staging-evidence.json"
    )
    template = json.loads(template_path.read_text(encoding="utf-8"))
    template["gates"][0]["status"] = "PASS_LIVE"

    with pytest.raises(ValueError, match="PASS_LIVE"):
        validate_staging_evidence(template)


def test_evidence_validator_keeps_human_action_gates_blocked() -> None:
    template_path = (
        ROOT / "docs" / "exec-plans" / "templates" / "phase29e-staging-evidence.json"
    )
    template = json.loads(template_path.read_text(encoding="utf-8"))
    gate = next(
        item
        for item in template["gates"]
        if item["id"] == "nvidia_nim_production_entitlement"
    )
    gate["status"] = "PASS_LOCAL"

    with pytest.raises(ValueError, match="must remain human-blocked"):
        validate_staging_evidence(template)


def test_evidence_validator_cli_is_redacted(tmp_path: Path) -> None:
    script = ROOT / "scripts" / "validate-phase29e-staging-evidence.py"
    valid = ROOT / "docs" / "exec-plans" / "templates" / "phase29e-staging-evidence.json"
    accepted = subprocess.run(
        [sys.executable, str(script), str(valid)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert accepted.returncode == 0
    assert '"status":"PASS_LOCAL"' in accepted.stdout
    assert '"pass_live":false' in accepted.stdout
    assert accepted.stderr == ""

    invalid = tmp_path / "invalid-evidence.json"
    invalid.write_text('{"sentinel-secret":"must-not-leak"}', encoding="utf-8")
    rejected = subprocess.run(
        [sys.executable, str(script), str(invalid)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert rejected.returncode == 1
    assert "must-not-leak" not in rejected.stdout
    assert "must-not-leak" not in rejected.stderr
    assert rejected.stderr == ""
