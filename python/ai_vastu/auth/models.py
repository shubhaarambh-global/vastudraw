from __future__ import annotations

from uuid import UUID

from ai_vastu.plan_schema.base import FrozenModel


class AuthenticatedUser(FrozenModel):
    user_id: UUID
    role: str
    email: str | None = None
