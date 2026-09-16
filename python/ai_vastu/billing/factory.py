from __future__ import annotations

import os
from pathlib import Path

from .postgres_repository import PostgresBillingRepository
from .repository import BillingRepository
from .sqlite_repository import SqliteBillingRepository


def create_billing_repository() -> BillingRepository:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env in {"production", "staging"}:
        database_url = os.getenv("AI_VASTU_DATABASE_URL", "")
        if not database_url:
            raise RuntimeError(
                "AI_VASTU_DATABASE_URL is required for production billing."
            )
        return PostgresBillingRepository(database_url)

    path = Path(
        os.getenv(
            "AI_VASTU_BILLING_SQLITE_PATH",
            ".local/billing.sqlite3",
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteBillingRepository(path)
