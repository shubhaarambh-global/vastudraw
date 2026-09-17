from __future__ import annotations

from ai_vastu.requirements.generation_profile import normalize_room_type

from ..models import (
    RuleApplicability,
    VastuInfluenceMode,
    VastuReasoningProfile,
    VastuRuleReasoning,
)
from .base import VastuReasoningInput


class FixtureVastuReasoningProvider:
    """Deterministic offline provider for tests and local development."""

    name = "fixture"

    def reason(self, request: VastuReasoningInput) -> VastuReasoningProfile:
        present = {normalize_room_type(item.room_type) for item in request.confirmed.rooms}

        reasoning: list[VastuRuleReasoning] = []
        for rule in request.catalog.rules:
            if rule.subject_room_types:
                applies = any(room_type in present for room_type in rule.subject_room_types)
                applicability = (
                    RuleApplicability.APPLICABLE if applies else RuleApplicability.NOT_APPLICABLE
                )
            else:
                applicability = RuleApplicability.CONTEXT_DEPENDENT

            reasoning.append(
                VastuRuleReasoning(
                    rule_id=rule.rule_id,
                    applicability=applicability,
                    importance=rule.default_importance,
                    flexibility=rule.default_flexibility,
                    weight_multiplier_basis_points=10_000,
                    rationale=(
                        "Deterministic fixture uses the source-backed catalog defaults "
                        "without inventing new Vastu rules."
                    ),
                )
            )

        # We intentionally leave influence weights to the service because they
        # come from confirmed/user-selected mode, not from the provider.
        return VastuReasoningProfile(
            project_id=request.confirmed.project_id,
            draft_id=request.confirmed.draft_id,
            provider=self.name,
            model=None,
            influence_mode=VastuInfluenceMode.BALANCED,
            architecture_weight_basis_points=5_000,
            vastu_weight_basis_points=5_000,
            rules=tuple(reasoning),
            notes=("Fixture provider: catalog defaults only.",),
        ).with_content_hash()
