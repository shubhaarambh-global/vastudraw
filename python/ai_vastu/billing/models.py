from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class SubscriptionStatus(StrEnum):
    NONE = "none"
    ACTIVE = "active"
    AUTHENTICATED = "authenticated"
    PAUSED = "paused"
    HALTED = "halted"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class PaymentOrderStatus(StrEnum):
    PENDING = "pending"
    CHECKOUT_CREATED = "checkout_created"
    CHECKOUT_UNKNOWN = "checkout_unknown"
    CHECKOUT_FAILED = "checkout_failed"
    FULFILLED = "fulfilled"


class PaymentOrderConflictError(ValueError):
    """Raised when an idempotency key is reused for a different purchase."""


class PaymentOrderStateError(ValueError):
    """Raised when a payment order cannot make the requested state transition."""


@dataclass(frozen=True, slots=True)
class EntitlementSnapshot:
    user_id: str
    free_generation_available: bool
    project_credits: int
    active_subscription_sku: str | None
    subscription_status: SubscriptionStatus
    subscription_period_end: datetime | None

    @property
    def has_active_subscription(self) -> bool:
        period_end = self.subscription_period_end
        return (
            self.subscription_status == SubscriptionStatus.ACTIVE
            and period_end is not None
            and period_end.tzinfo is not None
            and period_end > datetime.now(UTC)
        )


@dataclass(frozen=True, slots=True)
class ProjectGrant:
    user_id: str
    project_id: str
    source: str


@dataclass(frozen=True, slots=True)
class GenerationAuthorization:
    allowed: bool
    reason: str
    consumption: str | None = None


@dataclass(frozen=True, slots=True)
class CheckoutSession:
    sku: str
    provider: str
    provider_reference_id: str
    checkout_url: str


@dataclass(frozen=True, slots=True)
class NewPaymentOrder:
    merchant_order_id: str
    user_id: str
    sku: str
    provider: str
    amount_paise: int
    currency: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class PaymentOrder:
    merchant_order_id: str
    user_id: str
    sku: str
    provider: str
    amount_paise: int
    currency: str
    idempotency_key: str
    status: PaymentOrderStatus
    provider_order_id: str | None
    checkout_url: str | None
    expires_at: datetime | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime
    fulfilled_at: datetime | None
