from __future__ import annotations

from uuid import UUID

import pytest

from ai_vastu.plan_schema import ValidationReport, ValidationResult, ValidationSeverity
from ai_vastu.scoring import (
    ScoringConfig,
    ScoringInputError,
    ScoringRequest,
    score_and_select_alternatives,
    score_candidate,
)

from .helpers import candidate, problem


def config(*, max_alternatives: int = 3) -> ScoringConfig:
    return ScoringConfig(
        max_alternatives=max_alternatives,
        room_change_threshold_mm=100,
        minimum_changed_rooms=2,
        reject_validation_warnings=False,
    )


def test_score_is_deterministic_and_explicitly_architectural() -> None:
    item = candidate(UUID("a2000000-0000-0000-0000-000000000001"))
    request = ScoringRequest(problem=problem(), config=config(), candidates=(item,))
    first = score_candidate(request, item)
    second = score_candidate(request, item)
    assert first == second
    assert first.overall_basis_points == 10_000
    assert first.scoring_summary.mode == "ARCHITECTURAL_SOFT_CONSTRAINTS_V1"
    assert first.content_hash is not None


def test_swapped_layout_is_selected_as_diverse() -> None:
    first = candidate(UUID("a2000000-0000-0000-0000-000000000001"))
    second = candidate(UUID("a2000000-0000-0000-0000-000000000002"), swapped=True)
    request = ScoringRequest(problem=problem(), config=config(), candidates=(first, second))
    result = score_and_select_alternatives(request)
    assert len(result.selected) == 2
    assert result.selected[0].rank == 1
    assert result.selected[1].minimum_changed_rooms_vs_selected == 2
    assert result.content_hash is not None


def test_exact_duplicate_placement_is_excluded() -> None:
    first = candidate(UUID("a2000000-0000-0000-0000-000000000001"))
    duplicate = candidate(UUID("a2000000-0000-0000-0000-000000000003"))
    request = ScoringRequest(problem=problem(), config=config(), candidates=(first, duplicate))
    result = score_and_select_alternatives(request)
    assert len(result.selected) == 1
    assert any(item.reason_code == "DUPLICATE_PLACEMENT_SIGNATURE" for item in result.excluded)


def test_hash_chain_mismatch_fails_closed() -> None:
    item = candidate(UUID("a2000000-0000-0000-0000-000000000001"))
    broken_geometry = item.geometry_result.model_copy(
        update={"source_planner_hash": "0" * 64, "content_hash": None}
    ).with_content_hash()
    broken = item.model_copy(update={"geometry_result": broken_geometry})
    request = ScoringRequest(problem=problem(), config=config(), candidates=(broken,))
    with pytest.raises(ScoringInputError, match="geometry/planner hash mismatch"):
        score_candidate(request, broken)


def test_invalid_phase9_report_cannot_be_scored() -> None:
    item = candidate(UUID("a2000000-0000-0000-0000-000000000001"))
    validation = item.validation_result
    failure = ValidationResult(
        check_id="phase10.fixture.invalid",
        severity=ValidationSeverity.ERROR,
        message_code="PHASE10_FIXTURE_INVALID",
        validator_version="1.0.0",
    )
    invalid_report = ValidationReport(valid=False, errors=(failure,))
    invalid_validation = validation.model_copy(
        update={"report": invalid_report, "content_hash": None}
    ).with_content_hash()
    broken = item.model_copy(update={"validation_result": invalid_validation})
    request = ScoringRequest(problem=problem(), config=config(), candidates=(broken,))
    with pytest.raises(ScoringInputError, match="failed Phase 9 validation"):
        score_candidate(request, broken)
