from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from .models import EntitlementSnapshot, ProjectGrant, SubscriptionStatus

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS billing_accounts (
    user_id TEXT PRIMARY KEY,
    free_generation_available INTEGER NOT NULL DEFAULT 1 CHECK (free_generation_available IN (0,1)),
    project_credits INTEGER NOT NULL DEFAULT 0 CHECK (project_credits >= 0),
    active_subscription_sku TEXT,
    subscription_status TEXT NOT NULL DEFAULT 'none',
    subscription_period_end TEXT,
    provider_subscription_id TEXT
);

CREATE TABLE IF NOT EXISTS billing_project_grants (
    user_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, project_id)
);

CREATE TABLE IF NOT EXISTS billing_events (
    provider TEXT NOT NULL,
    event_key TEXT NOT NULL,
    event_type TEXT NOT NULL,
    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provider, event_key)
);
"""


class SqliteBillingRepository:
    def __init__(self, path: Path | str) -> None:
        self._connection = sqlite3.connect(str(path))
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(_SCHEMA)
        self._connection.commit()

    def ensure_user(self, user_id: str) -> None:
        self._connection.execute(
            "INSERT OR IGNORE INTO billing_accounts(user_id) VALUES (?)", (user_id,)
        )
        self._connection.commit()

    def get_snapshot(self, user_id: str) -> EntitlementSnapshot:
        self.ensure_user(user_id)
        row = self._connection.execute(
            """
            SELECT user_id, free_generation_available, project_credits,
                   active_subscription_sku, subscription_status,
                   subscription_period_end
            FROM billing_accounts WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        assert row is not None
        period_end = (
            datetime.fromisoformat(row["subscription_period_end"])
            if row["subscription_period_end"]
            else None
        )
        return EntitlementSnapshot(
            user_id=row["user_id"],
            free_generation_available=bool(row["free_generation_available"]),
            project_credits=int(row["project_credits"]),
            active_subscription_sku=row["active_subscription_sku"],
            subscription_status=SubscriptionStatus(row["subscription_status"]),
            subscription_period_end=period_end,
        )

    def grant_project_credits(self, user_id: str, count: int) -> None:
        if count <= 0:
            raise ValueError("Project credit grant must be positive.")
        self.ensure_user(user_id)
        self._connection.execute(
            """
            UPDATE billing_accounts
            SET project_credits = project_credits + ?
            WHERE user_id = ?
            """,
            (count, user_id),
        )
        self._connection.commit()

    def consume_project_credit(self, user_id: str) -> bool:
        self.ensure_user(user_id)
        cursor = self._connection.execute(
            """
            UPDATE billing_accounts
            SET project_credits = project_credits - 1
            WHERE user_id = ? AND project_credits > 0
            """,
            (user_id,),
        )
        self._connection.commit()
        return cursor.rowcount == 1

    def consume_free_generation(self, user_id: str) -> bool:
        self.ensure_user(user_id)
        cursor = self._connection.execute(
            """
            UPDATE billing_accounts
            SET free_generation_available = 0
            WHERE user_id = ? AND free_generation_available = 1
            """,
            (user_id,),
        )
        self._connection.commit()
        return cursor.rowcount == 1

    def get_project_grant(self, user_id: str, project_id: str) -> ProjectGrant | None:
        row = self._connection.execute(
            """
            SELECT user_id, project_id, source
            FROM billing_project_grants
            WHERE user_id = ? AND project_id = ?
            """,
            (user_id, project_id),
        ).fetchone()
        if row is None:
            return None
        return ProjectGrant(
            user_id=row["user_id"], project_id=row["project_id"], source=row["source"]
        )

    def add_project_grant(self, user_id: str, project_id: str, source: str) -> None:
        self._connection.execute(
            """
            INSERT INTO billing_project_grants(user_id, project_id, source)
            VALUES (?, ?, ?)
            """,
            (user_id, project_id, source),
        )
        self._connection.commit()

    def update_project_grant_source(
        self, user_id: str, project_id: str, source: str
    ) -> None:
        cursor = self._connection.execute(
            """
            UPDATE billing_project_grants SET source = ?
            WHERE user_id = ? AND project_id = ?
            """,
            (source, user_id, project_id),
        )
        self._connection.commit()
        if cursor.rowcount != 1:
            raise ValueError("Project grant does not exist.")

    def has_pending_free_project(self, user_id: str) -> bool:
        row = self._connection.execute(
            """
            SELECT 1 FROM billing_project_grants
            WHERE user_id = ? AND source = 'free_trial_pending'
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return row is not None

    def set_subscription(
        self,
        user_id: str,
        sku: str | None,
        status: SubscriptionStatus,
        period_end: datetime | None,
        provider_subscription_id: str | None,
    ) -> None:
        self.ensure_user(user_id)
        self._connection.execute(
            """
            UPDATE billing_accounts
            SET active_subscription_sku = ?,
                subscription_status = ?,
                subscription_period_end = ?,
                provider_subscription_id = ?
            WHERE user_id = ?
            """,
            (
                sku,
                status.value,
                period_end.isoformat() if period_end else None,
                provider_subscription_id,
                user_id,
            ),
        )
        self._connection.commit()

    def record_event_once(
        self, provider: str, event_key: str, event_type: str
    ) -> bool:
        cursor = self._connection.execute(
            """
            INSERT OR IGNORE INTO billing_events(provider, event_key, event_type)
            VALUES (?, ?, ?)
            """,
            (provider, event_key, event_type),
        )
        self._connection.commit()
        return cursor.rowcount == 1

    def close(self) -> None:
        self._connection.close()
