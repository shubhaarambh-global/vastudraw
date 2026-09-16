from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .models import EntitlementSnapshot, ProjectGrant, SubscriptionStatus


class BillingRepository(Protocol):
    def ensure_user(self, user_id: str) -> None: ...

    def get_snapshot(self, user_id: str) -> EntitlementSnapshot: ...

    def grant_project_credits(self, user_id: str, count: int) -> None: ...

    def consume_project_credit(self, user_id: str) -> bool: ...

    def consume_free_generation(self, user_id: str) -> bool: ...

    def get_project_grant(self, user_id: str, project_id: str) -> ProjectGrant | None: ...

    def add_project_grant(self, user_id: str, project_id: str, source: str) -> None: ...

    def update_project_grant_source(
        self, user_id: str, project_id: str, source: str
    ) -> None: ...

    def has_pending_free_project(self, user_id: str) -> bool: ...

    def set_subscription(
        self,
        user_id: str,
        sku: str | None,
        status: SubscriptionStatus,
        period_end: datetime | None,
        provider_subscription_id: str | None,
    ) -> None: ...

    def record_event_once(
        self, provider: str, event_key: str, event_type: str
    ) -> bool: ...

    def close(self) -> None: ...
