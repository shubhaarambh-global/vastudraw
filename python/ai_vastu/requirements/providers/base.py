from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ai_vastu.requirements.models import RequirementDraft


@dataclass(frozen=True, slots=True)
class ReferenceAsset:
    filename: str
    content_type: str
    data: bytes


@dataclass(frozen=True, slots=True)
class InterpretationInput:
    draft_id: UUID
    user_id: UUID
    project_id: UUID
    prompt: str
    references: tuple[ReferenceAsset, ...]


class RequirementsProvider(Protocol):
    name: str

    def interpret(self, request: InterpretationInput) -> RequirementDraft: ...
