from __future__ import annotations

from uuid import UUID

from ai_vastu.architectural_geometry import (
    ArchitecturalGeometryRequest,
    OpeningBuildRequest,
    WallBuildConfig,
    build_architectural_geometry,
)
from ai_vastu.constraints import ConstraintCompilerInput, compile_constraints
from ai_vastu.plan_schema import (
    BuildableArea,
    DoorHinge,
    DoorSwing,
    IntPoint,
    IntPolygon,
    OpeningKind,
    RoomRequirement,
    RoomType,
    WallCategory,
)
from ai_vastu.solver import (
    PlannerConfig,
    PlannerResult,
    PlannerStatus,
    RoomPlacement,
    SolverRunMetadata,
)
from ai_vastu.validation import (
    ArchitecturalValidationRequest,
    DoorSwingContext,
    SwingSpace,
    ValidationConfig,
)


def rectangle(width_mm: int, depth_mm: int) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=0, y_mm=0),
            IntPoint(x_mm=width_mm, y_mm=0),
            IntPoint(x_mm=width_mm, y_mm=depth_mm),
            IntPoint(x_mm=0, y_mm=depth_mm),
        )
    )


def validation_request(
    *,
    min_width_mm: int = 3500,
    include_access: bool = True,
    include_swing_context: bool = True,
) -> ArchitecturalValidationRequest:
    requirements = (
        RoomRequirement(
            id=UUID("91000000-0000-0000-0000-000000000001"),
            room_type=RoomType.LIVING,
            min_width_mm=min_width_mm,
            max_width_mm=4000,
            min_depth_mm=3500,
            max_depth_mm=4000,
            min_area_mm2=12_000_000,
        ),
        RoomRequirement(
            id=UUID("91000000-0000-0000-0000-000000000002"),
            room_type=RoomType.DINING,
            min_width_mm=min_width_mm,
            max_width_mm=4000,
            min_depth_mm=3500,
            max_depth_mm=4000,
            min_area_mm2=12_000_000,
        ),
    )
    problem = compile_constraints(
        ConstraintCompilerInput(
            buildable_area=BuildableArea(polygon=rectangle(8000, 4000)),
            available_floor_indices=(0,),
            room_requirements=requirements,
        )
    )
    room_ids = {item.requirement_id: item.id for item in problem.room_instances}
    placements = (
        RoomPlacement(
            room_instance_id=room_ids[requirements[0].id],
            room_type=RoomType.LIVING,
            floor_index=0,
            x_mm=0,
            y_mm=0,
            width_mm=4000,
            depth_mm=4000,
            area_mm2=16_000_000,
        ),
        RoomPlacement(
            room_instance_id=room_ids[requirements[1].id],
            room_type=RoomType.DINING,
            floor_index=0,
            x_mm=4000,
            y_mm=0,
            width_mm=4000,
            depth_mm=4000,
            area_mm2=16_000_000,
        ),
    )
    planner_config = PlannerConfig(
        solver_step_mm=100,
        max_time_ms=1000,
        max_conflicts=1000,
        random_seed=1,
    )
    planner = PlannerResult(
        status=PlannerStatus.OPTIMAL,
        metadata=SolverRunMetadata(
            solver_version="phase9-fixture",
            problem_hash=problem.compute_content_hash(),
            config=planner_config,
        ),
        placements=placements,
        objective_penalty=0,
    ).with_content_hash()
    base_request = ArchitecturalGeometryRequest(
        problem=problem,
        planner_result=planner,
        floor_id=UUID("91000000-0000-0000-0000-000000000010"),
        floor_name="Ground Floor",
        elevation_mm=0,
        floor_to_floor_mm=3300,
        wall_config=WallBuildConfig(
            external_wall_thickness_mm=230,
            internal_wall_thickness_mm=115,
            wall_height_mm=3000,
        ),
    )
    base_geometry = build_architectural_geometry(base_request)

    openings: tuple[OpeningBuildRequest, ...] = ()
    swing_contexts: tuple[DoorSwingContext, ...] = ()
    if include_access:
        living_id = placements[0].room_instance_id
        external_wall = next(
            wall
            for wall in base_geometry.floor.walls
            if wall.category is WallCategory.EXTERNAL
            and wall.axis.start.x_mm == 0
            and wall.axis.end.x_mm == 0
        )
        shared_wall = next(
            wall
            for wall in base_geometry.floor.walls
            if wall.category is WallCategory.INTERNAL
            and wall.axis.start.x_mm == 4000
            and wall.axis.end.x_mm == 4000
        )
        exterior_door = OpeningBuildRequest(
            wall_id=external_wall.id,
            kind=OpeningKind.DOOR,
            offset_from_wall_start_mm=1000,
            width_mm=900,
            height_mm=2100,
            sill_height_mm=0,
            hinge=DoorHinge.LEFT,
            swing=DoorSwing.IN,
        )
        internal_opening = OpeningBuildRequest(
            wall_id=shared_wall.id,
            kind=OpeningKind.OPENING,
            offset_from_wall_start_mm=1500,
            width_mm=1000,
            height_mm=2200,
            sill_height_mm=0,
        )
        openings = (exterior_door, internal_opening)
        geometry_request = base_request.model_copy(update={"openings": openings})
        geometry = build_architectural_geometry(geometry_request)
        door = next(item for item in geometry.floor.openings if item.kind is OpeningKind.DOOR)
        if include_swing_context:
            swing_contexts = (
                DoorSwingContext(
                    opening_id=door.id,
                    swing_space=SwingSpace.ROOM,
                    room_id=living_id,
                ),
            )
    else:
        geometry = base_geometry

    return ArchitecturalValidationRequest(
        plot_boundary=rectangle(8000, 4000),
        problem=problem,
        geometry=geometry,
        config=ValidationConfig(
            tiny_sliver_area_mm2=100_000,
            door_clearance_margin_mm=100,
        ),
        swing_contexts=swing_contexts,
    )
