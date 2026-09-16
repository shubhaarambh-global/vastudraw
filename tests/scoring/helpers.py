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
    AdjacencyPreference,
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
from ai_vastu.scoring import ScoringCandidate
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
    validate_architectural_geometry,
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


def problem():
    requirements = (
        RoomRequirement(
            id=UUID("a1000000-0000-0000-0000-000000000001"),
            room_type=RoomType.LIVING,
            min_width_mm=3500,
            preferred_width_mm=4000,
            max_width_mm=4000,
            min_depth_mm=3500,
            preferred_depth_mm=4000,
            max_depth_mm=4000,
            min_area_mm2=12_000_000,
            preferred_area_mm2=16_000_000,
            adjacency_preferences=(
                AdjacencyPreference(
                    target_room_type=RoomType.DINING,
                    weight=80,
                    max_gap_mm=0,
                    min_shared_length_mm=3000,
                ),
            ),
            user_priority=80,
        ),
        RoomRequirement(
            id=UUID("a1000000-0000-0000-0000-000000000002"),
            room_type=RoomType.DINING,
            min_width_mm=3500,
            preferred_width_mm=4000,
            max_width_mm=4000,
            min_depth_mm=3500,
            preferred_depth_mm=4000,
            max_depth_mm=4000,
            min_area_mm2=12_000_000,
            preferred_area_mm2=16_000_000,
            user_priority=70,
        ),
    )
    return compile_constraints(
        ConstraintCompilerInput(
            buildable_area=BuildableArea(polygon=rectangle(8000, 4000)),
            available_floor_indices=(0,),
            room_requirements=requirements,
        )
    )


def candidate(candidate_id: UUID, *, swapped: bool = False) -> ScoringCandidate:
    compiled = problem()
    instances = {item.room_type: item for item in compiled.room_instances}
    living_x = 4000 if swapped else 0
    dining_x = 0 if swapped else 4000
    placements = (
        RoomPlacement(
            room_instance_id=instances[RoomType.LIVING].id,
            room_type=RoomType.LIVING,
            floor_index=0,
            x_mm=living_x,
            y_mm=0,
            width_mm=4000,
            depth_mm=4000,
            area_mm2=16_000_000,
        ),
        RoomPlacement(
            room_instance_id=instances[RoomType.DINING].id,
            room_type=RoomType.DINING,
            floor_index=0,
            x_mm=dining_x,
            y_mm=0,
            width_mm=4000,
            depth_mm=4000,
            area_mm2=16_000_000,
        ),
    )
    config = PlannerConfig(
        solver_step_mm=100,
        max_time_ms=1000,
        max_conflicts=1000,
        random_seed=10,
    )
    planner = PlannerResult(
        status=PlannerStatus.OPTIMAL,
        metadata=SolverRunMetadata(
            solver_version="phase10-fixture",
            problem_hash=compiled.compute_content_hash(),
            config=config,
        ),
        placements=placements,
        objective_penalty=0,
    ).with_content_hash()

    base_request = ArchitecturalGeometryRequest(
        problem=compiled,
        planner_result=planner,
        floor_id=UUID("a1000000-0000-0000-0000-000000000010"),
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
    external_x = 8000 if swapped else 0
    exterior_wall = next(
        wall
        for wall in base_geometry.floor.walls
        if wall.category is WallCategory.EXTERNAL
        and wall.axis.start.x_mm == external_x
        and wall.axis.end.x_mm == external_x
    )
    shared_wall = next(
        wall
        for wall in base_geometry.floor.walls
        if wall.category is WallCategory.INTERNAL
        and wall.axis.start.x_mm == 4000
        and wall.axis.end.x_mm == 4000
    )
    geometry = build_architectural_geometry(
        base_request.model_copy(
            update={
                "openings": (
                    OpeningBuildRequest(
                        wall_id=exterior_wall.id,
                        kind=OpeningKind.DOOR,
                        offset_from_wall_start_mm=1000,
                        width_mm=900,
                        height_mm=2100,
                        sill_height_mm=0,
                        hinge=DoorHinge.LEFT,
                        swing=DoorSwing.IN,
                    ),
                    OpeningBuildRequest(
                        wall_id=shared_wall.id,
                        kind=OpeningKind.OPENING,
                        offset_from_wall_start_mm=1500,
                        width_mm=1000,
                        height_mm=2200,
                        sill_height_mm=0,
                    ),
                )
            }
        )
    )
    door = next(item for item in geometry.floor.openings if item.kind is OpeningKind.DOOR)
    validation = validate_architectural_geometry(
        ArchitecturalValidationRequest(
            plot_boundary=rectangle(8000, 4000),
            problem=compiled,
            geometry=geometry,
            config=ValidationConfig(
                tiny_sliver_area_mm2=100_000,
                door_clearance_margin_mm=100,
            ),
            swing_contexts=(
                DoorSwingContext(
                    opening_id=door.id,
                    swing_space=SwingSpace.ROOM,
                    room_id=instances[RoomType.LIVING].id,
                ),
            ),
        )
    )
    assert validation.report.valid
    return ScoringCandidate(
        candidate_id=candidate_id,
        planner_result=planner,
        geometry_result=geometry,
        validation_result=validation,
    )
