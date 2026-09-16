from uuid import UUID

from ai_vastu.constraints import ConstraintCompilerInput, compile_constraints
from ai_vastu.plan_schema import BuildableArea, IntPoint, IntPolygon, RoomRequirement, RoomType

polygon = IntPolygon(
    outer=(
        IntPoint(x_mm=0, y_mm=0),
        IntPoint(x_mm=12_000, y_mm=0),
        IntPoint(x_mm=12_000, y_mm=10_000),
        IntPoint(x_mm=0, y_mm=10_000),
    )
)
requirements = (
    RoomRequirement(
        id=UUID("63000000-0000-0000-0000-000000000001"),
        room_type=RoomType.LIVING,
        min_width_mm=3_000,
        min_depth_mm=3_000,
        min_area_mm2=12_000_000,
    ),
    RoomRequirement(
        id=UUID("63000000-0000-0000-0000-000000000002"),
        room_type=RoomType.BEDROOM,
        quantity=2,
        min_width_mm=2_700,
        min_depth_mm=3_000,
        min_area_mm2=9_000_000,
    ),
)
base = ConstraintCompilerInput(
    buildable_area=BuildableArea(polygon=polygon),
    available_floor_indices=(0, 1),
    room_requirements=requirements,
)
reordered = base.model_copy(update={"room_requirements": tuple(reversed(requirements))})
first = compile_constraints(base)
second = compile_constraints(reordered)
if first.content_hash != second.content_hash:
    raise SystemExit("Constraint compiler is not deterministic across requirement input order.")
if first.assumptions:
    raise SystemExit("Constraint compiler invented assumptions.")
print(
    "Constraint compiler deterministic: "
    f"rooms={len(first.room_instances)}, hard={len(first.hard_constraints)}, "
    f"soft={len(first.soft_constraints)}, hash={first.content_hash}"
)
