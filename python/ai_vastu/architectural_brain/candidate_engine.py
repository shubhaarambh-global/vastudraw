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
from ai_vastu.plan_schema import (
    AdjacencyPreference,
    RoomType,
)
from ai_vastu.precedents import PrecedentMatch
from ai_vastu.requirements.generation_adapter import CompiledGeneration
from ai_vastu.requirements.models import ConfirmedRequirements
from ai_vastu.vastu_reasoning import VastuReasoningProfile

from .bridge import apply_architectural_concept
from .candidate_dedup import (
    SPATIAL_DEDUP_QUANTUM_MM,
    duplicate_reason_code,
    semantic_topology_signature,
    solved_spatial_signature,
    spatially_equivalent,
)
from .critic import critique_plan
from .errors import ArchitecturalBrainConfigurationError, ArchitecturalBrainProviderError
from .precedent_topology import bind_precedent_topologies
from .scoring import score_plan_document
from .service import ArchitecturalBrainService


def _unique_adjacency_preferences(
    preferences: tuple[AdjacencyPreference, ...],
) -> tuple[AdjacencyPreference, ...]:
    """Preserve the earliest preference for each target room type.

    Requirement layers are applied in authority/order before the candidate
    concept. A later Architectural Brain concept must not duplicate or
    silently replace an already-established relationship.
    """

    seen: set[RoomType] = set()
    unique: list[AdjacencyPreference] = []

    for preference in preferences:
        target = preference.target_room_type

        if target in seen:
            continue

        seen.add(target)
        unique.append(preference)

    return tuple(unique)


def _normalize_concept_adjacency(
    compiled: CompiledGeneration,
) -> CompiledGeneration:
    """Remove duplicate late concept preferences without weakening conflicts."""

    updated = []
    changed = False

    for requirement in compiled.request.room_requirements:
        preferences = _unique_adjacency_preferences(requirement.adjacency_preferences)

        if preferences != requirement.adjacency_preferences:
            changed = True

            requirement = requirement.model_copy(
                update={
                    "adjacency_preferences": preferences,
                }
            )

        updated.append(requirement)

    if not changed:
        return compiled

    updated_by_id = {item.id: item for item in updated}
    request = compiled.request.model_copy(
        update={
            "room_requirements": tuple(updated),
            "floor_requirements": tuple(
                tuple(updated_by_id.get(item.id, item) for item in floor)
                for floor in compiled.request.floor_requirements
            ),
        }
    )

    return CompiledGeneration(
        request=request,
        profile_version=compiled.profile_version,
        notices=(
            *compiled.notices,
            (
                "Duplicate Architectural Brain adjacency "
                "preferences were collapsed by target room "
                "type; the earlier layered preference was retained."
            ),
        ),
    )


def _bounded_exclusion_message(
    message: str,
    *,
    max_length: int = 980,
) -> str:
    """Keep CandidateExclusion.message within its schema bound."""

    if len(message) <= max_length:
        return message

    suffix = " ...[truncated]"

    return message[: max_length - len(suffix)] + suffix


def _value(value: object | None) -> str | None:
    if value is None:
        return None
    raw = getattr(value, "value", value)
    return str(raw)


def _planner_diagnostic_text(artifact: CandidateArtifact) -> str:
    planner = artifact.generation.planner_result

    grouped: dict[str, int] = {}
    for contribution in planner.objective_contributions:
        grouped[contribution.kind] = (
            grouped.get(contribution.kind, 0) + contribution.weighted_penalty
        )

    tracked = {
        "RESIDENTIAL_OCCUPIED_AREA_TARGET",
        "RESIDENTIAL_ROOM_AREA_BALANCE",
        "RESIDENTIAL_COMPACTNESS_VOID",
        "RESIDENTIAL_TOPOLOGY_ADJACENCY",
    }
    other = sum(value for kind, value in grouped.items() if kind not in tracked)

    objective_penalty = (
        "none" if planner.objective_penalty is None else str(planner.objective_penalty)
    )

    return (
        f"planner_status={planner.status.value}; "
        f"objective_penalty={objective_penalty}; "
        "occupied_area_penalty="
        f"{grouped.get('RESIDENTIAL_OCCUPIED_AREA_TARGET', 0)}; "
        "room_balance_penalty="
        f"{grouped.get('RESIDENTIAL_ROOM_AREA_BALANCE', 0)}; "
        "compactness_penalty="
        f"{grouped.get('RESIDENTIAL_COMPACTNESS_VOID', 0)}; "
        "topology_penalty="
        f"{grouped.get('RESIDENTIAL_TOPOLOGY_ADJACENCY', 0)}; "
        f"other_penalty={other}"
    )


def run_architectural_brain_candidates(
    *,
    confirmed: ConfirmedRequirements,
    compiled: CompiledGeneration,
    original_prompt: str,
    vastu_profile: VastuReasoningProfile | None,
    precedent_matches: tuple[PrecedentMatch, ...] = (),
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
    except (ArchitecturalBrainConfigurationError, ArchitecturalBrainProviderError):
        raise
    except RuntimeError as exc:
        raise MultiCandidateGenerationError(f"Architectural Brain provider failed: {exc}") from exc

    concepts = bind_precedent_topologies(
        brain.concepts,
        precedent_matches,
    )

    strategies = default_candidate_strategies()
    accepted: list[
        tuple[
            CandidateResult,
            CandidateArtifact,
            str,
            str,
        ]
    ] = []
    exclusions: list[CandidateExclusion] = []
    diagnostics: list[str] = []
    planning_mode = None

    for concept, strategy in zip(concepts, strategies, strict=False):
        concept_compiled = _normalize_concept_adjacency(
            apply_architectural_concept(
                compiled,
                concept,
            )
        )
        try:
            run = run_multi_candidate_generation(
                confirmed=confirmed,
                compiled=concept_compiled,
                vastu_profile=vastu_profile,
                strategies=(strategy,),
                max_alternatives=1,
            )
        except MultiCandidateGenerationError as exc:
            message = str(exc)

            exclusions.append(
                CandidateExclusion(
                    strategy_id=strategy.strategy_id,
                    reason_code="BRAIN_CONCEPT_REJECTED",
                    message=_bounded_exclusion_message(message),
                )
            )

            diagnostics.append(f"{strategy.strategy_id}: GENERATION_REJECTED: {message}")
            continue

        if planning_mode is None:
            planning_mode = run.run.planning_mode
        candidate = run.run.candidates[0]
        artifact = run.selected_artifacts[0]
        document = candidate.plan_document
        if document is None:
            diagnostics.append(f"{strategy.strategy_id}: NO_PLAN_DOCUMENT")
            continue

        quality = score_plan_document(document)

        site_metric = next(
            (item for item in quality.metrics if item.key == "site_allocation"),
            None,
        )

        site_score = None if site_metric is None else site_metric.score_basis_points

        critique = critique_plan(document)
        if not critique.accepted:
            finding_text = "; ".join(
                (f"{item.severity.value} {item.code}: {item.message}") for item in critique.findings
            )

            exclusions.append(
                CandidateExclusion(
                    strategy_id=strategy.strategy_id,
                    reason_code="ARCHITECTURAL_CRITIC_REJECTED",
                    message=_bounded_exclusion_message(finding_text),
                )
            )

            site_text = "unknown" if site_score is None else f"{site_score / 100:.1f}%"
            planner_text = _planner_diagnostic_text(artifact)

            diagnostics.append(
                f"{strategy.strategy_id}: "
                "CRITIC_REJECTED; "
                f"site_allocation={site_text}; "
                "evidence_coverage="
                f"{quality.evaluation_coverage_basis_points / 100:.1f}%; "
                f"{planner_text}; "
                f"{finding_text}"
            )
            continue

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
        diagnostics.append(
            f"{strategy.strategy_id}: "
            "ACCEPTED; "
            "site_allocation="
            + ("unknown" if site_score is None else f"{site_score / 100:.1f}%")
            + "; evidence_coverage="
            + f"{quality.evaluation_coverage_basis_points / 100:.1f}%"
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
                semantic_topology_signature(concept.topology),
                solved_spatial_signature(document),
            )
        )
        exclusions.extend(run.run.exclusions)

    if not accepted or planning_mode is None:
        diagnostic_text = "\n".join(f"- {item}" for item in diagnostics)

        if not diagnostic_text:
            diagnostic_text = "- No candidate-specific diagnostic was recorded."

        raise MultiCandidateGenerationError(
            "Architectural Brain produced no hard-valid, "
            "critic-accepted candidate.\n"
            "Candidate diagnostics:\n"
            f"{diagnostic_text}"
        )

    accepted.sort(
        key=lambda item: (
            -item[0].combined_score_basis_points,
            -item[0].architecture_score_basis_points,
            str(item[0].candidate_id),
        )
    )

    # Deduplicate only after scoring so the strongest representative of an
    # effectively identical solved layout survives.
    unique_accepted: list[
        tuple[
            CandidateResult,
            CandidateArtifact,
            str,
            str,
        ]
    ] = []

    for item in accepted:
        candidate = item[0]
        topology_signature = item[2]

        current_document = candidate.plan_document
        if current_document is None:
            raise MultiCandidateGenerationError(
                "Accepted candidate lost its PlanDocument before deduplication."
            )
        duplicate_of = None
        reason_code = None

        for prior in unique_accepted:
            prior_document = prior[0].plan_document
            if prior_document is None:
                raise MultiCandidateGenerationError(
                    "Previously accepted candidate lost its PlanDocument during deduplication."
                )

            if not spatially_equivalent(
                current_document,
                prior_document,
            ):
                continue
            reason = duplicate_reason_code(
                topology_signature=topology_signature,
                spatial_signature="equivalent",
                prior_topology_signature=prior[2],
                prior_spatial_signature="equivalent",
            )

            if reason is not None:
                duplicate_of = prior
                reason_code = reason
                break

        if duplicate_of is not None and reason_code is not None:
            prior_candidate = duplicate_of[0]

            message = (
                "Candidate suppressed because its solved "
                f"{SPATIAL_DEDUP_QUANTUM_MM} mm-normalized spatial "
                "arrangement duplicates higher-ranked strategy "
                f"{prior_candidate.strategy.strategy_id}; "
                "topology_same="
                f"{topology_signature == duplicate_of[2]}."
            )

            exclusions.append(
                CandidateExclusion(
                    strategy_id=candidate.strategy.strategy_id,
                    reason_code=reason_code,
                    message=message,
                )
            )

            diagnostics.append(
                f"{candidate.strategy.strategy_id}: "
                f"{reason_code}; "
                "duplicate_of="
                f"{prior_candidate.strategy.strategy_id}; "
                "topology_same="
                f"{topology_signature == duplicate_of[2]}"
            )

            continue

        unique_accepted.append(item)

    selected = unique_accepted[:max_alternatives]

    candidates = tuple(
        item[0].model_copy(
            update={
                "rank": index,
            }
        )
        for index, item in enumerate(
            selected,
            start=1,
        )
    )
    result = CandidateRunResult(
        project_id=confirmed.project_id,
        planning_mode=planning_mode,
        candidates=candidates,
        exclusions=tuple(exclusions),
        attempted_candidate_count=len(concepts),
        rejected_candidate_count=max(0, len(concepts) - len(candidates)),
    ).with_content_hash()
    return MultiCandidateGenerationOutcome(
        run=result,
        selected_artifacts=tuple(item[1] for item in selected),
    )
