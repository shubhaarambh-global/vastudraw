from __future__ import annotations

from collections.abc import Iterable

from ai_vastu.architectural_geometry import evaluate_wet_stacks
from ai_vastu.plan_schema import IntPoint, PlanDocument

from .models import ArchitecturalQualityScore, EvidenceStatus, QualityMetric
from .site_accounting import analyze_floor_site_accounting


def _polygon_area(points: tuple[IntPoint, ...]) -> int:
    xy = [(p.x_mm, p.y_mm) for p in points]
    total = 0
    for index, (x1, y1) in enumerate(xy):
        x2, y2 = xy[(index + 1) % len(xy)]
        total += x1 * y2 - x2 * y1
    return abs(total) // 2


def _score_weighted(metrics: Iterable[QualityMetric]) -> ArchitecturalQualityScore:
    items = tuple(metrics)
    evaluated = [m for m in items if m.status is EvidenceStatus.EVALUATED]
    unevaluated = [m for m in items if m.status is EvidenceStatus.NOT_EVALUATED]
    evaluated_weight = sum(m.weight for m in evaluated)
    unevaluated_weight = sum(m.weight for m in unevaluated)
    total = evaluated_weight + unevaluated_weight
    coverage = 10_000 if total == 0 else round(evaluated_weight * 10_000 / total)
    score = None
    if evaluated_weight:
        score = round(
            sum((m.score_basis_points or 0) * m.weight for m in evaluated) / evaluated_weight
        )
    return ArchitecturalQualityScore(
        score_basis_points=score,
        evaluation_coverage_basis_points=coverage,
        evaluated_weight=evaluated_weight,
        unevaluated_weight=unevaluated_weight,
        metrics=items,
    )


def score_plan_document(document: PlanDocument) -> ArchitecturalQualityScore:
    floor = document.floors[0]
    site_accounting = analyze_floor_site_accounting(
        envelope=document.buildable_area.polygon,
        floor=floor,
        solver_step_mm=document.generation_metadata.solver_step_mm or 1,
    )
    utilization = site_accounting.accounting.allocation_basis_points

    proportion_scores: list[int] = []
    for candidate_floor in document.floors:
        for room in candidate_floor.rooms:
            xs = [point.x_mm for point in room.polygon.outer]
            ys = [point.y_mm for point in room.polygon.outer]
            width = max(xs) - min(xs)
            depth = max(ys) - min(ys)
            short = max(1, min(width, depth))
            long = max(width, depth)
            ratio = long / short
            proportion_scores.append(
                10_000 if ratio <= 1.8 else 7500 if ratio <= 2.4 else 4000
            )
    room_quality = (
        round(sum(proportion_scores) / len(proportion_scores)) if proportion_scores else 0
    )

    opening_count = sum(len(candidate_floor.openings) for candidate_floor in document.floors)
    access_score = min(10_000, opening_count * 1200)
    wet_stack = evaluate_wet_stacks(document.floors) if len(document.floors) > 1 else None

    metrics = (
        QualityMetric(
            key="site_allocation",
            label="Site allocation",
            status=EvidenceStatus.EVALUATED,
            score_basis_points=utilization,
            weight=15,
            evidence=(
                "Explicit room and purposeful-site polygons account for "
                f"{utilization / 100:.1f}% of the buildable envelope.",
            ),
        ),
        QualityMetric(
            key="room_proportions",
            label="Room proportions",
            status=EvidenceStatus.EVALUATED,
            score_basis_points=room_quality,
            weight=15,
            evidence=("Evaluated from room polygon aspect ratios.",),
        ),
        QualityMetric(
            key="circulation_access",
            label="Circulation and access",
            status=EvidenceStatus.EVALUATED,
            score_basis_points=access_score,
            weight=15,
            evidence=(f"{opening_count} generated openings are present.",),
        ),
        QualityMetric(
            key="topology_adjacency",
            label="Topology and adjacency",
            status=EvidenceStatus.EVALUATED,
            score_basis_points=document.scoring.overall_basis_points,
            weight=15,
            evidence=("Uses deterministic objective evidence from the canonical plan.",),
        ),
        QualityMetric(
            key="privacy",
            label="Privacy",
            status=EvidenceStatus.NOT_EVALUATED,
            weight=8,
            note="Needs door-path/sight-line evidence before scoring.",
        ),
        QualityMetric(
            key="daylight",
            label="Daylight potential",
            status=EvidenceStatus.NOT_EVALUATED,
            weight=8,
            note="Needs window/exterior-edge evidence before scoring.",
        ),
        QualityMetric(
            key="ventilation",
            label="Ventilation potential",
            status=EvidenceStatus.NOT_EVALUATED,
            weight=8,
            note="Needs opposing/perimeter opening evidence before scoring.",
        ),
        QualityMetric(
            key="furniture",
            label="Furniture feasibility",
            status=EvidenceStatus.NOT_EVALUATED,
            weight=8,
            note="Needs deterministic furniture-fit evaluation.",
        ),
        (
            QualityMetric(
                key="service_planning",
                label="Vertical wet/service coordination",
                status=EvidenceStatus.EVALUATED,
                score_basis_points=wet_stack.score_basis_points,
                weight=4,
                evidence=(
                    f"Aligned={wet_stack.aligned_count}; "
                    f"proximate={wet_stack.proximate_count}; "
                    f"dispersed={wet_stack.dispersed_count}; "
                    f"unpaired={len(wet_stack.unpaired_upper_room_ids)}.",
                ),
            )
            if wet_stack is not None
            else QualityMetric(
                key="service_planning",
                label="Service planning",
                status=EvidenceStatus.NOT_EVALUATED,
                weight=4,
                note="Vertical wet-stack evidence requires a multi-floor building.",
            )
        ),
        QualityMetric(
            key="buildability",
            label="Wall/buildability efficiency",
            status=EvidenceStatus.EVALUATED,
            score_basis_points=max(
                0,
                10_000
                - max(
                    0,
                    sum(len(candidate_floor.walls) for candidate_floor in document.floors)
                    - 24 * len(document.floors),
                )
                * 250,
            ),
            weight=4,
            evidence=(
                f"{sum(len(candidate_floor.walls) for candidate_floor in document.floors)} "
                "wall segments across the building.",
            ),
        ),
    )
    return _score_weighted(metrics)
