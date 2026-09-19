from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass

from ai_vastu.generation.errors import CirculationGenerationError, GenerationInputError
from ai_vastu.generation.models import ArchitecturalGenerationResult, GenerationDisposition
from ai_vastu.requirements.finalization import (
    CanonicalGeneration,
    Phase24FinalizationError,
    build_canonical_plan_document,
)
from ai_vastu.requirements.generation_adapter import CompiledGeneration, run_compiled_generation
from ai_vastu.requirements.models import ConfirmedRequirements
from ai_vastu.solver import RoomPlacement
from ai_vastu.vastu_reasoning import (
    PlanningBlend,
    VastuReasoningProfile,
    WeightedVastuAssessment,
    assess_plan,
    load_soft_vastu_catalog,
)

from .models import (
    CandidateExclusion,
    CandidateExplanation,
    CandidatePlanningMode,
    CandidateResult,
    CandidateRunResult,
    CandidateStrategy,
)
from .strategies import default_candidate_strategies, search_variant_for_strategy

_BASIS_POINTS = 10_000


class MultiCandidateGenerationError(RuntimeError):
    pass


def _generation_failure_detail(
    generation: ArchitecturalGenerationResult,
) -> str:
    """Explain why a deterministic generation was not accepted."""

    planner = generation.planner_result

    parts = [
        f"disposition={generation.disposition.value}",
        f"planner_status={planner.status.value}",
    ]

    if planner.objective_penalty is not None:
        parts.append(f"objective_penalty={planner.objective_penalty}")

    if planner.notices:
        notice_text = " | ".join(
            (f"{item.severity.value}:{item.code}:{item.message}") for item in planner.notices
        )
        parts.append(f"planner_notices=[{notice_text}]")

    validation = generation.validation_result

    if validation is not None:
        report = validation.report

        parts.append(f"validation_valid={report.valid}")

        if report.errors:
            error_text = " | ".join(
                (
                    f"{item.severity.value}:"
                    f"{item.check_id}:"
                    f"{item.message_code}:"
                    "entities=" + (",".join(str(entity) for entity in item.entity_refs) or "none")
                )
                for item in report.errors
            )

            parts.append(f"validation_errors=[{error_text}]")

        if report.warnings:
            warning_text = " | ".join(
                (f"{item.severity.value}:{item.check_id}:{item.message_code}")
                for item in report.warnings
            )

            parts.append(f"validation_warnings=[{warning_text}]")

    detail = "; ".join(parts)

    # CandidateExclusion.message is intentionally bounded to 1000 chars.
    # Preserve the leading solver/validation evidence and truncate only
    # verbose diagnostic tail data.
    max_length = 980

    if len(detail) <= max_length:
        return detail

    return detail[: max_length - len(" ...[truncated]")] + " ...[truncated]"


@dataclass(frozen=True, slots=True)
class CandidateArtifact:
    strategy: CandidateStrategy
    generation: ArchitecturalGenerationResult
    canonical: CanonicalGeneration
    vastu_assessment: WeightedVastuAssessment | None
    planning_blend: PlanningBlend
    placement_signature: str


@dataclass(frozen=True, slots=True)
class MultiCandidateGenerationOutcome:
    run: CandidateRunResult
    selected_artifacts: tuple[CandidateArtifact, ...]

    @property
    def selected(self) -> CandidateArtifact:
        return self.selected_artifacts[0]


def _planning_mode(
    confirmed: ConfirmedRequirements,
    profile: VastuReasoningProfile | None,
) -> CandidatePlanningMode:
    if profile is not None:
        return CandidatePlanningMode(profile.influence_mode.value)
    if confirmed.vastu_mode.value == "space_efficient":
        return CandidatePlanningMode.PRACTICAL
    if confirmed.vastu_mode.value == "strict":
        return CandidatePlanningMode.VASTU_FORWARD
    return CandidatePlanningMode.BALANCED


def compute_vastu_evaluation_coverage(
    assessment: WeightedVastuAssessment,
) -> int | None:
    evaluated = sum(
        item.effective_weight for item in assessment.rules if item.score_basis_points is not None
    )
    unevaluated = sum(
        item.effective_weight for item in assessment.rules if item.status == "NOT_EVALUATED"
    )
    denominator = evaluated + unevaluated
    if denominator <= 0:
        return None
    return (evaluated * _BASIS_POINTS + denominator // 2) // denominator


def _blend(
    architecture_score: int,
    profile: VastuReasoningProfile | None,
    assessment: WeightedVastuAssessment | None,
) -> PlanningBlend:
    vastu_score = None if assessment is None else assessment.overall_basis_points
    if profile is None or vastu_score is None:
        return PlanningBlend(
            architecture_score_basis_points=architecture_score,
            vastu_score_basis_points=vastu_score,
            architecture_weight_basis_points=_BASIS_POINTS,
            vastu_weight_basis_points=0,
            combined_basis_points=architecture_score,
            ranking_ready=False,
            note=(
                "Candidate ranking is architecture-only because a geometry-supported "
                "soft-Vastu score is unavailable."
            ),
        )

    combined = (
        architecture_score * profile.architecture_weight_basis_points
        + vastu_score * profile.vastu_weight_basis_points
        + _BASIS_POINTS // 2
    ) // _BASIS_POINTS
    return PlanningBlend(
        architecture_score_basis_points=architecture_score,
        vastu_score_basis_points=vastu_score,
        architecture_weight_basis_points=profile.architecture_weight_basis_points,
        vastu_weight_basis_points=profile.vastu_weight_basis_points,
        combined_basis_points=combined,
        ranking_ready=True,
        note=(
            "Phase 26C ranks only hard-valid candidates using measurable architecture "
            "evidence and the geometry-supported soft-Vastu assessment."
        ),
    )


def _placement_signature(placements: Iterable[RoomPlacement]) -> str:
    payload = [
        {
            "room_instance_id": str(item.room_instance_id),
            "x_mm": item.x_mm,
            "y_mm": item.y_mm,
            "width_mm": item.width_mm,
            "depth_mm": item.depth_mm,
        }
        for item in sorted(placements, key=lambda value: str(value.room_instance_id))
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _changed_room_count(
    first: CandidateArtifact,
    second: CandidateArtifact,
    threshold_mm: int,
) -> int:
    left = {item.room_instance_id: item for item in first.generation.planner_result.placements}
    right = {item.room_instance_id: item for item in second.generation.planner_result.placements}
    if set(left) != set(right):
        raise MultiCandidateGenerationError(
            "Candidate pool contains different room-instance identity sets."
        )

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


def _has_unmeasured_room_priorities(result: ArchitecturalGenerationResult) -> bool:
    return any(
        notice.code == "SOFT_OBJECTIVE_NOT_YET_OPTIMIZED"
        and "Privacy/daylight/ventilation" in notice.message
        for notice in result.planner_result.notices
    )


def _occupied_area_basis_points(artifact: CandidateArtifact) -> int:
    points = artifact.generation.problem.buildable_area.polygon.outer
    xs = [point.x_mm for point in points]
    ys = [point.y_mm for point in points]
    buildable_area_mm2 = (max(xs) - min(xs)) * (max(ys) - min(ys))
    if buildable_area_mm2 <= 0:
        return 0
    occupied_area_mm2 = sum(item.area_mm2 for item in artifact.generation.planner_result.placements)
    return min(
        _BASIS_POINTS,
        (occupied_area_mm2 * _BASIS_POINTS + buildable_area_mm2 // 2) // buildable_area_mm2,
    )


def _explanation(
    artifact: CandidateArtifact,
    coverage: int | None,
) -> CandidateExplanation:
    blend = artifact.planning_blend
    occupied_bp = _occupied_area_basis_points(artifact)
    strengths = [
        (
            "Current measurable-objective score "
            f"{blend.architecture_score_basis_points / 100:.1f}/100. "
            "Full architectural quality scoring is not claimed in Phase 26C.4A."
        ),
        (f"Room-envelope occupancy {occupied_bp / 100:.1f}% of the current buildable rectangle."),
    ]
    compromises: list[str] = []

    if blend.vastu_score_basis_points is not None:
        strengths.append(f"Soft Vastu score {blend.vastu_score_basis_points / 100:.1f}/100.")
    if coverage is not None:
        strengths.append(f"Vastu evaluation coverage {coverage / 100:.1f}%.")
        if coverage < _BASIS_POINTS:
            compromises.append(
                "The Vastu score is partial because some applicable guidance is not "
                "yet supported by the geometry evaluator."
            )

    if _has_unmeasured_room_priorities(artifact.generation):
        compromises.append(
            "Privacy, daylight and ventilation priorities remain unscored where "
            "the current geometry does not provide measurable evidence."
        )

    variant = search_variant_for_strategy(artifact.strategy)
    return CandidateExplanation(
        strengths=tuple(strengths),
        compromises=tuple(compromises),
        selection_reason=(
            f"{artifact.strategy.label} used deterministic search variant {variant.value}. "
            "Its final rank is based on measured scores after hard validation, "
            "not on the strategy label."
        ),
    )


def _candidate_result(
    artifact: CandidateArtifact,
    *,
    rank: int,
) -> CandidateResult:
    document = artifact.canonical.document.with_content_hash()
    document_hash = document.content_hash
    assert document_hash is not None
    assessment = artifact.vastu_assessment
    coverage = None if assessment is None else compute_vastu_evaluation_coverage(assessment)
    blend = artifact.planning_blend

    return CandidateResult(
        candidate_id=artifact.canonical.candidate_id,
        rank=rank,
        strategy=artifact.strategy,
        valid_architecture=True,
        architecture_score_basis_points=blend.architecture_score_basis_points,
        vastu_score_basis_points=blend.vastu_score_basis_points,
        vastu_evaluation_coverage_basis_points=coverage,
        combined_score_basis_points=blend.combined_basis_points,
        architecture_weight_basis_points=blend.architecture_weight_basis_points,
        vastu_weight_basis_points=blend.vastu_weight_basis_points,
        plan_document_hash=document_hash,
        plan_document=document,
        soft_vastu_suggestions=() if assessment is None else assessment.suggestions,
        unevaluated_metrics=(
            ("privacy", "daylight", "ventilation")
            if _has_unmeasured_room_priorities(artifact.generation)
            else ()
        ),
        explanation=_explanation(artifact, coverage),
    )


def _strategy_compiled(
    compiled: CompiledGeneration,
    strategy: CandidateStrategy,
) -> CompiledGeneration:
    variant = search_variant_for_strategy(strategy)
    planner_config = compiled.request.planner_config.model_copy(update={"search_variant": variant})
    request = compiled.request.model_copy(update={"planner_config": planner_config})
    return CompiledGeneration(
        request=request,
        profile_version=compiled.profile_version,
        notices=(
            *compiled.notices,
            (
                f"Phase 26C strategy={strategy.strategy_id}; "
                f"search_variant={variant.value}; strategy label is not scoring evidence."
            ),
        ),
    )


def run_multi_candidate_generation(
    *,
    confirmed: ConfirmedRequirements,
    compiled: CompiledGeneration,
    vastu_profile: VastuReasoningProfile | None = None,
    strategies: tuple[CandidateStrategy, ...] | None = None,
    max_alternatives: int = 4,
    room_change_threshold_mm: int = 300,
    minimum_changed_rooms: int = 1,
) -> MultiCandidateGenerationOutcome:
    if max_alternatives < 1 or max_alternatives > 6:
        raise ValueError("max_alternatives must be between 1 and 6.")
    if room_change_threshold_mm < 1:
        raise ValueError("room_change_threshold_mm must be positive.")
    if minimum_changed_rooms < 1:
        raise ValueError("minimum_changed_rooms must be positive.")

    strategy_set = strategies or default_candidate_strategies()
    if not strategy_set:
        raise ValueError("At least one deterministic candidate strategy is required.")

    catalog = load_soft_vastu_catalog() if vastu_profile is not None else None
    accepted: list[CandidateArtifact] = []
    exclusions: list[CandidateExclusion] = []

    for strategy in sorted(strategy_set, key=lambda item: item.deterministic_ordinal):
        strategy_compiled = _strategy_compiled(compiled, strategy)
        try:
            generation = run_compiled_generation(strategy_compiled)
        except CirculationGenerationError as exc:
            exclusions.append(
                CandidateExclusion(
                    strategy_id=strategy.strategy_id,
                    reason_code="CIRCULATION_DISCONNECTED",
                    message=str(exc),
                )
            )
            continue
        except GenerationInputError as exc:
            exclusions.append(
                CandidateExclusion(
                    strategy_id=strategy.strategy_id,
                    reason_code="GENERATION_INPUT_ERROR",
                    message=str(exc),
                )
            )
            continue

        if generation.disposition is not GenerationDisposition.ACCEPTED:
            exclusions.append(
                CandidateExclusion(
                    strategy_id=strategy.strategy_id,
                    reason_code=generation.disposition.value,
                    message=_generation_failure_detail(generation),
                )
            )
            continue

        try:
            canonical = build_canonical_plan_document(
                confirmed=confirmed,
                compiled=strategy_compiled,
                result=generation,
            )
        except Phase24FinalizationError as exc:
            exclusions.append(
                CandidateExclusion(
                    strategy_id=strategy.strategy_id,
                    reason_code="CANONICALIZATION_REJECTED",
                    message=str(exc),
                )
            )
            continue

        assessment = None
        if vastu_profile is not None:
            assert catalog is not None
            assessment = assess_plan(canonical.document, vastu_profile, catalog)

        blend = _blend(canonical.scoring.overall_basis_points, vastu_profile, assessment)
        accepted.append(
            CandidateArtifact(
                strategy=strategy,
                generation=generation,
                canonical=canonical,
                vastu_assessment=assessment,
                planning_blend=blend,
                placement_signature=_placement_signature(generation.planner_result.placements),
            )
        )

    if not accepted:
        exclusion_text = "\n".join(
            (f"- {item.strategy_id}: {item.reason_code}: {item.message}") for item in exclusions
        )

        if not exclusion_text:
            exclusion_text = "- No deterministic exclusion detail was recorded."

        raise MultiCandidateGenerationError(
            "All deterministic Phase 26C candidate "
            "strategies were rejected.\n"
            "Deterministic diagnostics:\n"
            f"{exclusion_text}"
        )

    accepted.sort(
        key=lambda item: (
            -item.planning_blend.combined_basis_points,
            -item.planning_blend.architecture_score_basis_points,
            -(
                item.planning_blend.vastu_score_basis_points
                if item.planning_blend.vastu_score_basis_points is not None
                else -1
            ),
            item.strategy.deterministic_ordinal,
            str(item.canonical.candidate_id),
        )
    )

    unique: list[CandidateArtifact] = []
    seen_signatures: set[str] = set()
    for artifact in accepted:
        if artifact.placement_signature in seen_signatures:
            exclusions.append(
                CandidateExclusion(
                    strategy_id=artifact.strategy.strategy_id,
                    reason_code="DUPLICATE_PLACEMENT_SIGNATURE",
                    message=(
                        "Exact duplicate room placement was removed before diversity selection."
                    ),
                )
            )
            continue
        seen_signatures.add(artifact.placement_signature)
        unique.append(artifact)

    selected: list[CandidateArtifact] = []
    for artifact in unique:
        if len(selected) >= max_alternatives:
            exclusions.append(
                CandidateExclusion(
                    strategy_id=artifact.strategy.strategy_id,
                    reason_code="MAX_ALTERNATIVES_REACHED",
                    message="Candidate ranked below the requested alternative count.",
                )
            )
            continue

        changed_counts = [
            _changed_room_count(artifact, prior, room_change_threshold_mm) for prior in selected
        ]
        if changed_counts and min(changed_counts) < minimum_changed_rooms:
            exclusions.append(
                CandidateExclusion(
                    strategy_id=artifact.strategy.strategy_id,
                    reason_code="INSUFFICIENT_GEOMETRIC_DIVERSITY",
                    message=(
                        "Candidate did not change enough rooms relative to every "
                        "already-selected alternative."
                    ),
                )
            )
            continue
        selected.append(artifact)

    if not selected:
        raise MultiCandidateGenerationError(
            "Phase 26C diversity filtering removed every accepted candidate."
        )

    candidate_results = tuple(
        _candidate_result(artifact, rank=index) for index, artifact in enumerate(selected, start=1)
    )
    run = CandidateRunResult(
        project_id=confirmed.project_id,
        planning_mode=_planning_mode(confirmed, vastu_profile),
        candidates=candidate_results,
        exclusions=tuple(
            sorted(
                exclusions,
                key=lambda item: (item.reason_code, item.strategy_id, item.message),
            )
        ),
        attempted_candidate_count=len(strategy_set),
        rejected_candidate_count=len(strategy_set) - len(selected),
    ).with_content_hash()

    return MultiCandidateGenerationOutcome(
        run=run,
        selected_artifacts=tuple(selected),
    )
