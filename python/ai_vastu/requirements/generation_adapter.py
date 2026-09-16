from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict

from ai_vastu.generation.models import (
    ArchitecturalGenerationRequest,
    ArchitecturalGenerationResult,
)
from ai_vastu.generation.service import generate_architectural_plan
from ai_vastu.requirements.generation_profile import (
    PROFILE_VERSION,
    ROOM_MINIMUMS,
    normalize_room_type,
)
from ai_vastu.requirements.models import ConfirmedRequirements


class UnsupportedConfirmedRequirement(ValueError):
    pass


class GenerateConfirmedOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: UUID
    accept_profile_defaults: Literal[True]


@dataclass(frozen=True, slots=True)
class CompiledGeneration:
    request: ArchitecturalGenerationRequest
    profile_version: str
    notices: tuple[str, ...]


def _stable_id(project_id: UUID, key: str) -> UUID:
    return uuid5(project_id, f"phase24b:{key}")


def _room_requirement(
    *,
    project_id: UUID,
    room_type: str,
    quantity: int,
    floor_preference: int | None,
    ordinal: int,
) -> dict[str, object]:
    if room_type not in ROOM_MINIMUMS:
        raise UnsupportedConfirmedRequirement(
            f"No deterministic room-minimum profile exists for room type: {room_type}"
        )
    minimum = ROOM_MINIMUMS[room_type]
    floor_preferences = [] if floor_preference is None else [floor_preference]
    return {
        "id": str(_stable_id(project_id, f"room:{ordinal}:{room_type}")),
        "room_type": room_type,
        "quantity": quantity,
        "min_width_mm": minimum.min_width_mm,
        "min_depth_mm": minimum.min_depth_mm,
        "min_area_mm2": minimum.min_area_mm2,
        "floor_preference": floor_preferences,
        "locked": False,
        "vastu_profile_refs": [],
        "privacy_priority": 50,
        "daylight_priority": 50,
        "ventilation_priority": 50,
        "user_priority": 50,
    }


def compile_confirmed_requirements(
    confirmed: ConfirmedRequirements,
) -> CompiledGeneration:
    if confirmed.floor_count != 1:
        raise UnsupportedConfirmedRequirement(
            "Commercial MVP currently supports exactly one generated floor."
        )
    for room in confirmed.rooms:
        if room.floor_preference not in {None, 0}:
            raise UnsupportedConfirmedRequirement(
                "Commercial MVP cannot silently drop an upper-floor preference."
            )

    width = confirmed.plot_width_mm
    depth = confirmed.plot_depth_mm

    polygon = {
        "outer": [
            {"x_mm": 0, "y_mm": 0},
            {"x_mm": width, "y_mm": 0},
            {"x_mm": width, "y_mm": depth},
            {"x_mm": 0, "y_mm": depth},
        ],
        "holes": [],
    }

    room_requirements: list[dict[str, object]] = []
    explicit_bedrooms = 0
    ordinal = 0

    for room in confirmed.rooms:
        room_type = normalize_room_type(room.room_type)
        if room_type in {
            "bedroom",
            "master_bedroom",
            "parents_bedroom",
            "guest_bedroom",
            "children_bedroom",
        }:
            explicit_bedrooms += room.quantity

        room_requirements.append(
            _room_requirement(
                project_id=confirmed.project_id,
                room_type=room_type,
                quantity=room.quantity,
                floor_preference=room.floor_preference,
                ordinal=ordinal,
            )
        )
        ordinal += 1

    missing_bedrooms = confirmed.bedroom_count - explicit_bedrooms
    if missing_bedrooms < 0:
        raise UnsupportedConfirmedRequirement(
            "Explicit bedroom requirements exceed bedroom_count."
        )
    if missing_bedrooms:
        room_requirements.append(
            _room_requirement(
                project_id=confirmed.project_id,
                room_type="bedroom",
                quantity=missing_bedrooms,
                floor_preference=None,
                ordinal=ordinal,
            )
        )
        ordinal += 1

    explicit_parking = sum(
        room.quantity
        for room in confirmed.rooms
        if normalize_room_type(room.room_type) in {"parking", "garage"}
    )
    missing_parking = confirmed.parking_count - explicit_parking
    if missing_parking < 0:
        raise UnsupportedConfirmedRequirement(
            "Explicit parking requirements exceed parking_count."
        )
    if missing_parking:
        room_requirements.append(
            _room_requirement(
                project_id=confirmed.project_id,
                room_type="parking",
                quantity=missing_parking,
                floor_preference=0,
                ordinal=ordinal,
            )
        )

    if not room_requirements:
        raise UnsupportedConfirmedRequirement(
            "At least one confirmed room requirement is required."
        )

    assumptions = [
        {
            "id": str(_stable_id(confirmed.project_id, "profile-assumption")),
            "code": "PHASE24B_PROFILE_DEFAULTS",
            "description": (
                "User explicitly accepted deterministic architectural generation "
                f"profile {PROFILE_VERSION} for room minima and runtime settings."
            ),
            "source": "DOCUMENTED_DEFAULT",
            "confirmed_by_user": True,
            "affected_entity_ids": [],
        }
    ]

    payload: dict[str, object] = {
        "plot_boundary": polygon,
        "buildable_area": {
            "polygon": polygon,
            "setbacks": [],
        },
        "room_requirements": room_requirements,
        "floor_id": str(_stable_id(confirmed.project_id, "floor:0")),
        "floor_name": "Ground Floor",
        "floor_index": 0,
        "elevation_mm": 0,
        "floor_to_floor_mm": 3000,
        "wall_config": {
            "external_wall_thickness_mm": 230,
            "internal_wall_thickness_mm": 115,
            "wall_height_mm": 3000,
        },
        "planner_config": {
            "solver_step_mm": 1,
            "max_time_ms": 5000,
            "max_conflicts": 100000,
            "num_search_workers": 1,
            "random_seed": 0,
        },
        "validation_config": {
            "tiny_sliver_area_mm2": 10000,
            "door_clearance_margin_mm": 50,
        },
        "openings": [],
        "stairs": [],
        "swing_contexts": [],
        "assumptions": assumptions,
    }

    request = ArchitecturalGenerationRequest.model_validate_json(
        json.dumps(payload)
    )
    notices = (
        "True-North/road/facing are confirmed context but are not inputs in the "
        "inspected Phase 16 generation request.",
        "Frozen Vastu evaluation must run in the final Phase 24 binding.",
    )
    return CompiledGeneration(
        request=request,
        profile_version=PROFILE_VERSION,
        notices=notices,
    )


def run_compiled_generation(
    compiled: CompiledGeneration,
) -> ArchitecturalGenerationResult:
    return generate_architectural_plan(compiled.request)
