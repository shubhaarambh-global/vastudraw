from __future__ import annotations

from ai_vastu.architectural_geometry import evaluate_wet_stacks, validate_circulation
from ai_vastu.plan_schema import PlanDocument, RoomGeometry

from .models import (
    ArchitecturalCritique,
    CritiqueFinding,
    CritiqueSeverity,
)
from .scoring import score_plan_document
from .site_accounting import analyze_floor_site_accounting

_MIN_SITE_ALLOCATION_BASIS_POINTS = 8_500

_SANITARY_ROOM_TYPES = frozenset(
    {
        "attached_toilet",
        "common_toilet",
        "powder_room",
        "bath",
        "servant_toilet",
    }
)


def _shared_axis_aligned_wall_length_mm(
    first: RoomGeometry,
    second: RoomGeometry,
) -> int:
    """Return actual collinear shared-boundary length for orthogonal rooms."""

    first_points = first.polygon.outer
    second_points = second.polygon.outer
    best = 0

    for first_index, first_start in enumerate(first_points):
        first_end = first_points[(first_index + 1) % len(first_points)]

        for second_index, second_start in enumerate(second_points):
            second_end = second_points[(second_index + 1) % len(second_points)]

            # Vertical collinear segments.
            if (
                first_start.x_mm == first_end.x_mm
                and second_start.x_mm == second_end.x_mm
                and first_start.x_mm == second_start.x_mm
            ):
                first_lo = min(first_start.y_mm, first_end.y_mm)
                first_hi = max(first_start.y_mm, first_end.y_mm)
                second_lo = min(second_start.y_mm, second_end.y_mm)
                second_hi = max(second_start.y_mm, second_end.y_mm)

                best = max(
                    best,
                    max(
                        0,
                        min(first_hi, second_hi) - max(first_lo, second_lo),
                    ),
                )

            # Horizontal collinear segments.
            if (
                first_start.y_mm == first_end.y_mm
                and second_start.y_mm == second_end.y_mm
                and first_start.y_mm == second_start.y_mm
            ):
                first_lo = min(first_start.x_mm, first_end.x_mm)
                first_hi = max(first_start.x_mm, first_end.x_mm)
                second_lo = min(second_start.x_mm, second_end.x_mm)
                second_hi = max(second_start.x_mm, second_end.x_mm)

                best = max(
                    best,
                    max(
                        0,
                        min(first_hi, second_hi) - max(first_lo, second_lo),
                    ),
                )

    return best


def critique_plan(
    document: PlanDocument,
    *,
    repair_round: int = 0,
) -> ArchitecturalCritique:
    findings: list[CritiqueFinding] = []
    floor = document.floors[0]

    if document.generation_metadata.solver_step_mm is not None:
        for candidate_floor in document.floors:
            stair_rooms = tuple(
                room
                for room in candidate_floor.rooms
                if room.room_type.value == "staircase"
            )
            if candidate_floor.index > 0 and len(stair_rooms) != 1:
                findings.append(
                    CritiqueFinding(
                        code="VERTICAL_CORE_MISSING",
                        severity=CritiqueSeverity.REJECT,
                        message=(
                            f"Floor {candidate_floor.index} has no unique canonical "
                            "staircase arrival."
                        ),
                        repair_hint=(
                            "Reserve one continuous core before solving every served floor."
                        ),
                    )
                )
                continue
            circulation = validate_circulation(
                candidate_floor,
                require_external_entry=candidate_floor.index == 0,
                anchor_room_ids=()
                if candidate_floor.index == 0
                else (stair_rooms[0].id,),
            )
            if circulation.accepted:
                continue
            findings.append(
                CritiqueFinding(
                    code=circulation.reason_code or "CIRCULATION_INVALID",
                    severity=CritiqueSeverity.REJECT,
                    message=f"Floor {candidate_floor.index}: {circulation.message}",
                    repair_hint=(
                        "Re-solve the room topology so the dwelling entry and aligned "
                        "stair reach every required room through real door-capable shared "
                        "walls; sanitary rooms may not serve as transit corridors."
                    ),
                )
            )

    if len(document.floors) > 1:
        for lower, upper in zip(document.floors, document.floors[1:], strict=False):
            if len(lower.stairs) != 1 or len(upper.stairs) != 1:
                findings.append(
                    CritiqueFinding(
                        code="VERTICAL_CORE_MISSING",
                        severity=CritiqueSeverity.REJECT,
                        message="Every consecutive floor pair requires one canonical stair.",
                        repair_hint="Generate and validate a continuous building-level core.",
                    )
                )
                continue
            if lower.stairs[0].footprint != upper.stairs[0].footprint:
                findings.append(
                    CritiqueFinding(
                        code="VERTICAL_CORE_MISALIGNED",
                        severity=CritiqueSeverity.REJECT,
                        message=(
                            f"Stair footprints on floors {lower.index} and {upper.index} "
                            "do not align."
                        ),
                        repair_hint=(
                            "Use the same deterministic core reservation on consecutive floors."
                        ),
                    )
                )

        wet_stack = evaluate_wet_stacks(document.floors)
        if wet_stack.dispersed_count or wet_stack.unpaired_upper_room_ids:
            findings.append(
                CritiqueFinding(
                    code="WET_STACK_SUBOPTIMAL",
                    severity=CritiqueSeverity.WARNING,
                    message=(
                        "The building is valid, but some upper-floor wet/service rooms "
                        "are materially dispersed or lack a compatible lower-floor zone."
                    ),
                    repair_hint=(
                        "Prefer aligned or proximate plumbing zones without overriding "
                        "room usability or hard requirements."
                    ),
                )
            )

    try:
        site_accounting = analyze_floor_site_accounting(
            envelope=document.buildable_area.polygon,
            floor=floor,
            solver_step_mm=(document.generation_metadata.solver_step_mm or 1),
        )
    except ValueError as exc:
        return ArchitecturalCritique(
            accepted=False,
            findings=(
                CritiqueFinding(
                    code="INVALID_SITE_ACCOUNTING_GEOMETRY",
                    severity=CritiqueSeverity.REJECT,
                    message=str(exc),
                    repair_hint=(
                        "Keep every room and purposeful-site polygon "
                        "inside the buildable envelope and prevent "
                        "classified polygons from overlapping."
                    ),
                ),
            ),
            repair_round=repair_round,
        )

    score = score_plan_document(document)
    metric_index = {item.key: item for item in score.metrics}

    site = metric_index["site_allocation"]
    site_score = site.score_basis_points or 0

    if site_score < _MIN_SITE_ALLOCATION_BASIS_POINTS:
        findings.append(
            CritiqueFinding(
                code="LOW_SITE_ALLOCATION",
                severity=CritiqueSeverity.REJECT,
                message=(
                    "Candidate leaves too much of the confirmed buildable "
                    "envelope outside useful or purposefully classified spaces."
                ),
                repair_hint=(
                    "Increase useful room/circulation allocation or explicitly "
                    "classify residual area as courtyard, landscape, utility, "
                    "shaft or other purposeful open space."
                ),
            )
        )

    # Percentage alone cannot distinguish intentional open space from
    # accidental dead land. Reject every geometrically unclassified residual.
    if site_accounting.unexplained_residual_area_mm2 > 0:
        envelope_area_mm2 = site_accounting.accounting.envelope_area_mm2
        residual_area_mm2 = site_accounting.unexplained_residual_area_mm2
        residual_bp = round(residual_area_mm2 * 10_000 / max(1, envelope_area_mm2))

        largest = site_accounting.residual_regions[0] if site_accounting.residual_regions else None

        residual_detail = (
            f"Unexplained residual is "
            f"{residual_area_mm2 / 1_000_000:.2f} m2 "
            f"({residual_bp / 100:.1f}% of the buildable envelope)."
        )

        if largest is not None:
            residual_detail += (
                " Largest residual region is "
                f"{largest.area_mm2 / 1_000_000:.2f} m2; "
                f"bbox=({largest.min_x_mm}, {largest.min_y_mm})-"
                f"({largest.max_x_mm}, {largest.max_y_mm}) mm; "
                f"centroid=({largest.centroid_x_mm}, "
                f"{largest.centroid_y_mm}) mm."
            )

        findings.append(
            CritiqueFinding(
                code="UNEXPLAINED_SITE_RESIDUAL",
                severity=CritiqueSeverity.REJECT,
                message=(
                    "Candidate contains geometrically unclassified space "
                    "inside the confirmed buildable envelope. " + residual_detail
                ),
                repair_hint=(
                    "Allocate the residual to legitimate program space or "
                    "represent it explicitly as a purposeful architectural "
                    "space such as courtyard, lightwell, shaft, landscape, "
                    "setback/open space, utility yard, porch or vehicle "
                    "access. Do not hide residual land by enlarging rooms."
                ),
            )
        )

    # Parking size has no universal architectural maximum. Confirmed user/site
    # constraints remain hard; automatic parking sizing is handled by the
    # solver's role-sensitive soft area targets. The critic therefore must not
    # reject a plan solely because a parking polygon crosses an arbitrary area
    # threshold. Site-accounting and circulation checks still reject filler or
    # unusable geometry through their own evidence-based rules.

    for candidate_floor in document.floors:
        puja_rooms = [
            room for room in candidate_floor.rooms if room.room_type.value == "puja"
        ]
        sanitary_rooms = [
            room
            for room in candidate_floor.rooms
            if room.room_type.value in _SANITARY_ROOM_TYPES
        ]

        for puja in puja_rooms:
            for sanitary in sanitary_rooms:
                shared_wall_mm = _shared_axis_aligned_wall_length_mm(
                    puja,
                    sanitary,
                )

                if shared_wall_mm <= 0:
                    continue

                findings.append(
                    CritiqueFinding(
                        code="PUJA_SANITARY_SHARED_WALL",
                        severity=CritiqueSeverity.REJECT,
                        message=(
                            f"Floor {candidate_floor.index}: puja space shares a wall "
                            "with a toilet/bathroom. This residential adjacency is not "
                            "accepted."
                        ),
                        repair_hint=(
                            "Separate the puja and sanitary space with another room, "
                            "circulation zone, shaft or non-sanitary buffer."
                        ),
                    )
                )

        if len(candidate_floor.openings) < max(2, len(candidate_floor.rooms) - 2):
            findings.append(
                CritiqueFinding(
                    code="WEAK_CIRCULATION_EVIDENCE",
                    severity=CritiqueSeverity.WARNING,
                    message=(
                        f"Floor {candidate_floor.index} has too few openings to "
                        "demonstrate a convincing access graph."
                    ),
                    repair_hint=(
                        "Require door-connected access from stair/entry to every "
                        "enclosed room."
                    ),
                )
            )

    rejected = any(item.severity is CritiqueSeverity.REJECT for item in findings)

    return ArchitecturalCritique(
        accepted=not rejected,
        findings=tuple(findings),
        repair_round=repair_round,
    )
