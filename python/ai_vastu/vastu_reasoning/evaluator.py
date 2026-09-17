from __future__ import annotations

import math
from collections import defaultdict
from typing import Literal

from ai_vastu.plan_schema import IntPolygon, PlanDocument, RoomGeometry

from .models import (
    EvaluationKind,
    RuleApplicability,
    RuleImportance,
    SoftVastuCatalog,
    SoftVastuRule,
    VastuReasoningProfile,
    VastuRuleAssessment,
    WeightedVastuAssessment,
)

SectorStatus = Literal[
    "PREFERRED",
    "SECONDARY",
    "NEUTRAL",
    "AVOIDED",
]


_IMPORTANCE_FACTOR = {
    RuleImportance.NEGLIGIBLE: 0,
    RuleImportance.LOW: 25,
    RuleImportance.MODERATE: 50,
    RuleImportance.HIGH: 75,
    RuleImportance.CORE: 100,
}


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
        raise ValueError("Cannot classify zero-area polygon.")
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
        return "CENTER"
    local_bearing = math.degrees(math.atan2(dx, dy)) % 360.0
    north_rotation_deg = north_rotation_udeg / 1_000_000.0
    true_bearing = (local_bearing - north_rotation_deg) % 360.0
    index = int(((true_bearing + 22.5) % 360.0) // 45.0)
    return ("N", "NE", "E", "SE", "S", "SW", "W", "NW")[index]


def _sector_score(
    sector: str,
    rule: SoftVastuRule,
) -> tuple[int, SectorStatus]:
    if sector in rule.preferred_sectors:
        return 10_000, "PREFERRED"
    if sector in rule.secondary_sectors:
        return 7_500, "SECONDARY"
    if sector in rule.avoid_sectors:
        return 0, "AVOIDED"
    return 5_000, "NEUTRAL"


def assess_plan(
    document: PlanDocument,
    profile: VastuReasoningProfile,
    catalog: SoftVastuCatalog,
) -> WeightedVastuAssessment:
    profile_by_id = {item.rule_id: item for item in profile.rules}
    all_rooms = tuple(room for floor in document.floors for room in floor.rooms)
    rooms_by_type: dict[str, list[RoomGeometry]] = defaultdict(list)
    for room in all_rooms:
        rooms_by_type[room.room_type.value].append(room)

    assessments: list[VastuRuleAssessment] = []
    weighted_sum = 0
    total_weight = 0
    suggestions: list[str] = []

    for rule in catalog.rules:
        context = profile_by_id[rule.rule_id]
        effective_weight = (
            rule.base_weight
            * _IMPORTANCE_FACTOR[context.importance]
            * context.weight_multiplier_basis_points
            // 10_000
        )

        if context.applicability is RuleApplicability.NOT_APPLICABLE:
            assessments.append(
                VastuRuleAssessment(
                    rule_id=rule.rule_id,
                    title=rule.title,
                    applicability=context.applicability,
                    importance=context.importance,
                    flexibility=context.flexibility,
                    score_basis_points=None,
                    effective_weight=0,
                    status="NOT_APPLICABLE",
                    evidence=("reasoning_profile=NOT_APPLICABLE",),
                    suggestion=rule.suggestion,
                )
            )
            continue

        if rule.evaluation_kind is EvaluationKind.UNSUPPORTED:
            assessments.append(
                VastuRuleAssessment(
                    rule_id=rule.rule_id,
                    title=rule.title,
                    applicability=context.applicability,
                    importance=context.importance,
                    flexibility=context.flexibility,
                    score_basis_points=None,
                    effective_weight=effective_weight,
                    status="NOT_EVALUATED",
                    evidence=("geometry_evaluator=not_implemented_in_26B",),
                    suggestion=rule.suggestion,
                )
            )
            continue

        matching = [
            room
            for room_type in rule.subject_room_types
            for room in rooms_by_type.get(room_type, [])
        ]
        if not matching:
            assessments.append(
                VastuRuleAssessment(
                    rule_id=rule.rule_id,
                    title=rule.title,
                    applicability=RuleApplicability.NOT_APPLICABLE,
                    importance=context.importance,
                    flexibility=context.flexibility,
                    score_basis_points=None,
                    effective_weight=0,
                    status="NOT_APPLICABLE",
                    evidence=("matching_entities=0",),
                    suggestion=rule.suggestion,
                )
            )
            continue

        room_scores: list[int] = []
        room_statuses: list[SectorStatus] = []
        evidence: list[str] = []
        for room in matching:
            cx, cy = _polygon_centroid(room.polygon)
            sector = _sector_for_point(
                x_mm=cx,
                y_mm=cy,
                plot=document.plot.boundary,
                north_rotation_udeg=document.orientation.north_rotation_udeg,
            )
            score, status = _sector_score(sector, rule)
            room_scores.append(score)
            room_statuses.append(status)
            evidence.append(
                f"room={room.id};type={room.room_type.value};sector={sector};score={score}"
            )

        score = sum(room_scores) // len(room_scores)
        rank = {"AVOIDED": 0, "NEUTRAL": 1, "SECONDARY": 2, "PREFERRED": 3}
        status = min(room_statuses, key=lambda value: rank[value])

        if effective_weight > 0:
            weighted_sum += score * effective_weight
            total_weight += effective_weight

        if score < 10_000:
            suggestions.append(rule.suggestion)

        assessments.append(
            VastuRuleAssessment(
                rule_id=rule.rule_id,
                title=rule.title,
                applicability=context.applicability,
                importance=context.importance,
                flexibility=context.flexibility,
                score_basis_points=score,
                effective_weight=effective_weight,
                status=status,
                evidence=tuple(evidence),
                suggestion=rule.suggestion,
            )
        )

    overall = None if total_weight == 0 else weighted_sum // total_weight
    profile_hash = profile.content_hash or profile.compute_content_hash()
    return WeightedVastuAssessment(
        project_id=document.project_id,
        profile_hash=profile_hash,
        overall_basis_points=overall,
        rules=tuple(assessments),
        suggestions=tuple(dict.fromkeys(suggestions)),
    ).with_content_hash()
