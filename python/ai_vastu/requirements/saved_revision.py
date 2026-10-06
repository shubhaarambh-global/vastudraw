from __future__ import annotations

from dataclasses import replace
from typing import Literal
from uuid import UUID, uuid4

from ai_vastu.plan_schema import PlanDocument, RoomRequirement

from .finalization import CanonicalGeneration, build_canonical_plan_document
from .generation_adapter import compile_confirmed_requirements, run_compiled_generation
from .models import ConfirmedRequirements


def regenerate_room_dimension(
    *,
    base: PlanDocument,
    confirmed: ConfirmedRequirements,
    room_id: UUID,
    axis: Literal["width", "depth"],
    target_mm: int,
    exact: bool = True,
) -> CanonicalGeneration:
    """Regenerate a valid plan using saved constraints and a confirmed dimension."""
    if base.project_id != confirmed.project_id or axis not in {"width", "depth"}:
        raise ValueError("Invalid revision context.")
    if len(base.floors) != 1 or confirmed.floor_count != 1:
        raise ValueError("Saved-plan dimension regeneration currently supports one floor.")
    if any(floor.fixtures or floor.furniture or floor.annotations for floor in base.floors):
        raise ValueError("Regeneration cannot preserve saved furnishings or annotations.")
    if any(room.locked for floor in base.floors for room in floor.rooms):
        raise ValueError("Regeneration cannot preserve locked room geometry.")
    rooms = [room for floor in base.floors for room in floor.rooms if room.id == room_id]
    if len(rooms) != 1 or target_mm <= 0:
        raise ValueError("Invalid room dimension request.")
    room = rooms[0]
    base_values = [p.x_mm if axis == "width" else p.y_mm for p in room.polygon.outer]
    if max(base_values) - min(base_values) == target_mm:
        raise ValueError("The requested dimension is already saved.")
    compiled = compile_confirmed_requirements(confirmed)
    reserve_mm = compiled.request.planner_config.clearance_reserve_mm
    # Canonical polygons describe envelopes; solver minima describe clear dimensions.
    # Its explicit wall reserve is added to minima, but maxima bound the envelope.
    minimum_target_mm = target_mm - reserve_mm if exact else target_mm
    requirements: list[RoomRequirement] = []
    matched = False
    for requirement in base.room_requirements:
        if requirement.id == room.requirement_id:
            maximum = getattr(requirement, f"max_{axis}_mm")
            minimum = getattr(requirement, f"min_{axis}_mm")
            if (
                requirement.locked
                or minimum_target_mm < minimum
                or (maximum is not None and target_mm > maximum)
            ):
                raise ValueError("The dimension conflicts with existing room constraints.")
            # A user-confirmed exact dimension is authoritative; AI supplies no coordinates.
            changes = {
                f"min_{axis}_mm": minimum_target_mm,
                f"preferred_{axis}_mm": target_mm,
            }
            if exact:
                changes[f"max_{axis}_mm"] = target_mm
            requirement = requirement.model_copy(update=changes)
            matched = True
        requirements.append(requirement)
    if not matched:
        raise ValueError("Saved room requirement is unavailable.")
    compiled = replace(
        compiled,
        request=compiled.request.model_copy(
            update={
                "room_requirements": tuple(requirements),
            }
        ),
    )
    result = run_compiled_generation(compiled)
    canonical = build_canonical_plan_document(confirmed=confirmed, compiled=compiled, result=result)
    document = canonical.document
    if (
        document.plot != base.plot
        or document.orientation != base.orientation
        or document.roads != base.roads
        or document.buildable_area != base.buildable_area
    ):
        raise ValueError("Regeneration would change saved site constraints.")
    revised = [
        r for f in document.floors for r in f.rooms if r.requirement_id == room.requirement_id
    ]
    if len(revised) != 1:
        raise ValueError("Requested room identity changed.")
    values = [p.x_mm if axis == "width" else p.y_mm for p in revised[0].polygon.outer]
    achieved = max(values) - min(values)
    if achieved < target_mm or (exact and achieved != target_mm):
        raise ValueError("Requested dimension was not achieved.")
    document = document.model_copy(
        update={"revision_id": uuid4(), "content_hash": None}
    ).with_content_hash()
    return replace(canonical, document=document)
