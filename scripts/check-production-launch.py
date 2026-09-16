from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import psycopg

from ai_vastu.production.settings import (
    EXPECTED_VASTU_BUNDLE_HASH,
    ProductionConfigurationError,
    load_production_settings,
)
from ai_vastu.vastu.models import RuleBundle

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"PRODUCTION LAUNCH BLOCKED: {message}")


try:
    settings = load_production_settings()
except ProductionConfigurationError as exc:
    fail(str(exc))

bundle_path = Path(
    os.getenv(
        "AI_VASTU_VASTU_RULE_BUNDLE_PATH",
        str(
            ROOT
            / "docs"
            / "vastu"
            / "spec-v1.0"
            / "production"
            / "rule-bundle.json"
        ),
    )
)
if not bundle_path.is_file():
    fail(f"Vastu production bundle missing: {bundle_path}")

bundle = RuleBundle.model_validate_json(bundle_path.read_text(encoding="utf-8"))
if not bundle.production or bundle.content_hash != EXPECTED_VASTU_BUNDLE_HASH:
    fail("Frozen Vastu production bundle verification failed.")

settings.requirements_path.mkdir(parents=True, exist_ok=True)
probe = settings.requirements_path / ".phase25-write-probe"
try:
    probe.write_text("phase25", encoding="utf-8")
    probe.unlink()
except OSError as exc:
    fail(f"Requirements storage is not writable: {exc}")

try:
    with (
        psycopg.connect(
            settings.database_url,
            connect_timeout=10,
        ) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT current_database(), current_user")
        database_row = cursor.fetchone()
        cursor.execute(
            """
            SELECT to_regclass('public.ai_vastu_rate_limit_windows') IS NOT NULL
            """
        )
        limiter_row = cursor.fetchone()
except Exception as exc:
    fail(f"PostgreSQL connectivity failed: {exc}")

if limiter_row is None or limiter_row[0] is not True:
    fail("Phase 25 rate-limit migration has not been applied.")

supabase_host = urlparse(settings.supabase_url).hostname
if not supabase_host:
    fail("Supabase URL has no hostname.")
try:
    socket.getaddrinfo(supabase_host, 443)
except OSError as exc:
    fail(f"Supabase hostname cannot be resolved: {exc}")

summary = settings.redacted_summary()
summary["vastu_bundle_hash"] = bundle.content_hash
summary["vastu_rules"] = len(bundle.rules)
summary["database_identity"] = list(database_row) if database_row else None
summary["rate_limit_table"] = True

print(json.dumps(summary, indent=2, sort_keys=True))
print("PRODUCTION LAUNCH GATE: PASS")
