from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable

from ai_vastu.constraints.models import (
    AdjacencyAvoidanceObjective,
    AdjacencyPreferenceObjective,
    DimensionAxis,
    FloorPreferenceObjective,
    PreferredAreaObjective,
    PreferredDimensionObjective,
    RoomPrioritiesObjective,
)
from ai_vastu.plan_schema import ScoreComponent, ScoringSummary
from ai_vastu.solver.models import PlannerStatus, RoomPlacement

from .errors import ScoringInputError
from .models import (
    CandidateScore,
    ObjectiveScore,
    ScoringCandidate,
    ScoringNotice,
    ScoringNoticeSeverity,
    ScoringRequest,
)

_BASIS_POINTS = 10_000


def _ratio_score(actual: int, preferred: int) -> int:
    deviation = abs(actual - preferred)
    penalty = (deviation * _BASIS_POINTS + preferred // 2) // preferred
    return max(0, _BASIS_POINTS - penalty)


def _placement_map(candidate: ScoringCandidate) -> dict[object, RoomPlacement]:
    return {item.room_instance_id: item for item in candidate.planner_result.placements}


def _room_type_map(request: ScoringRequest) -> dict[object, object]:
    return {item.id: item.room_type for item in request.problem.room_instances}


def _axis_gap_and_shared(a: RoomPlacement, b: RoomPlacement) -> tuple[int, int]:
    ax2 = a.x_mm + a.width_mm
    ay2 = a.y_mm + a.depth_mm
    bx2 = b.x_mm + b.width_mm
    by2 = b.y_mm + b.depth_mm

    gap_x = max(0, a.x_mm - bx2, b.x_mm - ax2)
    gap_y = max(0, a.y_mm - by2, b.y_mm - ay2)
    gap = gap_x + gap_y

    overlap_x = max(0, min(ax2, bx2) - max(a.x_mm, b.x_mm))
    overlap_y = max(0, min(ay2, by2) - max(a.y_mm, b.y_mm))
    shared = 0
    if ax2 == b.x_mm or bx2 == a.x_mm:
        shared = overlap_y
    elif ay2 == b.y_mm or by2 == a.y_mm:
        shared = overlap_x
    return gap, shared


def _adjacency_score(
    source: RoomPlacement,
    targets: Iterable[RoomPlacement],
    objective: AdjacencyPreferenceObjective,
) -> tuple[int, tuple[str, ...]]:
    best_score = -1
    best_evidence: tuple[str, ...] = ()
    for target in targets:
        gap, shared = _axis_gap_and_shared(source, target)
        checks: list[int] = []
        if objective.max_gap_mm is not None:
            checks.append(_BASIS_POINTS if gap <= objective.max_gap_mm else 0)
        if objective.min_shared_length_mm is not None:
            checks.append(_BASIS_POINTS if shared >= objective.min_shared_length_mm else 0)
        if not checks:
            checks.append(_BASIS_POINTS if shared > 0 else 0)
        score = sum(checks) // len(checks)
        evidence = (f"gap_mm={gap}", f"shared_length_mm={shared}")
        if score > best_score or (score == best_score and evidence < best_evidence):
            best_score = score
            best_evidence = evidence
    if best_score < 0:
        return 0, ("target_count=0",)
    return best_score, best_evidence


def _placement_signature(placements: tuple[RoomPlacement, ...]) -> str:
    payload = [
        {
            "room_instance_id": str(item.room_instance_id),
            "floor_index": item.floor_index,
            "x_mm": item.x_mm,
            "y_mm": item.y_mm,
            "width_mm": item.width_mm,
            "depth_mm": item.depth_mm,
        }
        for item in sorted(placements, key=lambda value: str(value.room_instance_id))
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalized_components(scores: tuple[ObjectiveScore, ...]) -> tuple[ScoreComponent, ...]:
    grouped_weight: dict[str, int] = defaultdict(int)
    grouped_weighted_score: dict[str, int] = defaultdict(int)
    for item in scores:
        grouped_weight[item.kind] += item.weight
        grouped_weighted_score[item.kind] += item.score_basis_points * item.weight
    total_weight = sum(grouped_weight.values())
    if total_weight <= 0:
        raise ScoringInputError("At least one scoreable soft objective must have positive weight.")

    kinds = sorted(grouped_weight)
    remaining = _BASIS_POINTS
    components: list[ScoreComponent] = []
    for index, kind in enumerate(kinds):
        weight = grouped_weight[kind]
        if index == len(kinds) - 1:
            normalized_weight = remaining
        else:
            normalized_weight = (weight * _BASIS_POINTS) // total_weight
            remaining -= normalized_weight
        score = grouped_weighted_score[kind] // weight
        components.append(
            ScoreComponent(
                key=kind,
                score_basis_points=score,
                weight_basis_points=normalized_weight,
            )
        )
    return tuple(components)


def _validate_candidate_chain(request: ScoringRequest, candidate: ScoringCandidate) -> None:
    problem_hash = request.problem.content_hash or request.problem.compute_content_hash()
    planner = candidate.planner_result
    geometry = candidate.geometry_result
    validation = candidate.validation_result

    if planner.status not in (PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE):
        raise ScoringInputError(f"Candidate {candidate.candidate_id} is not solver-feasible.")
    if planner.content_hash is None:
        raise ScoringInputError(f"Candidate {candidate.candidate_id} planner result is unhashed.")
    if geometry.content_hash is None:
        raise ScoringInputError(f"Candidate {candidate.candidate_id} geometry result is unhashed.")
    if validation.content_hash is None:
        raise ScoringInputError(
            f"Candidate {candidate.candidate_id} validation result is unhashed."
        )
    if planner.metadata.problem_hash != problem_hash:
        raise ScoringInputError(f"Candidate {candidate.candidate_id} references another problem.")
    if geometry.source_problem_hash != problem_hash:
        raise ScoringInputError(
            f"Candidate {candidate.candidate_id} geometry problem hash mismatch."
        )
    if geometry.source_planner_hash != planner.content_hash:
        raise ScoringInputError(
            f"Candidate {candidate.candidate_id} geometry/planner hash mismatch."
        )
    if validation.source_problem_hash != problem_hash:
        raise ScoringInputError(
            f"Candidate {candidate.candidate_id} validation problem hash mismatch."
        )
    if validation.source_geometry_hash != geometry.content_hash:
        raise ScoringInputError(
            f"Candidate {candidate.candidate_id} validation/geometry hash mismatch."
        )
    if not validation.report.valid:
        raise ScoringInputError(f"Candidate {candidate.candidate_id} failed Phase 9 validation.")
    if request.config.reject_validation_warnings and validation.report.warnings:
        raise ScoringInputError(
            f"Candidate {candidate.candidate_id} has validation warnings and policy rejects them."
        )


def score_candidate(request: ScoringRequest, candidate: ScoringCandidate) -> CandidateScore:
    _validate_candidate_chain(request, candidate)
    placements = _placement_map(candidate)
    room_types = _room_type_map(request)
    scores: list[ObjectiveScore] = []
    notices: list[ScoringNotice] = []

    for objective in request.problem.soft_constraints:
        source = placements.get(objective.room_instance_id)
        if source is None:
            raise ScoringInputError(
                f"Candidate {candidate.candidate_id} is missing room {objective.room_instance_id}."
            )

        if isinstance(objective, PreferredDimensionObjective):
            actual = source.width_mm if objective.axis is DimensionAxis.WIDTH else source.depth_mm
            value = _ratio_score(actual, objective.preferred_mm)
            scores.append(
                ObjectiveScore(
                    constraint_id=objective.id,
                    kind=objective.kind.value,
                    score_basis_points=value,
                    weight=objective.weight,
                    evidence=(f"actual_mm={actual}", f"preferred_mm={objective.preferred_mm}"),
                )
            )
        elif isinstance(objective, PreferredAreaObjective):
            value = _ratio_score(source.area_mm2, objective.preferred_area_mm2)
            scores.append(
                ObjectiveScore(
                    constraint_id=objective.id,
                    kind=objective.kind.value,
                    score_basis_points=value,
                    weight=objective.weight,
                    evidence=(
                        f"actual_area_mm2={source.area_mm2}",
                        f"preferred_area_mm2={objective.preferred_area_mm2}",
                    ),
                )
            )
        elif isinstance(objective, FloorPreferenceObjective):
            value = (
                _BASIS_POINTS if source.floor_index in objective.preferred_floor_indices else 0
            )
            scores.append(
                ObjectiveScore(
                    constraint_id=objective.id,
                    kind=objective.kind.value,
                    score_basis_points=value,
                    weight=objective.weight,
                    evidence=(f"floor_index={source.floor_index}",),
                )
            )
        elif isinstance(objective, AdjacencyPreferenceObjective):
            targets = (
                placement
                for room_id, placement in placements.items()
                if room_id != objective.room_instance_id
                and room_types.get(room_id) is objective.target_room_type
            )
            value, evidence = _adjacency_score(source, targets, objective)
            scores.append(
                ObjectiveScore(
                    constraint_id=objective.id,
                    kind=objective.kind.value,
                    score_basis_points=value,
                    weight=objective.weight,
                    evidence=evidence,
                )
            )
        elif isinstance(objective, AdjacencyAvoidanceObjective):
            notices.append(
                ScoringNotice(
                    code="UNSCORABLE_ADJACENCY_AVOIDANCE_WITHOUT_WEIGHT",
                    severity=ScoringNoticeSeverity.WARNING,
                    message=(
                        "The compiled adjacency-avoidance objective has no numeric weight; "
                        "Phase 10 does not invent one."
                    ),
                    constraint_id=objective.id,
                    candidate_id=candidate.candidate_id,
                )
            )
        elif isinstance(objective, RoomPrioritiesObjective):
            notices.append(
                ScoringNotice(
                    code="ROOM_PRIORITY_REQUIRES_FUTURE_MEASURABLE_FACTS",
                    severity=ScoringNoticeSeverity.INFO,
                    message=(
                        "Privacy/daylight/ventilation priorities are retained but not scored "
                        "until measurable architectural facts exist."
                    ),
                    constraint_id=objective.id,
                    candidate_id=candidate.candidate_id,
                )
            )
        else:  # pragma: no cover - discriminated union guard
            raise ScoringInputError(f"Unsupported scoring objective: {objective.kind}.")

    weighted = [(item.score_basis_points, item.weight) for item in scores if item.weight > 0]
    total_weight = sum(weight for _, weight in weighted)
    if total_weight <= 0:
        raise ScoringInputError("No positive-weight, scoreable soft objectives are available.")
    weighted_total = sum(score * weight for score, weight in weighted)
    overall = (weighted_total + total_weight // 2) // total_weight
    score_tuple = tuple(sorted(scores, key=lambda item: str(item.constraint_id)))
    summary = ScoringSummary(
        mode="ARCHITECTURAL_SOFT_CONSTRAINTS_V1",
        overall_basis_points=overall,
        components=_normalized_components(tuple(item for item in score_tuple if item.weight > 0)),
    )

    if candidate.validation_result.report.warnings:
        notices.append(
            ScoringNotice(
                code="VALIDATION_WARNINGS_PRESENT_NO_SCORE_PENALTY",
                severity=ScoringNoticeSeverity.WARNING,
                message=(
                    "Phase 9 validation warnings are disclosed but do not alter score unless "
                    "the explicit rejection policy is enabled."
                ),
                candidate_id=candidate.candidate_id,
            )
        )

    planner_hash = candidate.planner_result.content_hash
    geometry_hash = candidate.geometry_result.content_hash
    validation_hash = candidate.validation_result.content_hash
    assert planner_hash is not None
    assert geometry_hash is not None
    assert validation_hash is not None
    penalty = candidate.planner_result.objective_penalty
    assert penalty is not None
    return CandidateScore(
        candidate_id=candidate.candidate_id,
        overall_basis_points=overall,
        scoring_summary=summary,
        planner_objective_penalty=penalty,
        objective_scores=score_tuple,
        notices=tuple(
            sorted(
                notices,
                key=lambda item: (
                    item.code,
                    "" if item.constraint_id is None else str(item.constraint_id),
                ),
            )
        ),
        placement_signature=_placement_signature(candidate.planner_result.placements),
        source_planner_hash=planner_hash,
        source_geometry_hash=geometry_hash,
        source_validation_hash=validation_hash,
    ).with_content_hash()
