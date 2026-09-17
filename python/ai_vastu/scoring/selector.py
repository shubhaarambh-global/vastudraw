from __future__ import annotations

from ai_vastu.solver.models import RoomPlacement

from .errors import ScoringInputError
from .evaluator import score_candidate
from .models import (
    CandidateScore,
    ExcludedAlternative,
    RankedAlternative,
    ScoringCandidate,
    ScoringRequest,
    ScoringRunResult,
)


def _placements(candidate: ScoringCandidate) -> dict[object, RoomPlacement]:
    return {item.room_instance_id: item for item in candidate.planner_result.placements}


def _changed_room_count(
    first: ScoringCandidate,
    second: ScoringCandidate,
    threshold_mm: int,
) -> int:
    left = _placements(first)
    right = _placements(second)
    if set(left) != set(right):
        raise ScoringInputError("Candidates in one pool must contain the same room instance IDs.")
    changed = 0
    for room_id in sorted(left, key=str):
        a = left[room_id]
        b = right[room_id]
        delta = max(
            abs(a.x_mm - b.x_mm),
            abs(a.y_mm - b.y_mm),
            abs(a.width_mm - b.width_mm),
            abs(a.depth_mm - b.depth_mm),
        )
        if delta >= threshold_mm:
            changed += 1
    return changed


def score_and_select_alternatives(request: ScoringRequest) -> ScoringRunResult:
    """Score valid candidates, deduplicate exact placements, then select diverse alternatives."""

    problem_hash = request.problem.content_hash or request.problem.compute_content_hash()
    candidate_by_id = {item.candidate_id: item for item in request.candidates}
    scored = [score_candidate(request, item) for item in request.candidates]
    scored.sort(
        key=lambda item: (
            -item.overall_basis_points,
            item.planner_objective_penalty,
            item.content_hash or "",
            str(item.candidate_id),
        )
    )

    excluded: list[ExcludedAlternative] = []
    seen_signatures: set[str] = set()
    unique: list[CandidateScore] = []
    for item in scored:
        if item.placement_signature in seen_signatures:
            excluded.append(
                ExcludedAlternative(
                    candidate_id=item.candidate_id,
                    reason_code="DUPLICATE_PLACEMENT_SIGNATURE",
                    message=(
                        "Exact duplicate placement geometry was removed before diversity selection."
                    ),
                )
            )
            continue
        seen_signatures.add(item.placement_signature)
        unique.append(item)

    selected: list[RankedAlternative] = []
    selected_candidates: list[ScoringCandidate] = []
    for item in unique:
        if len(selected) >= request.config.max_alternatives:
            excluded.append(
                ExcludedAlternative(
                    candidate_id=item.candidate_id,
                    reason_code="MAX_ALTERNATIVES_REACHED",
                    message="Candidate ranked below the configured alternative count limit.",
                )
            )
            continue

        candidate = candidate_by_id[item.candidate_id]
        changed_counts = [
            _changed_room_count(
                candidate,
                prior,
                request.config.room_change_threshold_mm,
            )
            for prior in selected_candidates
        ]
        minimum_changed = min(changed_counts) if changed_counts else None
        if minimum_changed is not None and minimum_changed < request.config.minimum_changed_rooms:
            excluded.append(
                ExcludedAlternative(
                    candidate_id=item.candidate_id,
                    reason_code="INSUFFICIENT_GEOMETRIC_DIVERSITY",
                    message=(
                        "Candidate does not change enough rooms relative to every already selected "
                        "alternative under the explicit diversity threshold."
                    ),
                )
            )
            continue

        selected_candidates.append(candidate)
        selected.append(
            RankedAlternative(
                rank=len(selected) + 1,
                candidate=item,
                minimum_changed_rooms_vs_selected=minimum_changed,
            )
        )

    if not selected:
        raise ScoringInputError("Diversity selection produced no alternatives.")

    notices = tuple(
        sorted(
            (notice for item in scored for notice in item.notices),
            key=lambda notice: (
                notice.code,
                "" if notice.candidate_id is None else str(notice.candidate_id),
                "" if notice.constraint_id is None else str(notice.constraint_id),
            ),
        )
    )
    return ScoringRunResult(
        source_problem_hash=problem_hash,
        selected=tuple(selected),
        excluded=tuple(
            sorted(excluded, key=lambda item: (item.reason_code, str(item.candidate_id)))
        ),
        notices=notices,
    ).with_content_hash()
