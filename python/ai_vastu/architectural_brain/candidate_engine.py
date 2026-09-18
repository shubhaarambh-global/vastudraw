from __future__ import annotations

from ai_vastu.multi_candidate import (
    CandidateArtifact,
    CandidateExclusion,
    CandidateResult,
    CandidateRunResult,
    MultiCandidateGenerationError,
    MultiCandidateGenerationOutcome,
    default_candidate_strategies,
    run_multi_candidate_generation,
)
from ai_vastu.requirements.generation_adapter import CompiledGeneration
from ai_vastu.requirements.models import ConfirmedRequirements
from ai_vastu.vastu_reasoning import VastuReasoningProfile

from .bridge import apply_architectural_concept
from .critic import critique_plan
from .scoring import score_plan_document
from .service import ArchitecturalBrainService


def _value(value: object | None) -> str | None:
    if value is None:
        return None
    raw = getattr(value, "value", value)
    return str(raw)


def run_architectural_brain_candidates(
    *,
    confirmed: ConfirmedRequirements,
    compiled: CompiledGeneration,
    original_prompt: str,
    vastu_profile: VastuReasoningProfile | None,
    max_alternatives: int = 4,
) -> MultiCandidateGenerationOutcome:
    room_types = tuple(
        requirement.room_type.value
        for requirement in compiled.request.room_requirements
        for _ in range(requirement.quantity)
    )
    toilet_count = sum(
        requirement.quantity
        for requirement in compiled.request.room_requirements
        if "toilet" in requirement.room_type.value or "bath" in requirement.room_type.value
    )
    try:
        brain = ArchitecturalBrainService.from_environment().propose(
            project_id=confirmed.project_id,
            original_prompt=original_prompt,
            width_mm=confirmed.plot_width_mm,
            depth_mm=confirmed.plot_depth_mm,
            bedroom_count=confirmed.bedroom_count,
            toilet_count=toilet_count,
            parking_count=confirmed.parking_count,
            room_types=room_types,
            road_side=_value(confirmed.road_side),
            entrance_side=_value(confirmed.entrance_facing),
            concept_count=6,
        )
    except RuntimeError as exc:
        raise MultiCandidateGenerationError(
            f"Architectural Brain provider failed: {exc}"
        ) from exc

    strategies = default_candidate_strategies()
    accepted: list[tuple[CandidateResult, CandidateArtifact]] = []
    exclusions: list[CandidateExclusion] = []
    planning_mode = None

    for concept, strategy in zip(brain.concepts, strategies, strict=False):
        concept_compiled = apply_architectural_concept(compiled, concept)
        try:
            run = run_multi_candidate_generation(
                confirmed=confirmed,
                compiled=concept_compiled,
                vastu_profile=vastu_profile,
                strategies=(strategy,),
                max_alternatives=1,
            )
        except MultiCandidateGenerationError as exc:
            exclusions.append(
                CandidateExclusion(
                    strategy_id=strategy.strategy_id,
                    reason_code="BRAIN_CONCEPT_REJECTED",
                    message=str(exc),
                )
            )
            continue

        if planning_mode is None:
            planning_mode = run.run.planning_mode
        candidate = run.run.candidates[0]
        artifact = run.selected_artifacts[0]
        document = candidate.plan_document
        if document is None:
            continue

        critique = critique_plan(document)
        if not critique.accepted:
            exclusions.append(
                CandidateExclusion(
                    strategy_id=strategy.strategy_id,
                    reason_code="ARCHITECTURAL_CRITIC_REJECTED",
                    message="; ".join(item.message for item in critique.findings),
                )
            )
            continue

        quality = score_plan_document(document)
        architecture_score = quality.score_basis_points or candidate.architecture_score_basis_points
        vastu_score = candidate.vastu_score_basis_points
        combined = architecture_score
        if vastu_score is not None:
            combined = round(
                (
                    architecture_score * candidate.architecture_weight_basis_points
                    + vastu_score * candidate.vastu_weight_basis_points
                )
                / 10_000
            )
        explanation = candidate.explanation.model_copy(
            update={
                "strengths": (
                    *candidate.explanation.strengths,
                    (
                        "Architectural-quality evidence coverage "
                        f"{quality.evaluation_coverage_basis_points / 100:.1f}%."
                    ),
                    f"Precedent-backed concept: {concept.title}.",
                ),
                "compromises": (
                    *candidate.explanation.compromises,
                    *tuple(
                        item.message
                        for item in critique.findings
                        if item.severity.value == "WARNING"
                    ),
                ),
            }
        )
        accepted.append(
            (
                candidate.model_copy(
                    update={
                        "architecture_score_basis_points": architecture_score,
                        "combined_score_basis_points": combined,
                        "explanation": explanation,
                    }
                ),
                artifact,
            )
        )
        exclusions.extend(run.run.exclusions)

    if not accepted or planning_mode is None:
        raise MultiCandidateGenerationError(
            "Architectural Brain produced no hard-valid, critic-accepted candidate."
        )

    accepted.sort(
        key=lambda item: (
            -item[0].combined_score_basis_points,
            -item[0].architecture_score_basis_points,
            str(item[0].candidate_id),
        )
    )
    selected = accepted[:max_alternatives]
    candidates = tuple(
        item[0].model_copy(update={"rank": index}) for index, item in enumerate(selected, start=1)
    )
    result = CandidateRunResult(
        project_id=confirmed.project_id,
        planning_mode=planning_mode,
        candidates=candidates,
        exclusions=tuple(exclusions),
        attempted_candidate_count=len(brain.concepts),
        rejected_candidate_count=max(0, len(brain.concepts) - len(candidates)),
    ).with_content_hash()
    return MultiCandidateGenerationOutcome(
        run=result,
        selected_artifacts=tuple(item[1] for item in selected),
    )
