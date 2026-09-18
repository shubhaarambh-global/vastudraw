from uuid import UUID, uuid4

import pytest

from ai_vastu.generation.models import ArchitecturalGenerationRequest
from ai_vastu.requirements.generation_adapter import (
    UnsupportedConfirmedRequirement,
    compile_confirmed_requirements,
)
from ai_vastu.requirements.models import (
    ConfirmedRequirements,
    ConfirmedRoomRequirement,
    Direction,
)

USER = UUID("11111111-1111-1111-1111-111111111111")
PROJECT = UUID("22222222-2222-2222-2222-222222222222")


def make_confirmed() -> ConfirmedRequirements:
    return ConfirmedRequirements(
        draft_id=uuid4(),
        user_id=USER,
        project_id=PROJECT,
        user_confirmed=True,
        plot_width_mm=9144,
        plot_depth_mm=15240,
        north_rotation_deg=0,
        road_side=Direction.E,
        floor_count=1,
        bedroom_count=2,
        parking_count=1,
        rooms=[
            ConfirmedRoomRequirement(room_type="bedroom", quantity=2),
            ConfirmedRoomRequirement(room_type="kitchen", quantity=1),
            ConfirmedRoomRequirement(room_type="puja", quantity=1),
        ],
    )


def test_compiler_targets_existing_generation_request_exactly() -> None:
    compiled = compile_confirmed_requirements(make_confirmed())
    assert isinstance(compiled.request, ArchitecturalGenerationRequest)
    assert compiled.request.plot_boundary.outer[1].x_mm == 9144
    assert compiled.request.plot_boundary.outer[2].y_mm == 15240
    assert compiled.request.planner_config.num_search_workers == 1
    assert compiled.request.planner_config.random_seed == 0
    assert len(compiled.request.room_requirements) == 5
    assert any(
        requirement.room_type.value == "lobby" for requirement in compiled.request.room_requirements
    )


def test_parking_count_adds_explicit_deterministic_room_requirement() -> None:
    compiled = compile_confirmed_requirements(make_confirmed())
    parking = [
        item for item in compiled.request.room_requirements if item.room_type.value == "parking"
    ]
    assert len(parking) == 1
    assert parking[0].quantity == 1


def test_unsupported_room_type_fails_closed() -> None:
    confirmed = make_confirmed().model_copy(
        update={
            "rooms": [
                ConfirmedRoomRequirement(room_type="cinema", quantity=1),
            ],
            "bedroom_count": 0,
            "parking_count": 0,
        }
    )
    with pytest.raises(UnsupportedConfirmedRequirement):
        compile_confirmed_requirements(confirmed)
