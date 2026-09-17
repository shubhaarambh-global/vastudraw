from __future__ import annotations

from ai_vastu.requirements.models import VastuMode
from ai_vastu.vastu_reasoning import (
    RuleApplicability,
    RuleFlexibility,
    RuleImportance,
    VastuInfluenceMode,
    VastuReasoningProfile,
    VastuRuleReasoning,
)
from ai_vastu.vastu_reasoning.providers.base import VastuReasoningInput
from ai_vastu.vastu_reasoning.service import (
    VastuReasoningService,
    influence_mode_for_confirmed,
)

from .helpers import confirmed


class DowngradeProvider:
    name = "test"

    def reason(self, request: VastuReasoningInput) -> VastuReasoningProfile:
        rules = []
        for rule in request.catalog.rules:
            rules.append(
                VastuRuleReasoning(
                    rule_id=rule.rule_id,
                    applicability=RuleApplicability.APPLICABLE,
                    importance=(
                        RuleImportance.NEGLIGIBLE
                        if rule.rule_id == "SOFT_KITCHEN_ZONE"
                        else rule.default_importance
                    ),
                    flexibility=(
                        RuleFlexibility.FLEXIBLE
                        if rule.rule_id == "SOFT_KITCHEN_ZONE"
                        else rule.default_flexibility
                    ),
                    weight_multiplier_basis_points=1
                    if rule.rule_id == "SOFT_KITCHEN_ZONE"
                    else 10_000,
                    rationale="Test contextual reasoning.",
                )
            )
        return VastuReasoningProfile(
            project_id=request.confirmed.project_id,
            draft_id=request.confirmed.draft_id,
            provider=self.name,
            model=None,
            influence_mode=VastuInfluenceMode.BALANCED,
            architecture_weight_basis_points=5000,
            vastu_weight_basis_points=5000,
            rules=tuple(rules),
        ).with_content_hash()


def test_legacy_modes_map_to_requested_30_50_70_policy() -> None:
    assert (
        influence_mode_for_confirmed(confirmed(VastuMode.SPACE_EFFICIENT))
        is VastuInfluenceMode.PRACTICAL
    )
    assert (
        influence_mode_for_confirmed(confirmed(VastuMode.BALANCED)) is VastuInfluenceMode.BALANCED
    )
    assert (
        influence_mode_for_confirmed(confirmed(VastuMode.STRICT))
        is VastuInfluenceMode.VASTU_FORWARD
    )


def test_non_adjustable_core_rule_cannot_be_downgraded(monkeypatch) -> None:
    monkeypatch.delenv("AI_VASTU_VASTU_INFLUENCE_MODE", raising=False)
    source = confirmed()
    profile = VastuReasoningService(DowngradeProvider()).reason(
        confirmed=source,
        original_prompt="Plan a balanced 2BHK.",
    )
    kitchen = next(item for item in profile.rules if item.rule_id == "SOFT_KITCHEN_ZONE")
    assert kitchen.importance is RuleImportance.CORE
    assert kitchen.flexibility is RuleFlexibility.STRONGLY_PREFERRED
    assert kitchen.weight_multiplier_basis_points == 10_000
    assert profile.architecture_weight_basis_points == 5000
    assert profile.vastu_weight_basis_points == 5000


class MissingStaircaseProvider:
    name = "missing-staircase-test"

    def reason(
        self,
        request: VastuReasoningInput,
    ) -> VastuReasoningProfile:
        rules = tuple(
            VastuRuleReasoning(
                rule_id=rule.rule_id,
                applicability=RuleApplicability.APPLICABLE,
                importance=rule.default_importance,
                flexibility=rule.default_flexibility,
                weight_multiplier_basis_points=10_000,
                rationale="Test provider output.",
            )
            for rule in request.catalog.rules
            if rule.rule_id != "SOFT_STAIRCASE_ZONE"
        )

        return VastuReasoningProfile(
            project_id=request.confirmed.project_id,
            draft_id=request.confirmed.draft_id,
            provider=self.name,
            model=None,
            influence_mode=VastuInfluenceMode.BALANCED,
            architecture_weight_basis_points=5000,
            vastu_weight_basis_points=5000,
            rules=rules,
        ).with_content_hash()


def test_missing_irrelevant_rule_is_restored_deterministically(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "AI_VASTU_VASTU_INFLUENCE_MODE",
        raising=False,
    )

    profile = VastuReasoningService(MissingStaircaseProvider()).reason(
        confirmed=confirmed(),
        original_prompt="Ground-floor 2BHK without staircase.",
    )

    staircase = next(item for item in profile.rules if item.rule_id == "SOFT_STAIRCASE_ZONE")

    assert staircase.applicability is RuleApplicability.NOT_APPLICABLE
    assert staircase.weight_multiplier_basis_points == 10_000
    assert "deterministically restored" in staircase.rationale
