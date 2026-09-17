from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ai_vastu.requirements.models import ConfirmedRequirements

from ..models import SoftVastuCatalog, VastuReasoningProfile


@dataclass(frozen=True, slots=True)
class VastuReasoningInput:
    confirmed: ConfirmedRequirements
    original_prompt: str
    catalog: SoftVastuCatalog


class VastuReasoningProvider(Protocol):
    name: str

    def reason(self, request: VastuReasoningInput) -> VastuReasoningProfile: ...
