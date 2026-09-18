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
from ai_vastu.requirements.residential_planning import local_boundary_side


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
        raise UnsupportedConfirmedRequirement("Explicit bedroom requirements exceed bedroom_count.")
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
        raise UnsupportedConfirmedRequirement("Explicit parking requirements exceed parking_count.")
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
        ordinal += 1

    existing_types = {str(item["room_type"]) for item in room_requirements}
    circulation_types = {"lobby", "corridor", "foyer"}
    added_system_lobby = False
    if confirmed.bedroom_count >= 2 and not (existing_types & circulation_types):
        room_requirements.append(
            _room_requirement(
                project_id=confirmed.project_id,
                room_type="lobby",
                quantity=1,
                floor_preference=0,
                ordinal=ordinal,
            )
        )
        ordinal += 1
        added_system_lobby = True

    if not room_requirements:
        raise UnsupportedConfirmedRequirement(
            "At least one confirmed room requirement is required."
        )

    try:
        road_boundary_side = local_boundary_side(
            confirmed.road_side.value,
            north_rotation_deg=confirmed.north_rotation_deg,
        )
        entrance_boundary_side = local_boundary_side(
            (
                confirmed.entrance_facing.value
                if confirmed.entrance_facing is not None
                else confirmed.road_side.value
            ),
            north_rotation_deg=confirmed.north_rotation_deg,
        )
    except ValueError as exc:
        raise UnsupportedConfirmedRequirement(str(exc)) from exc

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
        },
        {
            "id": str(_stable_id(confirmed.project_id, "phase26c4a-residential-planning")),
            "code": "PHASE26C4A_RESIDENTIAL_PLANNING",
            "description": (
                "User accepted the V1 deterministic residential-planning profile: "
                "automatic room-envelope occupancy target, compactness optimization, "
                "road-connected parking, entrance-edge anchoring and deterministic "
                "circulation topology. The automatic occupancy target is a planning "
                "heuristic only and is not an FSI/FAR/setback or regulatory entitlement. "
                f"System circulation lobby added={added_system_lobby}."
            ),
            "source": "DOCUMENTED_DEFAULT",
            "confirmed_by_user": True,
            "affected_entity_ids": [],
        },
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
            "clearance_reserve_mm": 230,
            "residential_planning": {
                "enabled": True,
                "target_occupied_area_basis_points": 7000,
                "occupied_area_weight": 40,
                "room_area_balance_weight": 10,
                "compactness_weight": 40,
                "road_boundary_side": road_boundary_side.value,
                "entrance_boundary_side": entrance_boundary_side.value,
                "require_road_connected_parking": confirmed.parking_count > 0,
                "require_entrance_boundary_access": True,
            },
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
        "circulation_config": {
            "auto_generate": True,
            "internal_door_width_mm": 800,
            "external_door_width_mm": 900,
            "edge_margin_mm": 100,
            "door_height_mm": 2100,
        },
        "stairs": [],
        "swing_contexts": [],
        "assumptions": assumptions,
    }

    request = ArchitecturalGenerationRequest.model_validate_json(json.dumps(payload))
    notices = (
        "Phase 26C.4A compiles confirmed road/entrance directions into local "
        "rectangular boundary anchors for residential planning.",
        "Automatic occupied-area planning is a documented V1 heuristic and does "
        "not claim regulatory permissible construction area.",
        "Deterministic residential topology objectives are applied inside CP-SAT "
        "unless an explicit relationship already governs the same room pair.",
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
