from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from ai_vastu.vastu_reasoning import (
    RuleApplicability,
    VastuInfluenceMode,
    VastuReasoningProfile,
    VastuRuleReasoning,
    assess_plan,
    blend_plan_scores,
    load_soft_vastu_catalog,
)


def point(x: int, y: int):
    return SimpleNamespace(x_mm=x, y_mm=y)


def rect(x1: int, y1: int, x2: int, y2: int):
    return SimpleNamespace(outer=(point(x1, y1), point(x2, y1), point(x2, y2), point(x1, y2)))


def room(room_type: str, x1: int, y1: int, x2: int, y2: int, suffix: int):
    return SimpleNamespace(
        id=UUID(f"50000000-0000-0000-0000-{suffix:012d}"),
        room_type=SimpleNamespace(value=room_type),
        polygon=rect(x1, y1, x2, y2),
    )


def test_directional_rules_score_deterministically() -> None:
    catalog = load_soft_vastu_catalog()
    profile = VastuReasoningProfile(
        project_id=UUID("30000000-0000-0000-0000-000000000026"),
        draft_id=UUID("10000000-0000-0000-0000-000000000026"),
        provider="fixture",
        model=None,
        influence_mode=VastuInfluenceMode.BALANCED,
        architecture_weight_basis_points=5000,
        vastu_weight_basis_points=5000,
        rules=tuple(
            VastuRuleReasoning(
                rule_id=rule.rule_id,
                applicability=RuleApplicability.APPLICABLE,
                importance=rule.default_importance,
                flexibility=rule.default_flexibility,
                weight_multiplier_basis_points=10_000,
                rationale="Catalog default.",
            )
            for rule in catalog.rules
        ),
    ).with_content_hash()

    # Plot centre is (5000, 5000). Kitchen centroid -> SE, puja -> NE.
    document = SimpleNamespace(
        project_id=profile.project_id,
        plot=SimpleNamespace(boundary=rect(0, 0, 10_000, 10_000)),
        orientation=SimpleNamespace(north_rotation_udeg=0),
        floors=(
            SimpleNamespace(
                rooms=(
                    room("kitchen", 7000, 1000, 9000, 3000, 1),
                    room("puja", 7000, 7000, 9000, 9000, 2),
                    room("living", 500, 7000, 3000, 9500, 3),
                )
            ),
        ),
        scoring=SimpleNamespace(overall_basis_points=8000),
    )

    assessment = assess_plan(document, profile, catalog)
    by_id = {item.rule_id: item for item in assessment.rules}
    assert by_id["SOFT_KITCHEN_ZONE"].status == "PREFERRED"
    assert by_id["SOFT_PUJA_ZONE"].status == "PREFERRED"
    assert assessment.overall_basis_points is not None

    blend = blend_plan_scores(document, profile, assessment)
    assert blend.architecture_weight_basis_points == 5000
    assert blend.vastu_weight_basis_points == 5000
    assert blend.ranking_ready is False
