from __future__ import annotations

from uuid import UUID

from ai_vastu.constraints import (
    AdjacencyProhibitionConstraint,
    ConstraintCompilerInput,
    ConstraintOrigin,
    compile_constraints,
)
from ai_vastu.plan_schema import (
    BuildableArea,
    RoomRequirement,
    RoomType,
)

from .helpers import rectangle


def test_puja_sanitary_separation_is_compiled_as_architectural_invariant() -> None:
    puja = RoomRequirement(
        id=UUID("74000000-0000-0000-0000-000000000001"),
        room_type=RoomType.PUJA,
        min_width_mm=1_200,
        min_depth_mm=1_200,
        min_area_mm2=1_440_000,
    )

    toilet = RoomRequirement(
        id=UUID("74000000-0000-0000-0000-000000000002"),
        room_type=RoomType.COMMON_TOILET,
        min_width_mm=1_200,
        min_depth_mm=1_800,
        min_area_mm2=2_160_000,
    )

    problem = compile_constraints(
        ConstraintCompilerInput(
            buildable_area=BuildableArea(
                polygon=rectangle(
                    6_000,
                    6_000,
                )
            ),
            available_floor_indices=(0,),
            room_requirements=(
                puja,
                toilet,
            ),
        )
    )

    puja_id = next(room.id for room in problem.room_instances if room.room_type is RoomType.PUJA)

    constraints = tuple(
        item
        for item in problem.hard_constraints
        if (
            isinstance(
                item,
                AdjacencyProhibitionConstraint,
            )
            and item.room_instance_id == puja_id
            and item.target_room_type is RoomType.COMMON_TOILET
        )
    )

    assert len(constraints) == 1

    assert constraints[0].origin is ConstraintOrigin.ARCHITECTURAL_INVARIANT
