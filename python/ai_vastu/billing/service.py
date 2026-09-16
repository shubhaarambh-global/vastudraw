from __future__ import annotations

from datetime import datetime

from .catalog import ProductKind, get_product
from .models import EntitlementSnapshot, GenerationAuthorization, SubscriptionStatus
from .repository import BillingRepository


class BillingService:
    def __init__(self, repository: BillingRepository) -> None:
        self._repository = repository

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
        elif (
            snapshot.free_generation_available
            and not self._repository.has_pending_free_project(user_id)
        ):
            source = "free_trial_pending"
        else:
            raise PermissionError("No project entitlement is available.")

        self._repository.add_project_grant(user_id, project_id, source)
        return source

    def authorize_generation(
        self, user_id: str, project_id: str
    ) -> GenerationAuthorization:
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
            return GenerationAuthorization(
                allowed=True, reason="paid_project", consumption=None
            )
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
        self._repository.update_project_grant_source(
            user_id, project_id, "free_trial_used"
        )

    def apply_one_time_purchase(
        self, event_key: str, user_id: str, sku: str
    ) -> bool:
        product = get_product(sku)
        if product.kind not in {ProductKind.PROJECT, ProductKind.PROJECT_PACK}:
            raise ValueError("SKU is not a one-time project product.")
        if not self._repository.record_event_once(
            "razorpay", event_key, "payment_link.paid"
        ):
            return False
        self._repository.grant_project_credits(user_id, product.project_credits)
        return True

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
    ) -> bool:
        product = get_product(sku)
        if product.kind != ProductKind.SUBSCRIPTION:
            raise ValueError("SKU is not a subscription.")
        if not self._repository.record_event_once("razorpay", event_key, event_type):
            return False

        active_sku = sku if status == SubscriptionStatus.ACTIVE else None
        self._repository.set_subscription(
            user_id=user_id,
            sku=active_sku,
            status=status,
            period_end=period_end,
            provider_subscription_id=provider_subscription_id,
        )
        return True
