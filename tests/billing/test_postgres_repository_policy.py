from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ai_vastu.billing import postgres_repository


def test_billing_pool_disables_prepared_statements_for_transaction_pooler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_pool(conninfo: str, **options: Any) -> object:
        captured["conninfo"] = conninfo
        captured.update(options)
        return object()

    monkeypatch.setattr(postgres_repository, "ConnectionPool", fake_pool)
    postgres_repository.PostgresBillingRepository("postgresql://example.invalid/billing")

    assert captured["conninfo"] == "postgresql://example.invalid/billing"
    assert captured["kwargs"] == {
        "autocommit": False,
        "prepare_threshold": None,
        "row_factory": postgres_repository.dict_row,
    }


def test_phase29d_billing_tables_are_server_only_under_rls() -> None:
    migration = Path(
        "infra/postgres/migrations/202609270001_phase29d_payment_atomicity.sql"
    ).read_text(encoding="utf-8")
    lowered = migration.lower()

    for table in (
        "billing_accounts",
        "billing_project_grants",
        "billing_events",
        "billing_payment_orders",
    ):
        assert f"alter table public.{table} enable row level security" in lowered
        assert f"revoke all on table public.{table} from public" in lowered
        assert f"revoke all on table public.{table} from anon" in lowered
        assert f"revoke all on table public.{table} from authenticated" in lowered

    assert "create policy" not in lowered
