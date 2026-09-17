from __future__ import annotations

from ai_vastu.plan_schema import PlanDocument

from .models import PlanningBlend, VastuReasoningProfile, WeightedVastuAssessment


def blend_plan_scores(
    document: PlanDocument,
    profile: VastuReasoningProfile,
    assessment: WeightedVastuAssessment,
) -> PlanningBlend:
    architecture_score = document.scoring.overall_basis_points
    vastu_score = assessment.overall_basis_points

    if vastu_score is None:
        return PlanningBlend(
            architecture_score_basis_points=architecture_score,
            vastu_score_basis_points=None,
            architecture_weight_basis_points=10_000,
            vastu_weight_basis_points=0,
            combined_basis_points=architecture_score,
            ranking_ready=False,
            note=(
                "No geometry-supported soft Vastu rules were scoreable. "
                "Architecture score is shown alone."
            ),
        )

    combined = (
        architecture_score * profile.architecture_weight_basis_points
        + vastu_score * profile.vastu_weight_basis_points
    ) // 10_000
    return PlanningBlend(
        architecture_score_basis_points=architecture_score,
        vastu_score_basis_points=vastu_score,
        architecture_weight_basis_points=profile.architecture_weight_basis_points,
        vastu_weight_basis_points=profile.vastu_weight_basis_points,
        combined_basis_points=combined,
        ranking_ready=False,
        note=(
            "Phase 26B computes the deterministic architecture/Vastu blend for "
            "transparency. Multi-candidate selection using this blend begins in Phase 26C."
        ),
    )
