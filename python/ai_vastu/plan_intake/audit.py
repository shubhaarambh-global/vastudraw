from __future__ import annotations

import math
from collections import defaultdict
from typing import Literal

from ai_vastu.requirements.generation_profile import normalize_room_type
from ai_vastu.vastu_reasoning import load_soft_vastu_catalog
from ai_vastu.vastu_reasoning.models import EvaluationKind, RuleImportance

from .models import (
    AlternatePlanEnvelope,
    PlanAnalysisResult,
    PlanAuditStatus,
    PlanRecognitionDraft,
    PlanVastuAudit,
    PlanVastuRuleAudit,
)

_IMPORTANCE_FACTOR = {
    RuleImportance.NEGLIGIBLE: 0,
    RuleImportance.LOW: 25,
    RuleImportance.MODERATE: 50,
    RuleImportance.HIGH: 75,
    RuleImportance.CORE: 100,
}


def _sector_for_normalized_point(
    *,
    x_basis_points: int,
    y_basis_points: int,
    north_rotation_deg: float,
) -> str:
    dx = float(x_basis_points) - 5000.0
    dy = float(y_basis_points) - 5000.0
    if dx == 0.0 and dy == 0.0:
        return "CENTER"
    local_bearing = math.degrees(math.atan2(dx, dy)) % 360.0
    true_bearing = (local_bearing - north_rotation_deg) % 360.0
    index = int(((true_bearing + 22.5) % 360.0) // 45.0)
    return ("N", "NE", "E", "SE", "S", "SW", "W", "NW")[index]


def _sector_score(
    sector: str,
    *,
    preferred: tuple[str, ...],
    secondary: tuple[str, ...],
    avoided: tuple[str, ...],
) -> tuple[int, str]:
    if sector in preferred:
        return 10_000, "PREFERRED"
    if sector in secondary:
        return 7_500, "SECONDARY"
    if sector in avoided:
        return 0, "AVOIDED"
    return 5_000, "NEUTRAL"


def audit_recognized_plan(recognition: PlanRecognitionDraft) -> PlanVastuAudit:
    catalog = load_soft_vastu_catalog()
    north = recognition.orientation.north_rotation_deg

    rooms_by_type: dict[str, list[tuple[int, int, float, tuple[str, ...]]]] = defaultdict(list)
    for room in recognition.rooms:
        if room.centroid_x_basis_points is None or room.centroid_y_basis_points is None:
            continue
        room_type = normalize_room_type(room.room_type)
        rooms_by_type[room_type].append(
            (
                room.centroid_x_basis_points,
                room.centroid_y_basis_points,
                room.confidence,
                room.evidence,
            )
        )

    if north is None:
        return PlanVastuAudit(
            project_id=recognition.project_id,
            intake_id=recognition.intake_id,
            status=PlanAuditStatus.NEEDS_ORIENTATION,
            overall_basis_points=None,
            rules=(),
            suggestions=("Confirm the true-North direction before calculating a Vastu score.",),
            notes=(
                "No score is fabricated when true North is unknown.",
                "Uploaded-plan Vastu audits remain provisional until user confirmation.",
            ),
        ).with_content_hash()

    if not rooms_by_type:
        return PlanVastuAudit(
            project_id=recognition.project_id,
            intake_id=recognition.intake_id,
            status=PlanAuditStatus.NEEDS_ROOM_POSITIONS,
            overall_basis_points=None,
            rules=(),
            suggestions=("Confirm or improve room recognition before calculating a Vastu score.",),
            notes=(
                "No score is fabricated without room positions.",
                "Uploaded-plan Vastu audits remain provisional until user confirmation.",
            ),
        ).with_content_hash()

    audits: list[PlanVastuRuleAudit] = []
    suggestions: list[str] = []
    weighted_sum = 0
    total_weight = 0
    unevaluated_weight = 0

    for rule in catalog.rules:
        effective_weight = rule.base_weight * _IMPORTANCE_FACTOR[rule.default_importance]

        if rule.evaluation_kind is EvaluationKind.UNSUPPORTED:
            unevaluated_weight += effective_weight
            audits.append(
                PlanVastuRuleAudit(
                    rule_id=rule.rule_id,
                    title=rule.title,
                    status="NOT_EVALUATED",
                    score_basis_points=None,
                    effective_weight=effective_weight,
                    evidence=("geometry_evaluator=not_implemented_in_26B.5",),
                    suggestion=rule.suggestion,
                )
            )
            continue

        matching = [
            item
            for room_type in rule.subject_room_types
            for item in rooms_by_type.get(normalize_room_type(room_type), [])
        ]
        if not matching:
            audits.append(
                PlanVastuRuleAudit(
                    rule_id=rule.rule_id,
                    title=rule.title,
                    status="NOT_APPLICABLE",
                    score_basis_points=None,
                    effective_weight=0,
                    evidence=("matching_recognized_rooms=0",),
                    suggestion=rule.suggestion,
                )
            )
            continue

        scores: list[int] = []
        statuses: list[str] = []
        evidence: list[str] = []

        for x_bp, y_bp, confidence, source_evidence in matching:
            sector = _sector_for_normalized_point(
                x_basis_points=x_bp,
                y_basis_points=y_bp,
                north_rotation_deg=north,
            )
            score, status = _sector_score(
                sector,
                preferred=rule.preferred_sectors,
                secondary=rule.secondary_sectors,
                avoided=rule.avoid_sectors,
            )
            scores.append(score)
            statuses.append(status)
            evidence.append(
                f"recognized_centroid=({x_bp},{y_bp}); "
                f"true_north_sector={sector}; confidence={confidence:.2f}"
            )
            evidence.extend(source_evidence[:2])

        average_score = sum(scores) // len(scores)
        aggregate_status: Literal[
            "PREFERRED",
            "SECONDARY",
            "NEUTRAL",
            "AVOIDED",
        ]
        if "AVOIDED" in statuses:
            aggregate_status = "AVOIDED"
        elif all(item == "PREFERRED" for item in statuses):
            aggregate_status = "PREFERRED"
        elif "SECONDARY" in statuses:
            aggregate_status = "SECONDARY"
        else:
            aggregate_status = "NEUTRAL"

        weighted_sum += average_score * effective_weight
        total_weight += effective_weight

        audits.append(
            PlanVastuRuleAudit(
                rule_id=rule.rule_id,
                title=rule.title,
                status=aggregate_status,
                score_basis_points=average_score,
                effective_weight=effective_weight,
                evidence=tuple(evidence),
                suggestion=rule.suggestion,
            )
        )
        if average_score < 7_500 and rule.suggestion not in suggestions:
            suggestions.append(rule.suggestion)

    coverage_denominator = total_weight + unevaluated_weight
    coverage = (
        None
        if coverage_denominator == 0
        else (total_weight * 10_000 + coverage_denominator // 2) // coverage_denominator
    )

    if total_weight == 0:
        status = PlanAuditStatus.NO_EVALUABLE_RULES
        overall = None
    else:
        status = PlanAuditStatus.SCORED
        overall = (weighted_sum + total_weight // 2) // total_weight

    return PlanVastuAudit(
        project_id=recognition.project_id,
        intake_id=recognition.intake_id,
        status=status,
        overall_basis_points=overall,
        evaluation_coverage_basis_points=coverage,
        evaluated_weight=total_weight,
        unevaluated_weight=unevaluated_weight,
        rules=tuple(audits),
        suggestions=tuple(suggestions),
        notes=(
            "This is a provisional soft Vastu audit of recognized plan evidence.",
            (
                "Evaluation coverage measures the share of applicable weighted "
                "Vastu guidance that the current geometry evaluator can score."
            ),
            "Vastu guidance is traditional planning guidance, not a building-safety check.",
            "No Phase 26B.5 Vastu rule is a hard geometric constraint.",
        ),
    ).with_content_hash()


def alternate_plan_envelope(
    recognition: PlanRecognitionDraft,
) -> AlternatePlanEnvelope:
    envelope = recognition.envelope
    exact_area = envelope.built_up_area_mm2

    if (
        envelope.geometry_type == "RECTANGLE"
        and envelope.width_mm is not None
        and envelope.depth_mm is not None
    ):
        computed = envelope.width_mm * envelope.depth_mm
        if exact_area is None:
            exact_area = computed
        return AlternatePlanEnvelope(
            geometry_type="RECTANGLE",
            width_mm=envelope.width_mm,
            depth_mm=envelope.depth_mm,
            exact_area_mm2=exact_area,
            ready_for_exact_alternatives=False,
            requires_user_confirmation=True,
            reason=(
                "The envelope was recognized, but exact alternate generation is "
                "locked until the user confirms dimensions and true North."
            ),
        )

    return AlternatePlanEnvelope(
        geometry_type=envelope.geometry_type,
        width_mm=envelope.width_mm,
        depth_mm=envelope.depth_mm,
        exact_area_mm2=exact_area,
        ready_for_exact_alternatives=False,
        requires_user_confirmation=True,
        reason=("Exact alternate generation requires a confirmed measurable outer envelope."),
    )


def build_plan_analysis(recognition: PlanRecognitionDraft) -> PlanAnalysisResult:
    return PlanAnalysisResult(
        project_id=recognition.project_id,
        intake_id=recognition.intake_id,
        recognition=recognition,
        vastu_audit=audit_recognized_plan(recognition),
        alternate_plan_envelope=alternate_plan_envelope(recognition),
    ).with_content_hash()
