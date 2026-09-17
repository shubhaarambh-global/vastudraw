from uuid import UUID

import pytest

from ai_vastu.multi_candidate import (
    CandidateExplanation,
    CandidatePlanningMode,
    CandidateResult,
    CandidateRunResult,
    CandidateStrategy,
    CandidateStrategyKind,
)
from ai_vastu.multi_candidate.strategies import default_candidate_strategies


def test_phase26c_strategy_catalog_is_stable_and_structural_free() -> None:
    strategies = default_candidate_strategies()
    assert [item.deterministic_ordinal for item in strategies] == list(range(6))
    assert {item.kind for item in strategies} == {
        CandidateStrategyKind.COMPACT,
        CandidateStrategyKind.PRIVACY,
        CandidateStrategyKind.DAYLIGHT,
        CandidateStrategyKind.CIRCULATION,
        CandidateStrategyKind.VASTU_AWARE,
        CandidateStrategyKind.ALTERNATE_TOPOLOGY,
    }


def test_ranked_candidate_requires_valid_architecture() -> None:
    strategy = CandidateStrategy(
        strategy_id="compact",
        kind=CandidateStrategyKind.COMPACT,
        label="Compact",
        description="Compact option.",
        deterministic_ordinal=0,
    )
    with pytest.raises(ValueError):
        CandidateResult(
            candidate_id=UUID("11111111-1111-1111-1111-111111111111"),
            rank=1,
            strategy=strategy,
            valid_architecture=False,
            architecture_score_basis_points=9000,
            vastu_score_basis_points=9000,
            vastu_evaluation_coverage_basis_points=8000,
            combined_score_basis_points=9000,
            architecture_weight_basis_points=5000,
            vastu_weight_basis_points=5000,
            explanation=CandidateExplanation(
                selection_reason="Invalid candidates must not rank.",
            ),
        )


def test_candidate_run_hash_is_deterministic_and_structural_is_v2() -> None:
    strategy = default_candidate_strategies()[0]
    candidate = CandidateResult(
        candidate_id=UUID("22222222-2222-2222-2222-222222222222"),
        rank=1,
        strategy=strategy,
        valid_architecture=True,
        architecture_score_basis_points=9000,
        vastu_score_basis_points=7000,
        vastu_evaluation_coverage_basis_points=8000,
        combined_score_basis_points=8000,
        architecture_weight_basis_points=5000,
        vastu_weight_basis_points=5000,
        explanation=CandidateExplanation(
            strengths=("Valid architecture",),
            compromises=("Soft Vastu trade-off",),
            selection_reason="Highest deterministic blended score.",
        ),
    )
    run = CandidateRunResult(
        project_id=UUID("33333333-3333-3333-3333-333333333333"),
        planning_mode=CandidatePlanningMode.BALANCED,
        candidates=(candidate,),
    ).with_content_hash()

    assert run.structural_design_included is False
    assert run.content_hash == run.compute_content_hash()
