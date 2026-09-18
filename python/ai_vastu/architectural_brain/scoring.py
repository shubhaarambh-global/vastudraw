from __future__ import annotations

from collections.abc import Iterable

from ai_vastu.plan_schema import IntPoint, PlanDocument

from .models import ArchitecturalQualityScore, EvidenceStatus, QualityMetric


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
    envelope_area = _polygon_area(document.buildable_area.polygon.outer)
    room_area = sum(_polygon_area(room.polygon.outer) for room in floor.rooms)
    utilization = min(10_000, round(room_area * 10_000 / max(1, envelope_area)))

    proportion_scores: list[int] = []
    for room in floor.rooms:
        xs = [point.x_mm for point in room.polygon.outer]
        ys = [point.y_mm for point in room.polygon.outer]
        width = max(xs) - min(xs)
        depth = max(ys) - min(ys)
        short = max(1, min(width, depth))
        long = max(width, depth)
        ratio = long / short
        proportion_scores.append(10_000 if ratio <= 1.8 else 7500 if ratio <= 2.4 else 4000)
    room_quality = (
        round(sum(proportion_scores) / len(proportion_scores)) if proportion_scores else 0
    )

    opening_count = len(floor.openings)
    access_score = min(10_000, opening_count * 1200)

    metrics = (
        QualityMetric(
            key="site_allocation",
            label="Site allocation",
            status=EvidenceStatus.EVALUATED,
            score_basis_points=utilization,
            weight=15,
            evidence=(f"Room polygons occupy {utilization / 100:.1f}% of envelope.",),
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
        QualityMetric(
            key="service_planning",
            label="Service planning",
            status=EvidenceStatus.NOT_EVALUATED,
            weight=4,
            note="Needs plumbing-wall/shaft evidence.",
        ),
        QualityMetric(
            key="buildability",
            label="Wall/buildability efficiency",
            status=EvidenceStatus.EVALUATED,
            score_basis_points=max(0, 10_000 - max(0, len(floor.walls) - 24) * 250),
            weight=4,
            evidence=(f"{len(floor.walls)} wall segments.",),
        ),
    )
    return _score_weighted(metrics)
