from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SubscriptionStatus(StrEnum):
    NONE = "none"
    ACTIVE = "active"
    AUTHENTICATED = "authenticated"
    PAUSED = "paused"
    HALTED = "halted"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


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
        return self.subscription_status == SubscriptionStatus.ACTIVE


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
