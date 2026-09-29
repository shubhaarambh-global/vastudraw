from __future__ import annotations

import json
import os
import socket
from contextlib import suppress
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

import psycopg

from ai_vastu.billing.phonepe import PhonePeConfigurationError
from ai_vastu.billing.phonepe_factory import create_phonepe_client
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

if settings.payment_gateway == "disabled":
    fail("Payments are disabled; a production launch cannot be qualified.")
if settings.payment_gateway == "phonepe":
    try:
        with create_phonepe_client():
            pass
    except (PhonePeConfigurationError, ValueError) as exc:
        fail(f"PhonePe runtime configuration is invalid: {exc}")

bundle_path = Path(
    os.getenv(
        "AI_VASTU_VASTU_RULE_BUNDLE_PATH",
        str(ROOT / "docs" / "vastu" / "spec-v1.0" / "production" / "rule-bundle.json"),
    )
)
if not bundle_path.is_file():
    fail(f"Vastu production bundle missing: {bundle_path}")

bundle = RuleBundle.model_validate_json(bundle_path.read_text(encoding="utf-8"))
if not bundle.production or bundle.content_hash != EXPECTED_VASTU_BUNDLE_HASH:
    fail("Frozen Vastu production bundle verification failed.")

for storage_name, storage_root in (
    ("Requirements", settings.requirements_path),
    ("Generation upload", settings.generation_upload_root),
):
    probe_path: Path | None = None
    try:
        storage_root.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".phase29a-write-probe-",
            dir=storage_root,
            delete=False,
        ) as probe:
            probe_path = Path(probe.name)
            probe.write("phase29a")
        probe_path.unlink()
    except OSError as exc:
        if probe_path is not None:
            with suppress(OSError):
                probe_path.unlink(missing_ok=True)
        fail(f"{storage_name} storage is not writable: {exc}")

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
        cursor.execute(
            """
            SELECT to_regclass('public.billing_payment_orders') IS NOT NULL
            """
        )
        payment_orders_row = cursor.fetchone()
except Exception as exc:
    fail(f"PostgreSQL connectivity failed: {exc}")

if limiter_row is None or limiter_row[0] is not True:
    fail("Phase 25 rate-limit migration has not been applied.")
if payment_orders_row is None or payment_orders_row[0] is not True:
    fail("Phase 29D payment atomicity migration has not been applied.")

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
summary["payment_orders_table"] = True

print(json.dumps(summary, indent=2, sort_keys=True))
print("PRODUCTION LAUNCH GATE: PASS")
