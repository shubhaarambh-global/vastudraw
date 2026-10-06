from __future__ import annotations

import math
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid5

from ai_vastu.architectural_geometry import BuildingDiagnosticSeverity
from ai_vastu.generation.models import ArchitecturalGenerationResult
from ai_vastu.plan_schema.geometry import IntPolygon
from ai_vastu.plan_schema.models import (
    Assumption,
    AssumptionSource,
    EvidenceItem,
    Floor,
    GenerationMetadata,
    Orientation,
    OrientationSource,
    PlanDocument,
    Plot,
    PlotGeometryType,
    PlotInputSource,
    Road,
    RoomType,
    ScoringSummary,
    ValidationReport,
    ValidationResult,
    ValidationSeverity,
    VastuAnalysis,
    VastuResult,
    VerificationStatus,
)
from ai_vastu.plan_schema.units import quantize_angle_udeg
from ai_vastu.scoring.models import ScoringCandidate, ScoringConfig, ScoringRequest
from ai_vastu.scoring.selector import score_and_select_alternatives
from ai_vastu.validation.vehicle_access import validate_document_vehicle_access
from ai_vastu.vastu.evaluator import evaluate_bundle
from ai_vastu.vastu.models import (
    GeometrySemantic,
    RuleBundle,
    RuleEvaluation,
    VastuFact,
    VastuRule,
)

from .generation_adapter import CompiledGeneration
from .models import ConfirmedRequirements

EXPECTED_VASTU_V1_BUNDLE_HASH = "b11b66be61d6436fcaa43c1c5b743c0090051154146d91caf904eb5108546667"
_DIRECTION_BEARINGS: dict[str, float] = {
    "N": 0.0,
    "NE": 45.0,
    "E": 90.0,
    "SE": 135.0,
    "S": 180.0,
    "SW": 225.0,
    "W": 270.0,
    "NW": 315.0,
}
# For canonical rectangular boundary order:
# (0,0) -> (w,0) -> (w,d) -> (0,d)
# the outward local bearings are S, E, N, W.
_LOCAL_EDGE_BEARINGS = (180.0, 90.0, 0.0, 270.0)
_ROOM_TYPES = {item.value for item in RoomType}


class Phase24FinalizationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CanonicalGeneration:
    document: PlanDocument
    candidate_id: UUID
    scoring: ScoringSummary
    vastu: VastuAnalysis
    bundle_hash: str


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def production_rule_bundle_path() -> Path:
    configured = os.getenv("AI_VASTU_VASTU_RULE_BUNDLE_PATH", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            raise Phase24FinalizationError(
                "AI_VASTU_VASTU_RULE_BUNDLE_PATH must be absolute when configured."
            )
        return path
    return _repository_root() / "docs" / "vastu" / "spec-v1.0" / "production" / "rule-bundle.json"


def load_production_vastu_bundle() -> RuleBundle:
    path = production_rule_bundle_path()
    if not path.is_file():
        raise Phase24FinalizationError(f"Frozen production Vastu bundle not found: {path}")
    bundle = RuleBundle.model_validate_json(path.read_text(encoding="utf-8"))
    if not bundle.production:
        raise Phase24FinalizationError("Vastu RuleBundle is not marked production.")
    if bundle.content_hash != EXPECTED_VASTU_V1_BUNDLE_HASH:
        raise Phase24FinalizationError(
            "Frozen Vastu v1 bundle hash does not match the approved Phase 20B hash."
        )
    if bundle.spec_version != "1.0.0":
        raise Phase24FinalizationError(
            f"Unsupported production Vastu spec version: {bundle.spec_version}"
        )
    if not bundle.rules:
        raise Phase24FinalizationError("Production Vastu bundle contains no rules.")
    return bundle


def _polygon_centroid(polygon: IntPolygon) -> tuple[float, float]:
    points = polygon.outer
    twice_area = 0
    cx_numerator = 0
    cy_numerator = 0
    for index, first in enumerate(points):
        second = points[(index + 1) % len(points)]
        cross = first.x_mm * second.y_mm - second.x_mm * first.y_mm
        twice_area += cross
        cx_numerator += (first.x_mm + second.x_mm) * cross
        cy_numerator += (first.y_mm + second.y_mm) * cross
    if twice_area == 0:
        raise Phase24FinalizationError("Cannot classify a zero-area polygon.")
    denominator = 3 * twice_area
    return cx_numerator / denominator, cy_numerator / denominator


def _sector_for_point(
    *,
    x_mm: float,
    y_mm: float,
    plot: IntPolygon,
    north_rotation_udeg: int,
) -> str:
    center_x, center_y = _polygon_centroid(plot)
    dx = x_mm - center_x
    dy = y_mm - center_y
    if dx == 0 and dy == 0:
        raise Phase24FinalizationError(
            "A room centroid at the exact plot center has no eight-sector direction."
        )

    # Canonical +Y is drawing North when rotation is zero. The stored North
    # rotation rotates true North relative to canonical drawing coordinates.
    local_bearing = math.degrees(math.atan2(dx, dy)) % 360.0
    north_rotation_deg = north_rotation_udeg / 1_000_000.0
    true_bearing = (local_bearing - north_rotation_deg) % 360.0
    sector_index = int(((true_bearing + 22.5) % 360.0) // 45.0)
    return ("N", "NE", "E", "SE", "S", "SW", "W", "NW")[sector_index]


def _target_room_types_for_rule(rule: VastuRule) -> set[str]:
    candidates = {rule.subject.entity_type.strip().lower().replace(" ", "_")}
    candidates.update(
        attribute.value.strip().lower().replace(" ", "_") for attribute in rule.subject.attributes
    )
    matches = candidates & _ROOM_TYPES
    if not matches:
        raise Phase24FinalizationError(
            f"Reviewed CENTROID_IN_ZONE rule has no deterministic RoomType selector: {rule.rule_id}"
        )
    return matches


def build_vastu_facts(
    *,
    bundle: RuleBundle,
    floor: Floor,
    plot_boundary: IntPolygon,
    north_rotation_udeg: int,
) -> tuple[VastuFact, ...]:
    facts: list[VastuFact] = []
    for rule in bundle.rules:
        if rule.geometry_semantic is not GeometrySemantic.CENTROID_IN_ZONE:
            raise Phase24FinalizationError(
                "Phase 24 MVP only supports the reviewed CENTROID_IN_ZONE Vastu v1 "
                f"rules; unsupported semantic on {rule.rule_id}: "
                f"{rule.geometry_semantic.value}"
            )

        room_types = _target_room_types_for_rule(rule)
        metric_key = rule.predicate.metric_key
        for room in floor.rooms:
            if room.room_type.value not in room_types:
                continue
            centroid_x, centroid_y = _polygon_centroid(room.polygon)
            sector = _sector_for_point(
                x_mm=centroid_x,
                y_mm=centroid_y,
                plot=plot_boundary,
                north_rotation_udeg=north_rotation_udeg,
            )
            facts.append(
                VastuFact(
                    entity_id=str(room.id),
                    entity_type=rule.subject.entity_type,
                    attributes=rule.subject.attributes,
                    geometry_semantic=rule.geometry_semantic,
                    metric_key=metric_key,
                    value=sector,
                    evidence=(
                        f"room_type={room.room_type.value}",
                        f"centroid_x_mm={centroid_x:.3f}",
                        f"centroid_y_mm={centroid_y:.3f}",
                        f"true_north_sector={sector}",
                    ),
                )
            )
    return tuple(facts)


def _entity_refs(evaluation: RuleEvaluation) -> tuple[UUID, ...]:
    if evaluation.entity_id is None:
        return ()
    try:
        return (UUID(evaluation.entity_id),)
    except ValueError:
        return ()


def build_vastu_analysis(
    *,
    bundle: RuleBundle,
    floor: Floor,
    plot_boundary: IntPolygon,
    north_rotation_udeg: int,
) -> VastuAnalysis:
    facts = build_vastu_facts(
        bundle=bundle,
        floor=floor,
        plot_boundary=plot_boundary,
        north_rotation_udeg=north_rotation_udeg,
    )
    evaluations = evaluate_bundle(bundle, facts)
    rules_by_id = {rule.rule_id: rule for rule in bundle.rules}

    results: list[VastuResult] = []
    total_raw = 0
    total_earned = 0
    major_violations = 0
    minor_compromises = 0

    for evaluation in evaluations:
        rule = rules_by_id[evaluation.rule_id]
        total_raw += evaluation.raw_weight
        total_earned += evaluation.earned_weight

        if evaluation.status.value == "FAIL":
            if rule.severity.value in {"MAJOR", "CRITICAL"}:
                major_violations += 1
            else:
                minor_compromises += 1
        elif evaluation.status.value in {"PARTIAL", "COMPROMISE"}:
            minor_compromises += 1

        geometry_evidence = tuple(
            EvidenceItem(key=f"geometry_{index + 1}", value=value)
            for index, value in enumerate(evaluation.evidence)
        )
        results.append(
            VastuResult(
                rule_id=evaluation.rule_id,
                rule_version=evaluation.rule_version,
                entity_refs=_entity_refs(evaluation),
                status=evaluation.status,
                measured_evidence=(),
                geometry_evidence=geometry_evidence,
                raw_weight=evaluation.raw_weight,
                earned_weight=evaluation.earned_weight,
            )
        )

    overall = None
    if total_raw > 0:
        overall = (total_earned * 10_000 + total_raw // 2) // total_raw

    return VastuAnalysis(
        spec_version=bundle.spec_version,
        results=tuple(results),
        overall_basis_points=overall,
        major_violations=major_violations,
        minor_compromises=minor_compromises,
    )


def _building_floors(result: ArchitecturalGenerationResult) -> tuple[Floor, ...]:
    if result.floor_results:
        floors = tuple(
            item.geometry_result.floor
            for item in sorted(result.floor_results, key=lambda item: item.floor_index)
            if item.geometry_result is not None
        )
        if len(floors) != len(result.floor_results):
            raise Phase24FinalizationError(
                "Accepted multi-floor generation is missing floor geometry."
            )
        return floors
    if result.geometry_result is None:
        raise Phase24FinalizationError("Accepted generation is missing floor geometry.")
    return (result.geometry_result.floor,)


def _building_validation_report(result: ArchitecturalGenerationResult) -> ValidationReport:
    """Bind every floor and 2D9G building diagnostic into canonical evidence."""

    if not result.floor_results:
        if result.validation_result is None:
            raise Phase24FinalizationError("Accepted generation is missing validation output.")
        return result.validation_result.report
    if result.building_validation is None or not result.building_validation.accepted:
        raise Phase24FinalizationError(
            "BUILDING_CIRCULATION_DISCONNECTED: accepted multi-floor generation lacks "
            "successful independent whole-building validation."
        )

    errors: list[ValidationResult] = []
    warnings: list[ValidationResult] = []
    informational: list[ValidationResult] = []
    for floor_result in sorted(result.floor_results, key=lambda item: item.floor_index):
        if floor_result.validation_result is None:
            raise Phase24FinalizationError(
                "Accepted multi-floor generation is missing per-floor validation output."
            )
        report = floor_result.validation_result.report
        errors.extend(report.errors)
        warnings.extend(report.warnings)
        informational.extend(report.informational)

    destinations = {
        BuildingDiagnosticSeverity.ERROR: errors,
        BuildingDiagnosticSeverity.WARNING: warnings,
        BuildingDiagnosticSeverity.INFO: informational,
    }
    severities = {
        BuildingDiagnosticSeverity.ERROR: ValidationSeverity.ERROR,
        BuildingDiagnosticSeverity.WARNING: ValidationSeverity.WARNING,
        BuildingDiagnosticSeverity.INFO: ValidationSeverity.INFO,
    }
    for diagnostic in result.building_validation.diagnostics:
        destinations[diagnostic.severity].append(
            ValidationResult(
                check_id=f"phase2d9g.building.{diagnostic.code.lower()}",
                severity=severities[diagnostic.severity],
                entity_refs=diagnostic.entity_refs,
                message_code=diagnostic.code,
                evidence=(
                    EvidenceItem(
                        key="floor_indices",
                        value=",".join(str(item) for item in diagnostic.floor_indices),
                    ),
                    EvidenceItem(key="message", value=diagnostic.message),
                ),
                validator_version="2D9G.1",
            )
        )

    def ordered(values: list[ValidationResult]) -> tuple[ValidationResult, ...]:
        return tuple(
            sorted(
                values,
                key=lambda item: (
                    item.check_id,
                    item.message_code,
                    tuple(str(ref) for ref in item.entity_refs),
                ),
            )
        )

    return ValidationReport(
        valid=not errors,
        errors=ordered(errors),
        warnings=ordered(warnings),
        informational=ordered(informational),
    )


def _validate_building_program(
    *,
    confirmed: ConfirmedRequirements,
    compiled: CompiledGeneration,
    floors: tuple[Floor, ...],
) -> None:
    expected = Counter(
        requirement.room_type.value
        for requirement in compiled.request.room_requirements
        for _ in range(requirement.quantity)
    )
    actual = Counter(room.room_type.value for floor in floors for room in floor.rooms)
    if actual != expected:
        raise Phase24FinalizationError(
            "BUILDING_PROGRAM_INCOMPLETE: generated room instances do not exactly "
            f"match the confirmed program for floor_count={confirmed.floor_count}; "
            f"expected={dict(expected)} actual={dict(actual)}."
        )
    indexes = tuple(floor.index for floor in floors)
    if indexes != tuple(range(confirmed.floor_count)):
        raise Phase24FinalizationError(
            "INVALID_FLOOR_COUNT: canonical floors must be ordered consecutively from index 0."
        )


def _build_building_vastu_analysis(
    *,
    bundle: RuleBundle,
    floors: tuple[Floor, ...],
    plot_boundary: IntPolygon,
    north_rotation_udeg: int,
) -> VastuAnalysis:
    analyses = tuple(
        build_vastu_analysis(
            bundle=bundle,
            floor=floor,
            plot_boundary=plot_boundary,
            north_rotation_udeg=north_rotation_udeg,
        )
        for floor in floors
    )
    results = tuple(item for analysis in analyses for item in analysis.results)
    raw = sum(item.raw_weight for item in results)
    earned = sum(item.earned_weight for item in results)
    return VastuAnalysis(
        spec_version=bundle.spec_version,
        results=results,
        overall_basis_points=None if raw == 0 else (earned * 10_000 + raw // 2) // raw,
        major_violations=sum(item.major_violations for item in analyses),
        minor_compromises=sum(item.minor_compromises for item in analyses),
    )


def _circular_difference(first: float, second: float) -> float:
    raw = abs(first - second) % 360.0
    return min(raw, 360.0 - raw)


def _road_edge_index(direction: str, north_rotation_udeg: int) -> int:
    target = _DIRECTION_BEARINGS.get(direction)
    if target is None:
        raise Phase24FinalizationError(f"Unsupported road direction: {direction}")

    north_rotation_deg = north_rotation_udeg / 1_000_000.0
    true_edge_bearings = tuple(
        (local_bearing - north_rotation_deg) % 360.0 for local_bearing in _LOCAL_EDGE_BEARINGS
    )
    differences = tuple(_circular_difference(bearing, target) for bearing in true_edge_bearings)
    best = min(differences)
    if best > 22.5 + 1e-9:
        raise Phase24FinalizationError(
            "Confirmed road side does not correspond to a rectangular plot edge "
            "under the confirmed true-North rotation."
        )
    candidates = [index for index, value in enumerate(differences) if abs(value - best) < 1e-9]
    if len(candidates) != 1:
        raise Phase24FinalizationError(
            "Confirmed road side is ambiguous between multiple plot edges."
        )
    return candidates[0]


def _stable_id(project_id: UUID, key: str) -> UUID:
    return uuid5(project_id, f"phase24-final:{key}")


def _generation_identity(result: ArchitecturalGenerationResult) -> str:
    return (
        result.content_hash
        or result.planner_result.content_hash
        or result.planner_result.metadata.problem_hash
    )


def _candidate_id(
    project_id: UUID,
    draft_id: UUID,
    result: ArchitecturalGenerationResult,
) -> UUID:
    return _stable_id(
        project_id,
        f"candidate:{draft_id}:{_generation_identity(result)}",
    )


def _revision_id(
    project_id: UUID,
    draft_id: UUID,
    result: ArchitecturalGenerationResult,
    bundle: RuleBundle,
) -> UUID:
    return _stable_id(
        project_id,
        f"revision:{draft_id}:{_generation_identity(result)}:{bundle.content_hash}",
    )


def _confirmed_context_assumption(
    confirmed: ConfirmedRequirements,
) -> Assumption:
    entrance = (
        confirmed.entrance_facing.value
        if confirmed.entrance_facing is not None
        else "not-specified"
    )
    return Assumption(
        id=_stable_id(confirmed.project_id, f"confirmed-context:{confirmed.draft_id}"),
        code="PHASE24_CONFIRMED_CONTEXT",
        description=(
            f"Human-confirmed planning context: road_side={confirmed.road_side.value}; "
            f"entrance_facing={entrance}; vastu_mode={confirmed.vastu_mode.value}; "
            f"floor_count={confirmed.floor_count}."
        ),
        source=AssumptionSource("USER"),
        confirmed_by_user=True,
        affected_entity_ids=(),
    )


def _score_generation(
    *,
    result: ArchitecturalGenerationResult,
    candidate_id: UUID,
) -> ScoringSummary:
    if result.geometry_result is None or result.validation_result is None:
        raise Phase24FinalizationError(
            "Accepted generation is missing geometry or validation output."
        )
    scoring_result = score_and_select_alternatives(
        ScoringRequest(
            problem=result.problem,
            config=ScoringConfig(
                max_alternatives=1,
                room_change_threshold_mm=300,
                minimum_changed_rooms=1,
                reject_validation_warnings=False,
            ),
            candidates=(
                ScoringCandidate(
                    candidate_id=candidate_id,
                    planner_result=result.planner_result,
                    geometry_result=result.geometry_result,
                    validation_result=result.validation_result,
                ),
            ),
        )
    )
    if not scoring_result.selected:
        raise Phase24FinalizationError("Accepted generation was excluded by deterministic scoring.")
    return scoring_result.selected[0].candidate.scoring_summary


def build_canonical_plan_document(
    *,
    confirmed: ConfirmedRequirements,
    compiled: CompiledGeneration,
    result: ArchitecturalGenerationResult,
) -> CanonicalGeneration:
    if result.disposition.value != "ACCEPTED":
        raise Phase24FinalizationError(
            "Only ACCEPTED deterministic generations can become project revisions."
        )
    if result.geometry_result is None or result.validation_result is None:
        raise Phase24FinalizationError(
            "Accepted generation is missing geometry or validation output."
        )
    if not result.validation_result.report.valid:
        raise Phase24FinalizationError(
            "Invalid geometry cannot become a canonical project revision."
        )
    bundle = load_production_vastu_bundle()
    north = quantize_angle_udeg(str(confirmed.north_rotation_deg)).microdegrees
    candidate_id = _candidate_id(confirmed.project_id, confirmed.draft_id, result)
    revision_id = _revision_id(
        confirmed.project_id,
        confirmed.draft_id,
        result,
        bundle,
    )

    plot_boundary = compiled.request.plot_boundary
    edge_ids = tuple(
        _stable_id(confirmed.project_id, f"plot-edge:{index}")
        for index in range(len(plot_boundary.outer))
    )
    if len(edge_ids) != 4:
        raise Phase24FinalizationError(
            "Phase 24 commercial MVP requires a rectangular four-edge plot."
        )

    road_edge = _road_edge_index(confirmed.road_side.value, north)
    plot = Plot(
        id=_stable_id(confirmed.project_id, "plot"),
        geometry_type=PlotGeometryType("RECTANGLE"),
        boundary=plot_boundary,
        edge_ids=edge_ids,
        input_source=PlotInputSource("MANUAL"),
        verification_status=VerificationStatus("USER_VERIFIED"),
    )
    road = Road(
        id=_stable_id(confirmed.project_id, f"road:{confirmed.road_side.value}"),
        name=f"{confirmed.road_side.value} road",
        plot_edge_ids=(edge_ids[road_edge],),
        primary_access=True,
    )
    orientation = Orientation(
        north_rotation_udeg=north,
        source=OrientationSource("USER"),
        verified=True,
    )

    floors = _building_floors(result)
    _validate_building_program(
        confirmed=confirmed,
        compiled=compiled,
        floors=floors,
    )
    vastu_analysis = _build_building_vastu_analysis(
        bundle=bundle,
        floors=floors,
        plot_boundary=plot_boundary,
        north_rotation_udeg=north,
    )
    scoring = _score_generation(result=result, candidate_id=candidate_id)

    metadata = result.planner_result.metadata
    document = PlanDocument(
        schema_version="1.1.0",
        project_id=confirmed.project_id,
        revision_id=revision_id,
        canonical_units="mm",
        plot=plot,
        orientation=orientation,
        roads=(road,),
        buildable_area=compiled.request.buildable_area,
        room_requirements=compiled.request.room_requirements,
        floors=floors,
        vastu_spec_version=bundle.spec_version,
        vastu_analysis=vastu_analysis,
        validation=_building_validation_report(result),
        scoring=scoring,
        assumptions=(
            *compiled.request.assumptions,
            _confirmed_context_assumption(confirmed),
        ),
        generation_metadata=GenerationMetadata(
            solver_name=metadata.solver_name,
            solver_version=metadata.solver_version,
            solver_parameters=(),
            solver_step_mm=metadata.config.solver_step_mm,
            seed=metadata.config.random_seed,
            rule_bundle_hash=bundle.content_hash,
            input_hash=metadata.problem_hash,
        ),
    )

    vehicle_failures = validate_document_vehicle_access(document)
    if vehicle_failures:
        raise Phase24FinalizationError(
            "Final canonical vehicle access failed: " + ", ".join(vehicle_failures)
        )

    return CanonicalGeneration(
        document=document,
        candidate_id=candidate_id,
        scoring=scoring,
        vastu=vastu_analysis,
        bundle_hash=bundle.content_hash,
    )
