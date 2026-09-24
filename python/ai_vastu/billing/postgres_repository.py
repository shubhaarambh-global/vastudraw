from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .models import EntitlementSnapshot, ProjectGrant, SubscriptionStatus


class PostgresBillingRepository:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("AI_VASTU_DATABASE_URL is required.")
        self._pool = ConnectionPool(
            database_url,
            min_size=1,
            max_size=5,
            kwargs={"autocommit": False, "prepare_threshold": None, "row_factory": dict_row},
        )

    def ensure_user(self, user_id: str) -> None:
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO billing_accounts(user_id)
                VALUES (%s)
                ON CONFLICT (user_id) DO NOTHING
                """,
                (user_id,),
            )
            connection.commit()

    def get_snapshot(self, user_id: str) -> EntitlementSnapshot:
        self.ensure_user(user_id)
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, free_generation_available, project_credits,
                       active_subscription_sku, subscription_status,
                       subscription_period_end
                FROM billing_accounts WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cursor.fetchone()
        assert row is not None
        row_map = cast(dict[str, Any], row)
        return EntitlementSnapshot(
            user_id=str(row_map["user_id"]),
            free_generation_available=bool(row_map["free_generation_available"]),
            project_credits=int(row_map["project_credits"]),
            active_subscription_sku=row_map["active_subscription_sku"],
            subscription_status=SubscriptionStatus(str(row_map["subscription_status"])),
            subscription_period_end=row_map["subscription_period_end"],
        )

    def grant_project_credits(self, user_id: str, count: int) -> None:
        if count <= 0:
            raise ValueError("Project credit grant must be positive.")
        self.ensure_user(user_id)
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE billing_accounts
                SET project_credits = project_credits + %s
                WHERE user_id = %s
                """,
                (count, user_id),
            )
            connection.commit()

    def consume_project_credit(self, user_id: str) -> bool:
        self.ensure_user(user_id)
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE billing_accounts
                SET project_credits = project_credits - 1
                WHERE user_id = %s AND project_credits > 0
                """,
                (user_id,),
            )
            changed = cursor.rowcount == 1
            connection.commit()
            return changed

    def consume_free_generation(self, user_id: str) -> bool:
        self.ensure_user(user_id)
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE billing_accounts
                SET free_generation_available = FALSE
                WHERE user_id = %s AND free_generation_available = TRUE
                """,
                (user_id,),
            )
            changed = cursor.rowcount == 1
            connection.commit()
            return changed

    def get_project_grant(self, user_id: str, project_id: str) -> ProjectGrant | None:
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, project_id, source
                FROM billing_project_grants
                WHERE user_id = %s AND project_id = %s
                """,
                (user_id, project_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        row_map = cast(dict[str, Any], row)
        return ProjectGrant(
            user_id=str(row_map["user_id"]),
            project_id=str(row_map["project_id"]),
            source=str(row_map["source"]),
        )

    def add_project_grant(self, user_id: str, project_id: str, source: str) -> None:
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO billing_project_grants(user_id, project_id, source)
                VALUES (%s, %s, %s)
                """,
                (user_id, project_id, source),
            )
            connection.commit()

    def update_project_grant_source(self, user_id: str, project_id: str, source: str) -> None:
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE billing_project_grants SET source = %s
                WHERE user_id = %s AND project_id = %s
                """,
                (source, user_id, project_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Project grant does not exist.")
            connection.commit()

    def has_pending_free_project(self, user_id: str) -> bool:
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM billing_project_grants
                WHERE user_id = %s AND source = 'free_trial_pending'
                LIMIT 1
                """,
                (user_id,),
            )
            return cursor.fetchone() is not None

    def set_subscription(
        self,
        user_id: str,
        sku: str | None,
        status: SubscriptionStatus,
        period_end: datetime | None,
        provider_subscription_id: str | None,
    ) -> None:
        self.ensure_user(user_id)
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE billing_accounts
                SET active_subscription_sku = %s,
                    subscription_status = %s,
                    subscription_period_end = %s,
                    provider_subscription_id = %s
                WHERE user_id = %s
                """,
                (
                    sku,
                    status.value,
                    period_end,
                    provider_subscription_id,
                    user_id,
                ),
            )
            connection.commit()

    def record_event_once(self, provider: str, event_key: str, event_type: str) -> bool:
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO billing_events(provider, event_key, event_type)
                VALUES (%s, %s, %s)
                ON CONFLICT (provider, event_key) DO NOTHING
                """,
                (provider, event_key, event_type),
            )
            inserted = cursor.rowcount == 1
            connection.commit()
            return inserted

    def close(self) -> None:
        self._pool.close()
