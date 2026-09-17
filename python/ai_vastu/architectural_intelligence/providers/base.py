from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ai_vastu.requirements.models import ConfirmedRequirements

from ..models import ArchitecturalDesignIntent


@dataclass(frozen=True, slots=True)
class ArchitecturalReasoningInput:
    confirmed: ConfirmedRequirements
    original_prompt: str


class ArchitecturalIntelligenceProvider(Protocol):
    name: str

    def reason(
        self,
        request: ArchitecturalReasoningInput,
    ) -> ArchitecturalDesignIntent: ...
