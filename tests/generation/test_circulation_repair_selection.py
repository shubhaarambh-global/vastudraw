from __future__ import annotations

from uuid import UUID

from ai_vastu.architectural_geometry import ArchitecturalGeometryResult, WallBuildConfig
from ai_vastu.constraints import ConstraintCompilerInput, compile_constraints
from ai_vastu.generation.models import ArchitecturalGenerationRequest, CirculationGenerationConfig
from ai_vastu.generation.service import _circulation_repair_candidates
from ai_vastu.plan_schema import (
    AxisSegment,
    BuildableArea,
    Floor,
    IntPoint,
    IntPolygon,
    RoomGeometry,
    RoomRequirement,
    RoomType,
    Wall,
    WallCategory,
)
from ai_vastu.solver import PlannerConfig, ResidentialPlanningConfig
from ai_vastu.validation import ValidationConfig


def _rectangle(x0: int, y0: int, x1: int, y1: int) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=x0, y_mm=y0),
            IntPoint(x_mm=x1, y_mm=y0),
            IntPoint(x_mm=x1, y_mm=y1),
            IntPoint(x_mm=x0, y_mm=y1),
        )
    )


def test_repair_candidate_connects_nearest_reachable_and_disconnected_rooms() -> None:
    plot = _rectangle(0, 0, 10_000, 8_000)
    requirements = (
        RoomRequirement(
            id=UUID(int=101),
            room_type=RoomType.LIVING,
            min_width_mm=3_000,
            min_depth_mm=3_000,
            min_area_mm2=9_000_000,
        ),
        RoomRequirement(
            id=UUID(int=102),
            room_type=RoomType.BEDROOM,
            min_width_mm=3_000,
            min_depth_mm=3_000,
            min_area_mm2=9_000_000,
        ),
    )
    problem = compile_constraints(
        ConstraintCompilerInput(
            buildable_area=BuildableArea(polygon=plot),
            available_floor_indices=(0,),
            room_requirements=requirements,
        )
    )
    room_ids = {room.room_type: room.id for room in problem.room_instances}
    living_id = room_ids[RoomType.LIVING]
    bedroom_id = room_ids[RoomType.BEDROOM]

    living = RoomGeometry(
        id=living_id,
        room_type=RoomType.LIVING,
        polygon=_rectangle(0, 0, 4_000, 4_000),
    )
    bedroom = RoomGeometry(
        id=bedroom_id,
        room_type=RoomType.BEDROOM,
        polygon=_rectangle(5_000, 0, 9_000, 4_000),
    )
    entry_wall = Wall(
        id=UUID(int=201),
        axis=AxisSegment(
            start=IntPoint(x_mm=0, y_mm=0),
            end=IntPoint(x_mm=4_000, y_mm=0),
        ),
        thickness_mm=230,
        height_mm=3_000,
        category=WallCategory.EXTERNAL,
    )
    geometry = ArchitecturalGeometryResult(
        source_problem_hash=problem.content_hash or problem.compute_content_hash(),
        source_planner_hash="0" * 64,
        floor=Floor(
            id=UUID(int=301),
            index=0,
            name="Ground",
            elevation_mm=0,
            floor_to_floor_mm=3_000,
            rooms=(living, bedroom),
            walls=(entry_wall,),
        ),
    )
    request = ArchitecturalGenerationRequest(
        plot_boundary=plot,
        buildable_area=BuildableArea(polygon=plot),
        room_requirements=requirements,
        floor_id=UUID(int=301),
        floor_name="Ground",
        floor_index=0,
        elevation_mm=0,
        floor_to_floor_mm=3_000,
        wall_config=WallBuildConfig(
            external_wall_thickness_mm=230,
            internal_wall_thickness_mm=115,
            wall_height_mm=3_000,
        ),
        planner_config=PlannerConfig(
            solver_step_mm=100,
            residential_planning=ResidentialPlanningConfig(enabled=True),
            max_time_ms=5_000,
            max_conflicts=100_000,
            random_seed=0,
        ),
        validation_config=ValidationConfig(
            tiny_sliver_area_mm2=10_000,
            door_clearance_margin_mm=50,
        ),
        circulation_config=CirculationGenerationConfig(
            auto_generate=True,
            internal_door_width_mm=800,
            external_door_width_mm=900,
            edge_margin_mm=100,
            door_height_mm=2_100,
        ),
    )

    candidates = _circulation_repair_candidates(
        geometry,
        request,
        problem,
        attempted_pairs=frozenset(),
    )

    assert candidates
    first = candidates[0]
    assert {first.first_room_id, first.second_room_id} == {living_id, bedroom_id}
    assert first.min_shared_length_mm == 1_000
