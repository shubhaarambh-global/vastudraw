from __future__ import annotations

import os
from datetime import datetime

from .catalog import ProductKind, get_product
from .models import (
    EntitlementSnapshot,
    GenerationAuthorization,
    NewPaymentOrder,
    PaymentOrder,
    SubscriptionStatus,
)
from .repository import BillingRepository


def development_billing_bypass_enabled() -> bool:
    """Allow unrestricted generation only in an explicitly opted-in dev environment."""
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    requested = (
        os.getenv("AI_VASTU_DEV_BILLING_BYPASS", "")
        .strip()
        .lower()
        in {"1", "true", "yes", "on"}
    )
    return app_env == "development" and requested


class BillingService:
    def __init__(
        self,
        repository: BillingRepository,
        *,
        development_bypass: bool = False,
    ) -> None:
        self._repository = repository
        self._development_bypass = development_bypass

    def snapshot(self, user_id: str) -> EntitlementSnapshot:
        return self._repository.get_snapshot(user_id)

    def register_project(self, user_id: str, project_id: str) -> str:
        existing = self._repository.get_project_grant(user_id, project_id)
        if existing is not None:
            return existing.source

        snapshot = self._repository.get_snapshot(user_id)
        if snapshot.has_active_subscription:
            source = "subscription"
        elif self._repository.consume_project_credit(user_id):
            source = "project_credit"
        elif snapshot.free_generation_available and not self._repository.has_pending_free_project(
            user_id
        ):
            source = "free_trial_pending"
        else:
            raise PermissionError("No project entitlement is available.")

        self._repository.add_project_grant(user_id, project_id, source)
        return source

    def authorize_generation(self, user_id: str, project_id: str) -> GenerationAuthorization:
        if self._development_bypass:
            return GenerationAuthorization(
                allowed=True,
                reason="development_bypass",
                consumption=None,
            )

        snapshot = self._repository.get_snapshot(user_id)
        if snapshot.has_active_subscription:
            return GenerationAuthorization(
                allowed=True, reason="active_subscription", consumption=None
            )

        grant = self._repository.get_project_grant(user_id, project_id)
        if grant is None:
            return GenerationAuthorization(
                allowed=False, reason="project_not_entitled", consumption=None
            )

        if grant.source == "project_credit":
            return GenerationAuthorization(allowed=True, reason="paid_project", consumption=None)
        if grant.source == "free_trial_pending" and snapshot.free_generation_available:
            return GenerationAuthorization(
                allowed=True,
                reason="free_first_generation",
                consumption="free_generation",
            )
        if grant.source == "free_trial_used":
            return GenerationAuthorization(
                allowed=False, reason="free_generation_used", consumption=None
            )
        if grant.source == "subscription":
            return GenerationAuthorization(
                allowed=False, reason="subscription_inactive", consumption=None
            )

        return GenerationAuthorization(
            allowed=False, reason="unknown_entitlement", consumption=None
        )

    def record_successful_generation(self, user_id: str, project_id: str) -> None:
        authorization = self.authorize_generation(user_id, project_id)
        if not authorization.allowed:
            raise PermissionError(authorization.reason)
        if authorization.consumption != "free_generation":
            return

        if not self._repository.consume_free_generation(user_id):
            raise PermissionError("Free generation was already consumed.")
        self._repository.update_project_grant_source(user_id, project_id, "free_trial_used")

    def create_or_get_payment_order(
        self,
        *,
        merchant_order_id: str,
        idempotency_key: str,
        user_id: str,
        sku: str,
        provider: str,
    ) -> tuple[PaymentOrder, bool]:
        product = get_product(sku)
        if product.kind == ProductKind.FREE:
            raise ValueError("The free SKU does not create a payment order.")
        return self._repository.create_or_get_payment_order(
            NewPaymentOrder(
                merchant_order_id=merchant_order_id,
                user_id=user_id,
                sku=product.sku,
                provider=provider,
                amount_paise=product.amount_paise,
                currency=product.currency,
                idempotency_key=idempotency_key,
            )
        )

    def get_payment_order(
        self, provider: str, merchant_order_id: str
    ) -> PaymentOrder | None:
        return self._repository.get_payment_order(provider, merchant_order_id)

    def list_reconcilable_payment_orders(
        self, provider: str, limit: int
    ) -> list[PaymentOrder]:
        return self._repository.list_reconcilable_payment_orders(provider, limit)

    def mark_checkout_created(
        self,
        *,
        provider: str,
        merchant_order_id: str,
        provider_order_id: str,
        checkout_url: str,
        expires_at: datetime | None,
    ) -> PaymentOrder:
        return self._repository.mark_checkout_created(
            provider=provider,
            merchant_order_id=merchant_order_id,
            provider_order_id=provider_order_id,
            checkout_url=checkout_url,
            expires_at=expires_at,
        )

    def mark_checkout_unknown(
        self,
        *,
        provider: str,
        merchant_order_id: str,
        failure_code: str,
    ) -> PaymentOrder:
        return self._repository.mark_checkout_unknown(
            provider=provider,
            merchant_order_id=merchant_order_id,
            failure_code=failure_code,
        )

    def mark_checkout_failed(
        self,
        *,
        provider: str,
        merchant_order_id: str,
        failure_code: str,
    ) -> PaymentOrder:
        return self._repository.mark_checkout_failed(
            provider=provider,
            merchant_order_id=merchant_order_id,
            failure_code=failure_code,
        )

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
        return self._repository.apply_payment_order_event(
            provider=provider,
            event_key=event_key,
            event_type=event_type,
            merchant_order_id=merchant_order_id,
            provider_order_id=provider_order_id,
            amount_paise=amount_paise,
            currency=currency,
        )

    def apply_one_time_purchase(
        self,
        event_key: str,
        user_id: str,
        sku: str,
        *,
        provider: str = "razorpay",
        event_type: str = "payment_link.paid",
    ) -> bool:
        product = get_product(sku)
        if product.kind not in {ProductKind.PROJECT, ProductKind.PROJECT_PACK}:
            raise ValueError("SKU is not a one-time project product.")
        return self._repository.apply_legacy_one_time_event(
            provider=provider,
            event_key=event_key,
            event_type=event_type,
            user_id=user_id,
            sku=sku,
        )

    def apply_subscription_event(
        self,
        *,
        event_key: str,
        event_type: str,
        user_id: str,
        sku: str,
        status: SubscriptionStatus,
        provider_subscription_id: str,
        period_end: datetime | None,
        provider: str = "razorpay",
    ) -> bool:
        product = get_product(sku)
        if product.kind != ProductKind.SUBSCRIPTION:
            raise ValueError("SKU is not a subscription.")
        return self._repository.apply_legacy_subscription_event(
            provider=provider,
            event_key=event_key,
            event_type=event_type,
            user_id=user_id,
            sku=sku,
            status=status,
            provider_subscription_id=provider_subscription_id,
            period_end=period_end,
        )
