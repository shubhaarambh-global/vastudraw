from __future__ import annotations

from ai_vastu.plan_schema import PlanDocument

from .models import ArchitecturalCritique, CritiqueFinding, CritiqueSeverity
from .scoring import score_plan_document


def critique_plan(document: PlanDocument, *, repair_round: int = 0) -> ArchitecturalCritique:
    score = score_plan_document(document)
    findings: list[CritiqueFinding] = []
    metric_index = {item.key: item for item in score.metrics}

    site = metric_index["site_allocation"]
    if (site.score_basis_points or 0) < 8000:
        findings.append(
            CritiqueFinding(
                code="LOW_SITE_ALLOCATION",
                severity=CritiqueSeverity.WARNING,
                message="Plan leaves too much confirmed envelope outside useful room polygons.",
                repair_hint=(
                    "Increase useful allocation or explicitly classify remaining area as "
                    "open space/courtyard/landscape/utility; never inflate parking."
                ),
            )
        )

    floor = document.floors[0]
    parking_rooms = [room for room in floor.rooms if room.room_type.value in {"parking", "garage"}]
    for room in parking_rooms:
        xs = [p.x_mm for p in room.polygon.outer]
        ys = [p.y_mm for p in room.polygon.outer]
        area = (max(xs) - min(xs)) * (max(ys) - min(ys))
        if area > 20_000_000:
            findings.append(
                CritiqueFinding(
                    code="OVERSIZED_PARKING",
                    severity=CritiqueSeverity.REJECT,
                    message="Parking is oversized and appears to absorb residual site area.",
                    repair_hint="Cap one-car parking near 15-18 m² unless explicitly requested.",
                )
            )

    if len(floor.openings) < max(2, len(floor.rooms) - 2):
        findings.append(
            CritiqueFinding(
                code="WEAK_CIRCULATION_EVIDENCE",
                severity=CritiqueSeverity.WARNING,
                message="Too few openings to demonstrate a convincing access graph.",
                repair_hint="Require door-connected access from entry to every enclosed room.",
            )
        )

    rejected = any(item.severity is CritiqueSeverity.REJECT for item in findings)
    return ArchitecturalCritique(
        accepted=not rejected,
        findings=tuple(findings),
        repair_round=repair_round,
    )
