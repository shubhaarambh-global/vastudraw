from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .models import (
    EntitlementSnapshot,
    NewPaymentOrder,
    PaymentOrder,
    ProjectGrant,
    SubscriptionStatus,
)


class BillingRepository(Protocol):
    def ensure_user(self, user_id: str) -> None: ...

    def get_snapshot(self, user_id: str) -> EntitlementSnapshot: ...

    def grant_project_credits(self, user_id: str, count: int) -> None: ...

    def consume_project_credit(self, user_id: str) -> bool: ...

    def consume_free_generation(self, user_id: str) -> bool: ...

    def get_project_grant(self, user_id: str, project_id: str) -> ProjectGrant | None: ...

    def add_project_grant(self, user_id: str, project_id: str, source: str) -> None: ...

    def update_project_grant_source(self, user_id: str, project_id: str, source: str) -> None: ...

    def has_pending_free_project(self, user_id: str) -> bool: ...

    def set_subscription(
        self,
        user_id: str,
        sku: str | None,
        status: SubscriptionStatus,
        period_end: datetime | None,
        provider_subscription_id: str | None,
    ) -> None: ...

    def record_event_once(self, provider: str, event_key: str, event_type: str) -> bool: ...

    def create_or_get_payment_order(
        self, order: NewPaymentOrder
    ) -> tuple[PaymentOrder, bool]: ...

    def get_payment_order(
        self, provider: str, merchant_order_id: str
    ) -> PaymentOrder | None: ...

    def list_reconcilable_payment_orders(
        self, provider: str, limit: int
    ) -> list[PaymentOrder]: ...

    def mark_checkout_created(
        self,
        *,
        provider: str,
        merchant_order_id: str,
        provider_order_id: str,
        checkout_url: str,
        expires_at: datetime | None,
    ) -> PaymentOrder: ...

    def mark_checkout_unknown(
        self,
        *,
        provider: str,
        merchant_order_id: str,
        failure_code: str,
    ) -> PaymentOrder: ...

    def mark_checkout_failed(
        self,
        *,
        provider: str,
        merchant_order_id: str,
        failure_code: str,
    ) -> PaymentOrder: ...

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
    ) -> bool: ...

    def apply_legacy_one_time_event(
        self,
        *,
        provider: str,
        event_key: str,
        event_type: str,
        user_id: str,
        sku: str,
    ) -> bool: ...

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
    ) -> bool: ...

    def close(self) -> None: ...
