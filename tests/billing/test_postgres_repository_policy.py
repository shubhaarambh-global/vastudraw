from __future__ import annotations

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
