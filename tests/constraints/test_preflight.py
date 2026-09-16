from uuid import UUID

import pytest

from ai_vastu.constraints import (
    ConstraintCompilerInput,
    ConstraintConflictError,
    ConstraintInfeasibleError,
    compile_constraints,
)
from ai_vastu.plan_schema import (
    AdjacencyPreference,
    AdjacencyProhibition,
    BuildableArea,
    RoomRequirement,
    RoomType,
)

from .helpers import compiler_input, dining_requirement, kitchen_requirement, rectangle


def test_unavailable_floor_preference_fails_closed() -> None:
    kitchen = kitchen_requirement().model_copy(update={"floor_preference": (3,)})

    with pytest.raises(ConstraintConflictError, match="unavailable floor"):
        compile_constraints(compiler_input(requirements=(kitchen, dining_requirement())))


def test_preferred_and_prohibited_same_target_fails_closed() -> None:
    kitchen = kitchen_requirement().model_copy(
        update={
            "adjacency_prohibitions": (
                AdjacencyProhibition(target_room_type=RoomType.DINING, hard=True),
            )
        }
    )

    with pytest.raises(ConstraintConflictError, match="both prefers and prohibits"):
        compile_constraints(compiler_input(requirements=(kitchen, dining_requirement())))


def test_adjacency_preference_to_absent_room_type_fails_closed() -> None:
    kitchen = kitchen_requirement()

    with pytest.raises(ConstraintConflictError, match="unavailable room type"):
        compile_constraints(compiler_input(requirements=(kitchen,)))


def test_minimum_dimensions_cannot_already_exceed_max_area() -> None:
    room = RoomRequirement(
        id=UUID("62000000-0000-0000-0000-000000000001"),
        room_type=RoomType.BEDROOM,
        min_width_mm=4_000,
        min_depth_mm=4_000,
        min_area_mm2=10_000_000,
        max_area_mm2=12_000_000,
    )

    with pytest.raises(ConstraintInfeasibleError, match="minimum width/depth"):
        compile_constraints(compiler_input(requirements=(room,)))


def test_maximum_dimensions_must_be_able_to_reach_min_area() -> None:
    room = RoomRequirement(
        id=UUID("62000000-0000-0000-0000-000000000002"),
        room_type=RoomType.BEDROOM,
        min_width_mm=2_000,
        max_width_mm=2_500,
        min_depth_mm=2_000,
        max_depth_mm=2_500,
        min_area_mm2=8_000_000,
    )

    with pytest.raises(ConstraintInfeasibleError, match="cannot reach min area"):
        compile_constraints(compiler_input(requirements=(room,)))


def test_total_minimum_area_preflight_uses_all_floors() -> None:
    large = RoomRequirement(
        id=UUID("62000000-0000-0000-0000-000000000003"),
        room_type=RoomType.LIVING,
        quantity=2,
        min_width_mm=5_000,
        min_depth_mm=5_000,
        min_area_mm2=30_000_000,
    )
    input_data = ConstraintCompilerInput(
        buildable_area=BuildableArea(polygon=rectangle(5_000, 5_000)),
        available_floor_indices=(0, 1),
        room_requirements=(large,),
    )

    with pytest.raises(ConstraintInfeasibleError, match="total buildable floor capacity"):
        compile_constraints(input_data)


def test_soft_prohibition_without_target_is_reported_as_vacuous_not_invented() -> None:
    dining = dining_requirement()
    result = compile_constraints(compiler_input(requirements=(dining,)))

    assert len(result.notices) == 1
    assert result.notices[0].code == "VACUOUS_ADJACENCY_PROHIBITION"


def test_duplicate_adjacency_preference_targets_are_rejected() -> None:
    preference = AdjacencyPreference(target_room_type=RoomType.DINING, weight=80)
    kitchen = kitchen_requirement().model_copy(
        update={"adjacency_preferences": (preference, preference)}
    )

    with pytest.raises(ConstraintConflictError, match="duplicate adjacency preferences"):
        compile_constraints(compiler_input(requirements=(kitchen, dining_requirement())))
