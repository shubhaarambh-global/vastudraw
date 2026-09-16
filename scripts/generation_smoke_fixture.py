from uuid import UUID

from ai_vastu.architectural_geometry import WallBuildConfig
from ai_vastu.generation import ArchitecturalGenerationRequest
from ai_vastu.plan_schema import BuildableArea, IntPoint, IntPolygon, RoomRequirement, RoomType
from ai_vastu.solver import PlannerConfig
from ai_vastu.validation import ValidationConfig


def _rectangle(width_mm: int, depth_mm: int) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=0, y_mm=0),
            IntPoint(x_mm=width_mm, y_mm=0),
            IntPoint(x_mm=width_mm, y_mm=depth_mm),
            IntPoint(x_mm=0, y_mm=depth_mm),
        )
    )


def generation_request() -> ArchitecturalGenerationRequest:
    boundary = _rectangle(9000, 7000)
    requirements = (
        RoomRequirement(
            id=UUID("b6000000-0000-0000-0000-000000000001"),
            room_type=RoomType.LIVING,
            min_width_mm=3000,
            preferred_width_mm=3600,
            max_width_mm=4500,
            min_depth_mm=3000,
            preferred_depth_mm=3600,
            max_depth_mm=4500,
            min_area_mm2=10_000_000,
            user_priority=80,
        ),
        RoomRequirement(
            id=UUID("b6000000-0000-0000-0000-000000000002"),
            room_type=RoomType.DINING,
            min_width_mm=2700,
            preferred_width_mm=3000,
            max_width_mm=4000,
            min_depth_mm=2700,
            preferred_depth_mm=3000,
            max_depth_mm=4000,
            min_area_mm2=8_000_000,
            user_priority=70,
        ),
    )
    return ArchitecturalGenerationRequest(
        plot_boundary=boundary,
        buildable_area=BuildableArea(polygon=boundary),
        room_requirements=requirements,
        floor_id=UUID("b6000000-0000-0000-0000-000000000010"),
        floor_name="Ground Floor",
        floor_index=0,
        elevation_mm=0,
        floor_to_floor_mm=3300,
        wall_config=WallBuildConfig(
            external_wall_thickness_mm=230,
            internal_wall_thickness_mm=115,
            wall_height_mm=3000,
        ),
        planner_config=PlannerConfig(
            solver_step_mm=100,
            max_time_ms=5000,
            max_conflicts=100000,
            random_seed=19,
        ),
        validation_config=ValidationConfig(
            tiny_sliver_area_mm2=10_000,
            door_clearance_margin_mm=50,
        ),
    )
