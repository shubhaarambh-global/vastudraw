from uuid import UUID

from ai_vastu.constraints import ConstraintCompilerInput
from ai_vastu.plan_schema import (
    AdjacencyPreference,
    AdjacencyProhibition,
    Assumption,
    AssumptionSource,
    BuildableArea,
    IntPoint,
    IntPolygon,
    RoomRequirement,
    RoomType,
)


def rectangle(width_mm: int = 10_000, depth_mm: int = 12_000) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=0, y_mm=0),
            IntPoint(x_mm=width_mm, y_mm=0),
            IntPoint(x_mm=width_mm, y_mm=depth_mm),
            IntPoint(x_mm=0, y_mm=depth_mm),
        )
    )


def kitchen_requirement(*, quantity: int = 1) -> RoomRequirement:
    return RoomRequirement(
        id=UUID("61000000-0000-0000-0000-000000000001"),
        room_type=RoomType.KITCHEN,
        quantity=quantity,
        floor_preference=(0,),
        min_width_mm=2_400,
        preferred_width_mm=3_000,
        max_width_mm=4_500,
        min_depth_mm=2_400,
        preferred_depth_mm=3_200,
        max_depth_mm=4_500,
        min_area_mm2=7_000_000,
        preferred_area_mm2=10_000_000,
        max_area_mm2=18_000_000,
        adjacency_preferences=(
            AdjacencyPreference(
                target_room_type=RoomType.DINING,
                weight=90,
                max_gap_mm=300,
                min_shared_length_mm=1_200,
            ),
        ),
        privacy_priority=30,
        daylight_priority=75,
        ventilation_priority=90,
        user_priority=85,
    )


def dining_requirement() -> RoomRequirement:
    return RoomRequirement(
        id=UUID("61000000-0000-0000-0000-000000000002"),
        room_type=RoomType.DINING,
        min_width_mm=2_700,
        preferred_width_mm=3_300,
        min_depth_mm=2_700,
        preferred_depth_mm=3_300,
        min_area_mm2=8_000_000,
        preferred_area_mm2=11_000_000,
        adjacency_prohibitions=(
            AdjacencyProhibition(target_room_type=RoomType.SERVANT_TOILET, hard=True),
        ),
        user_priority=70,
    )


def explicit_assumption() -> Assumption:
    return Assumption(
        id=UUID("61000000-0000-0000-0000-000000000100"),
        code="TEST-ASSUMPTION",
        description="Synthetic explicit assumption for compiler tests.",
        source=AssumptionSource.DOCUMENTED_DEFAULT,
        confirmed_by_user=False,
    )


def compiler_input(
    *,
    requirements: tuple[RoomRequirement, ...] | None = None,
    floors: tuple[int, ...] = (0,),
    with_assumption: bool = False,
    width_mm: int = 10_000,
    depth_mm: int = 12_000,
) -> ConstraintCompilerInput:
    return ConstraintCompilerInput(
        buildable_area=BuildableArea(polygon=rectangle(width_mm, depth_mm)),
        available_floor_indices=floors,
        room_requirements=(
            requirements
            if requirements is not None
            else (kitchen_requirement(), dining_requirement())
        ),
        assumptions=(explicit_assumption(),) if with_assumption else (),
    )
