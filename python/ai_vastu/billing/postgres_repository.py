from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

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


def _payment_order_from_mapping(row: dict[str, Any]) -> PaymentOrder:
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
        expires_at=row["expires_at"],
        failure_code=row["failure_code"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        fulfilled_at=row["fulfilled_at"],
    )


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

        with self._pool.connection() as connection:  # noqa: SIM117
            with connection.transaction(), connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO billing_payment_orders(
                        provider, merchant_order_id, user_id, sku, amount_paise,
                        currency, idempotency_key
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING *
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
                row = cursor.fetchone()
                created = row is not None
                if row is None:
                    cursor.execute(
                        """
                        SELECT * FROM billing_payment_orders
                        WHERE provider = %s AND user_id = %s AND idempotency_key = %s
                        """,
                        (order.provider, order.user_id, order.idempotency_key),
                    )
                    row = cursor.fetchone()
                    if row is None:
                        raise PaymentOrderConflictError(
                            "The merchant payment order identifier is already in use."
                        )
                persisted = _payment_order_from_mapping(cast(dict[str, Any], row))
                if (
                    persisted.user_id != order.user_id
                    or persisted.sku != order.sku
                    or persisted.provider != order.provider
                    or persisted.amount_paise != order.amount_paise
                    or persisted.currency != order.currency
                ):
                    raise PaymentOrderConflictError(
                        "The idempotency key is already bound to a different purchase."
                    )
                return persisted, created

    def get_payment_order(
        self, provider: str, merchant_order_id: str
    ) -> PaymentOrder | None:
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM billing_payment_orders
                WHERE provider = %s AND merchant_order_id = %s
                """,
                (provider, merchant_order_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return _payment_order_from_mapping(cast(dict[str, Any], row))

    def list_reconcilable_payment_orders(
        self, provider: str, limit: int
    ) -> list[PaymentOrder]:
        bounded_limit = min(max(limit, 1), 500)
        with self._pool.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM billing_payment_orders
                WHERE provider = %s AND status = ANY(%s)
                ORDER BY created_at ASC, merchant_order_id ASC
                LIMIT %s
                """,
                (
                    provider,
                    [
                        PaymentOrderStatus.PENDING.value,
                        PaymentOrderStatus.CHECKOUT_CREATED.value,
                        PaymentOrderStatus.CHECKOUT_UNKNOWN.value,
                    ],
                    bounded_limit,
                ),
            )
            rows = cursor.fetchall()
        return [
            _payment_order_from_mapping(cast(dict[str, Any], row)) for row in rows
        ]

    @staticmethod
    def _locked_payment_order(
        cursor: Any, provider: str, merchant_order_id: str
    ) -> PaymentOrder:
        cursor.execute(
            """
            SELECT * FROM billing_payment_orders
            WHERE provider = %s AND merchant_order_id = %s
            FOR UPDATE
            """,
            (provider, merchant_order_id),
        )
        row = cursor.fetchone()
        if row is None:
            raise LookupError("Payment order does not exist.")
        return _payment_order_from_mapping(cast(dict[str, Any], row))

    def mark_checkout_created(
        self,
        *,
        provider: str,
        merchant_order_id: str,
        provider_order_id: str,
        checkout_url: str,
        expires_at: datetime | None,
    ) -> PaymentOrder:
        with self._pool.connection() as connection:  # noqa: SIM117
            with connection.transaction(), connection.cursor() as cursor:
                order = self._locked_payment_order(cursor, provider, merchant_order_id)
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
                    SET status = %s, provider_order_id = %s, checkout_url = %s,
                        expires_at = %s, failure_code = NULL, updated_at = now()
                    WHERE provider = %s AND merchant_order_id = %s
                    RETURNING *
                    """,
                    (
                        PaymentOrderStatus.CHECKOUT_CREATED.value,
                        provider_order_id,
                        checkout_url,
                        expires_at,
                        provider,
                        merchant_order_id,
                    ),
                )
                row = cursor.fetchone()
                assert row is not None
                return _payment_order_from_mapping(cast(dict[str, Any], row))

    def _mark_checkout_outcome(
        self,
        *,
        provider: str,
        merchant_order_id: str,
        failure_code: str,
        target: PaymentOrderStatus,
    ) -> PaymentOrder:
        with self._pool.connection() as connection:  # noqa: SIM117
            with connection.transaction(), connection.cursor() as cursor:
                order = self._locked_payment_order(cursor, provider, merchant_order_id)
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
                    SET status = %s, failure_code = %s, updated_at = now()
                    WHERE provider = %s AND merchant_order_id = %s
                    RETURNING *
                    """,
                    (target.value, failure_code, provider, merchant_order_id),
                )
                row = cursor.fetchone()
                assert row is not None
                return _payment_order_from_mapping(cast(dict[str, Any], row))

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
        cursor: Any,
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
            INSERT INTO billing_events(
                provider, event_key, event_type, merchant_order_id, user_id, sku
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (provider, event_key) DO NOTHING
            """,
            (provider, event_key, event_type, merchant_order_id, user_id, sku),
        )
        if cursor.rowcount == 1:
            return True
        cursor.execute(
            """
            SELECT event_type, merchant_order_id, user_id, sku
            FROM billing_events WHERE provider = %s AND event_key = %s
            """,
            (provider, event_key),
        )
        existing = cursor.fetchone()
        assert existing is not None
        existing_map = cast(dict[str, Any], existing)
        if (
            existing_map["event_type"] != event_type
            or existing_map["merchant_order_id"] != merchant_order_id
            or existing_map["user_id"] != user_id
            or existing_map["sku"] != sku
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
        with self._pool.connection() as connection:  # noqa: SIM117
            with connection.transaction(), connection.cursor() as cursor:
                order = self._locked_payment_order(cursor, provider, merchant_order_id)
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
                cursor.execute(
                    """
                    INSERT INTO billing_accounts(user_id)
                    VALUES (%s)
                    ON CONFLICT (user_id) DO NOTHING
                    """,
                    (order.user_id,),
                )
                cursor.execute(
                    """
                    UPDATE billing_accounts
                    SET project_credits = project_credits + %s
                    WHERE user_id = %s
                    """,
                    (product.project_credits, order.user_id),
                )
                cursor.execute(
                    """
                    UPDATE billing_payment_orders
                    SET status = %s,
                        provider_order_id = COALESCE(provider_order_id, %s),
                        failure_code = NULL, fulfilled_at = now(), updated_at = now()
                    WHERE provider = %s AND merchant_order_id = %s
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
        with self._pool.connection() as connection:  # noqa: SIM117
            with connection.transaction(), connection.cursor() as cursor:
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
                cursor.execute(
                    """
                    INSERT INTO billing_accounts(user_id)
                    VALUES (%s)
                    ON CONFLICT (user_id) DO NOTHING
                    """,
                    (user_id,),
                )
                cursor.execute(
                    """
                    UPDATE billing_accounts
                    SET project_credits = project_credits + %s
                    WHERE user_id = %s
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
        with self._pool.connection() as connection:  # noqa: SIM117
            with connection.transaction(), connection.cursor() as cursor:
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
                cursor.execute(
                    """
                    INSERT INTO billing_accounts(user_id)
                    VALUES (%s)
                    ON CONFLICT (user_id) DO NOTHING
                    """,
                    (user_id,),
                )
                active_sku = sku if status == SubscriptionStatus.ACTIVE else None
                cursor.execute(
                    """
                    UPDATE billing_accounts
                    SET active_subscription_sku = %s, subscription_status = %s,
                        subscription_period_end = %s, provider_subscription_id = %s
                    WHERE user_id = %s
                    """,
                    (
                        active_sku,
                        status.value,
                        period_end,
                        provider_subscription_id,
                        user_id,
                    ),
                )
                return True

    def close(self) -> None:
        self._pool.close()
