from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import cast

from .catalog import ProductKind, get_product
from .models import (
    EntitlementSnapshot,
    NewPaymentOrder,
    PaymentOrder,
    PaymentOrderConflictError,
    PaymentOrderStateError,
    PaymentOrderStatus,
    ProjectGrant,
    SubscriptionStatus,
)

_SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 30000;

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
    merchant_order_id TEXT,
    user_id TEXT,
    sku TEXT,
    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provider, event_key)
);

CREATE TABLE IF NOT EXISTS billing_payment_orders (
    provider TEXT NOT NULL,
    merchant_order_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    currency TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    provider_order_id TEXT,
    checkout_url TEXT,
    expires_at TEXT,
    failure_code TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    fulfilled_at TEXT,
    PRIMARY KEY (provider, merchant_order_id),
    UNIQUE (provider, user_id, idempotency_key)
);

CREATE UNIQUE INDEX IF NOT EXISTS billing_payment_orders_provider_order_idx
    ON billing_payment_orders(provider, provider_order_id)
    WHERE provider_order_id IS NOT NULL;
"""


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _payment_order_from_row(row: sqlite3.Row) -> PaymentOrder:
    created_at = _parse_datetime(row["created_at"])
    updated_at = _parse_datetime(row["updated_at"])
    assert created_at is not None
    assert updated_at is not None
    return PaymentOrder(
        merchant_order_id=str(row["merchant_order_id"]),
        user_id=str(row["user_id"]),
        sku=str(row["sku"]),
        provider=str(row["provider"]),
        amount_paise=int(row["amount_paise"]),
        currency=str(row["currency"]),
        idempotency_key=str(row["idempotency_key"]),
        status=PaymentOrderStatus(str(row["status"])),
        provider_order_id=row["provider_order_id"],
        checkout_url=row["checkout_url"],
        expires_at=_parse_datetime(row["expires_at"]),
        failure_code=row["failure_code"],
        created_at=created_at,
        updated_at=updated_at,
        fulfilled_at=_parse_datetime(row["fulfilled_at"]),
    )


class SqliteBillingRepository:
    def __init__(self, path: Path | str) -> None:
        self._connection = sqlite3.connect(str(path), timeout=30.0)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(_SCHEMA)
        self._migrate_existing_event_table()
        self._connection.commit()

    def _migrate_existing_event_table(self) -> None:
        columns = {
            str(row["name"])
            for row in self._connection.execute("PRAGMA table_info(billing_events)")
        }
        for name in ("merchant_order_id", "user_id", "sku"):
            if name not in columns:
                self._connection.execute(f"ALTER TABLE billing_events ADD COLUMN {name} TEXT")

    @contextmanager
    def _write_transaction(self) -> Iterator[sqlite3.Cursor]:
        self._connection.execute("BEGIN IMMEDIATE")
        cursor = self._connection.cursor()
        try:
            yield cursor
        except BaseException:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()
        finally:
            cursor.close()

    @staticmethod
    def _ensure_user_with_cursor(cursor: sqlite3.Cursor, user_id: str) -> None:
        cursor.execute("INSERT OR IGNORE INTO billing_accounts(user_id) VALUES (?)", (user_id,))

    @staticmethod
    def _select_payment_order(
        cursor: sqlite3.Cursor, provider: str, merchant_order_id: str
    ) -> sqlite3.Row | None:
        return cast(
            sqlite3.Row | None,
            cursor.execute(
            """
            SELECT * FROM billing_payment_orders
            WHERE provider = ? AND merchant_order_id = ?
            """,
            (provider, merchant_order_id),
            ).fetchone(),
        )

    @staticmethod
    def _validate_same_purchase(existing: PaymentOrder, requested: NewPaymentOrder) -> None:
        if (
            existing.user_id != requested.user_id
            or existing.sku != requested.sku
            or existing.provider != requested.provider
            or existing.amount_paise != requested.amount_paise
            or existing.currency != requested.currency
        ):
            raise PaymentOrderConflictError(
                "The idempotency key is already bound to a different purchase."
            )

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
        return EntitlementSnapshot(
            user_id=row["user_id"],
            free_generation_available=bool(row["free_generation_available"]),
            project_credits=int(row["project_credits"]),
            active_subscription_sku=row["active_subscription_sku"],
            subscription_status=SubscriptionStatus(row["subscription_status"]),
            subscription_period_end=_parse_datetime(row["subscription_period_end"]),
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

    def update_project_grant_source(self, user_id: str, project_id: str, source: str) -> None:
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

    def record_event_once(self, provider: str, event_key: str, event_type: str) -> bool:
        cursor = self._connection.execute(
            """
            INSERT OR IGNORE INTO billing_events(provider, event_key, event_type)
            VALUES (?, ?, ?)
            """,
            (provider, event_key, event_type),
        )
        self._connection.commit()
        return cursor.rowcount == 1

    def create_or_get_payment_order(
        self, order: NewPaymentOrder
    ) -> tuple[PaymentOrder, bool]:
        if not all(
            (
                order.merchant_order_id,
                order.user_id,
                order.sku,
                order.provider,
                order.currency,
                order.idempotency_key,
            )
        ):
            raise ValueError("Payment order identifiers and currency must not be empty.")
        if order.amount_paise <= 0:
            raise ValueError("Payment order amount must be positive.")

        with self._write_transaction() as cursor:
            cursor.execute(
                """
                INSERT OR IGNORE INTO billing_payment_orders(
                    provider, merchant_order_id, user_id, sku, amount_paise,
                    currency, idempotency_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.provider,
                    order.merchant_order_id,
                    order.user_id,
                    order.sku,
                    order.amount_paise,
                    order.currency,
                    order.idempotency_key,
                ),
            )
            created = cursor.rowcount == 1
            if created:
                row = self._select_payment_order(
                    cursor, order.provider, order.merchant_order_id
                )
            else:
                row = cursor.execute(
                    """
                    SELECT * FROM billing_payment_orders
                    WHERE provider = ? AND user_id = ? AND idempotency_key = ?
                    """,
                    (order.provider, order.user_id, order.idempotency_key),
                ).fetchone()
                if row is None:
                    raise PaymentOrderConflictError(
                        "The merchant payment order identifier is already in use."
                    )
            assert row is not None
            persisted = _payment_order_from_row(row)
            self._validate_same_purchase(persisted, order)
            return persisted, created

    def get_payment_order(
        self, provider: str, merchant_order_id: str
    ) -> PaymentOrder | None:
        row = self._connection.execute(
            """
            SELECT * FROM billing_payment_orders
            WHERE provider = ? AND merchant_order_id = ?
            """,
            (provider, merchant_order_id),
        ).fetchone()
        return _payment_order_from_row(row) if row is not None else None

    def list_reconcilable_payment_orders(
        self, provider: str, limit: int
    ) -> list[PaymentOrder]:
        bounded_limit = min(max(limit, 1), 500)
        rows = self._connection.execute(
            """
            SELECT * FROM billing_payment_orders
            WHERE provider = ? AND status IN (?, ?, ?)
            ORDER BY created_at ASC, merchant_order_id ASC
            LIMIT ?
            """,
            (
                provider,
                PaymentOrderStatus.PENDING.value,
                PaymentOrderStatus.CHECKOUT_CREATED.value,
                PaymentOrderStatus.CHECKOUT_UNKNOWN.value,
                bounded_limit,
            ),
        ).fetchall()
        return [_payment_order_from_row(row) for row in rows]

    def mark_checkout_created(
        self,
        *,
        provider: str,
        merchant_order_id: str,
        provider_order_id: str,
        checkout_url: str,
        expires_at: datetime | None,
    ) -> PaymentOrder:
        with self._write_transaction() as cursor:
            row = self._select_payment_order(cursor, provider, merchant_order_id)
            if row is None:
                raise LookupError("Payment order does not exist.")
            order = _payment_order_from_row(row)
            if order.status == PaymentOrderStatus.FULFILLED:
                return order
            if order.status == PaymentOrderStatus.CHECKOUT_FAILED:
                raise PaymentOrderStateError("A failed checkout cannot be recreated.")
            if order.status == PaymentOrderStatus.CHECKOUT_CREATED:
                if (
                    order.provider_order_id == provider_order_id
                    and order.checkout_url == checkout_url
                    and order.expires_at == expires_at
                ):
                    return order
                raise PaymentOrderConflictError(
                    "Checkout details conflict with the persisted payment order."
                )
            cursor.execute(
                """
                UPDATE billing_payment_orders
                SET status = ?, provider_order_id = ?, checkout_url = ?,
                    expires_at = ?, failure_code = NULL,
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE provider = ? AND merchant_order_id = ?
                """,
                (
                    PaymentOrderStatus.CHECKOUT_CREATED.value,
                    provider_order_id,
                    checkout_url,
                    expires_at.isoformat() if expires_at else None,
                    provider,
                    merchant_order_id,
                ),
            )
            updated = self._select_payment_order(cursor, provider, merchant_order_id)
            assert updated is not None
            return _payment_order_from_row(updated)

    def _mark_checkout_outcome(
        self,
        *,
        provider: str,
        merchant_order_id: str,
        failure_code: str,
        target: PaymentOrderStatus,
    ) -> PaymentOrder:
        with self._write_transaction() as cursor:
            row = self._select_payment_order(cursor, provider, merchant_order_id)
            if row is None:
                raise LookupError("Payment order does not exist.")
            order = _payment_order_from_row(row)
            if order.status == PaymentOrderStatus.FULFILLED:
                return order
            if (
                target == PaymentOrderStatus.CHECKOUT_UNKNOWN
                and order.status
                in {
                    PaymentOrderStatus.CHECKOUT_CREATED,
                    PaymentOrderStatus.CHECKOUT_FAILED,
                }
            ):
                return order
            if (
                target == PaymentOrderStatus.CHECKOUT_FAILED
                and order.status == PaymentOrderStatus.CHECKOUT_FAILED
            ):
                return order
            cursor.execute(
                """
                UPDATE billing_payment_orders
                SET status = ?, failure_code = ?,
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE provider = ? AND merchant_order_id = ?
                """,
                (target.value, failure_code, provider, merchant_order_id),
            )
            updated = self._select_payment_order(cursor, provider, merchant_order_id)
            assert updated is not None
            return _payment_order_from_row(updated)

    def mark_checkout_unknown(
        self,
        *,
        provider: str,
        merchant_order_id: str,
        failure_code: str,
    ) -> PaymentOrder:
        return self._mark_checkout_outcome(
            provider=provider,
            merchant_order_id=merchant_order_id,
            failure_code=failure_code,
            target=PaymentOrderStatus.CHECKOUT_UNKNOWN,
        )

    def mark_checkout_failed(
        self,
        *,
        provider: str,
        merchant_order_id: str,
        failure_code: str,
    ) -> PaymentOrder:
        return self._mark_checkout_outcome(
            provider=provider,
            merchant_order_id=merchant_order_id,
            failure_code=failure_code,
            target=PaymentOrderStatus.CHECKOUT_FAILED,
        )

    @staticmethod
    def _insert_event_once(
        cursor: sqlite3.Cursor,
        *,
        provider: str,
        event_key: str,
        event_type: str,
        merchant_order_id: str | None,
        user_id: str | None,
        sku: str | None,
    ) -> bool:
        cursor.execute(
            """
            INSERT OR IGNORE INTO billing_events(
                provider, event_key, event_type, merchant_order_id, user_id, sku
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (provider, event_key, event_type, merchant_order_id, user_id, sku),
        )
        if cursor.rowcount == 1:
            return True
        existing = cursor.execute(
            """
            SELECT event_type, merchant_order_id, user_id, sku
            FROM billing_events WHERE provider = ? AND event_key = ?
            """,
            (provider, event_key),
        ).fetchone()
        assert existing is not None
        if (
            existing["event_type"] != event_type
            or existing["merchant_order_id"] != merchant_order_id
            or existing["user_id"] != user_id
            or existing["sku"] != sku
        ):
            raise PaymentOrderConflictError(
                "The provider event key is already bound to different billing data."
            )
        return False

    def apply_payment_order_event(
        self,
        *,
        provider: str,
        event_key: str,
        event_type: str,
        merchant_order_id: str,
        provider_order_id: str,
        amount_paise: int,
        currency: str,
    ) -> bool:
        with self._write_transaction() as cursor:
            row = self._select_payment_order(cursor, provider, merchant_order_id)
            if row is None:
                raise LookupError("Payment order does not exist.")
            order = _payment_order_from_row(row)
            if order.amount_paise != amount_paise or order.currency != currency:
                raise PaymentOrderConflictError(
                    "Provider payment amount or currency does not match the order."
                )
            if order.provider_order_id not in {None, provider_order_id}:
                raise PaymentOrderConflictError(
                    "Provider order identifier does not match the payment order."
                )
            if order.status == PaymentOrderStatus.FULFILLED:
                return False

            product = get_product(order.sku)
            if product.kind not in {ProductKind.PROJECT, ProductKind.PROJECT_PACK}:
                raise ValueError("Payment order is not a one-time project product.")
            inserted = self._insert_event_once(
                cursor,
                provider=provider,
                event_key=event_key,
                event_type=event_type,
                merchant_order_id=merchant_order_id,
                user_id=order.user_id,
                sku=order.sku,
            )
            if not inserted:
                return False

            self._ensure_user_with_cursor(cursor, order.user_id)
            cursor.execute(
                """
                UPDATE billing_accounts
                SET project_credits = project_credits + ?
                WHERE user_id = ?
                """,
                (product.project_credits, order.user_id),
            )
            cursor.execute(
                """
                UPDATE billing_payment_orders
                SET status = ?, provider_order_id = COALESCE(provider_order_id, ?),
                    failure_code = NULL,
                    fulfilled_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE provider = ? AND merchant_order_id = ?
                """,
                (
                    PaymentOrderStatus.FULFILLED.value,
                    provider_order_id,
                    provider,
                    merchant_order_id,
                ),
            )
            return True

    def apply_legacy_one_time_event(
        self,
        *,
        provider: str,
        event_key: str,
        event_type: str,
        user_id: str,
        sku: str,
    ) -> bool:
        product = get_product(sku)
        if product.kind not in {ProductKind.PROJECT, ProductKind.PROJECT_PACK}:
            raise ValueError("SKU is not a one-time project product.")
        with self._write_transaction() as cursor:
            inserted = self._insert_event_once(
                cursor,
                provider=provider,
                event_key=event_key,
                event_type=event_type,
                merchant_order_id=None,
                user_id=user_id,
                sku=sku,
            )
            if not inserted:
                return False
            self._ensure_user_with_cursor(cursor, user_id)
            cursor.execute(
                """
                UPDATE billing_accounts
                SET project_credits = project_credits + ?
                WHERE user_id = ?
                """,
                (product.project_credits, user_id),
            )
            return True

    def apply_legacy_subscription_event(
        self,
        *,
        provider: str,
        event_key: str,
        event_type: str,
        user_id: str,
        sku: str,
        status: SubscriptionStatus,
        provider_subscription_id: str,
        period_end: datetime | None,
    ) -> bool:
        product = get_product(sku)
        if product.kind != ProductKind.SUBSCRIPTION:
            raise ValueError("SKU is not a subscription.")
        with self._write_transaction() as cursor:
            inserted = self._insert_event_once(
                cursor,
                provider=provider,
                event_key=event_key,
                event_type=event_type,
                merchant_order_id=None,
                user_id=user_id,
                sku=sku,
            )
            if not inserted:
                return False
            self._ensure_user_with_cursor(cursor, user_id)
            active_sku = sku if status == SubscriptionStatus.ACTIVE else None
            cursor.execute(
                """
                UPDATE billing_accounts
                SET active_subscription_sku = ?, subscription_status = ?,
                    subscription_period_end = ?, provider_subscription_id = ?
                WHERE user_id = ?
                """,
                (
                    active_sku,
                    status.value,
                    period_end.isoformat() if period_end else None,
                    provider_subscription_id,
                    user_id,
                ),
            )
            return True

    def close(self) -> None:
        self._connection.close()
