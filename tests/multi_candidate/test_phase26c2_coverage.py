from typing import Literal
from uuid import UUID

from ai_vastu.multi_candidate import compute_vastu_evaluation_coverage
from ai_vastu.vastu_reasoning.models import (
    RuleApplicability,
    RuleFlexibility,
    RuleImportance,
    VastuRuleAssessment,
    WeightedVastuAssessment,
)


def _rule(
    rule_id: str,
    *,
    score: int | None,
    weight: int,
    status: Literal[
        "PREFERRED",
        "SECONDARY",
        "NEUTRAL",
        "AVOIDED",
        "NOT_APPLICABLE",
        "NOT_EVALUATED",
    ],
) -> VastuRuleAssessment:
    return VastuRuleAssessment(
        rule_id=rule_id,
        title=rule_id,
        applicability=RuleApplicability.APPLICABLE,
        importance=RuleImportance.MODERATE,
        flexibility=RuleFlexibility.PREFERRED,
        score_basis_points=score,
        effective_weight=weight,
        status=status,
        evidence=(),
        suggestion="Traditional guidance only.",
    )


def test_coverage_excludes_not_applicable_and_counts_not_evaluated() -> None:
    assessment = WeightedVastuAssessment(
        project_id=UUID("33333333-3333-3333-3333-333333333333"),
        profile_hash="profile",
        overall_basis_points=5000,
        rules=(
            _rule("evaluated-a", score=5000, weight=2750, status="NEUTRAL"),
            _rule("evaluated-b", score=5000, weight=2500, status="NEUTRAL"),
            _rule("evaluated-c", score=5000, weight=2750, status="NEUTRAL"),
            _rule("unsupported-a", score=None, weight=3000, status="NOT_EVALUATED"),
            _rule("unsupported-b", score=None, weight=3250, status="NOT_EVALUATED"),
            _rule("not-applicable", score=None, weight=0, status="NOT_APPLICABLE"),
        ),
    )

    assert compute_vastu_evaluation_coverage(assessment) == 5614
