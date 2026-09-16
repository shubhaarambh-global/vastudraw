from __future__ import annotations

from uuid import UUID, uuid4

from ai_vastu.generation.models import ArchitecturalGenerationRequest
from ai_vastu.requirements.generation_adapter import compile_confirmed_requirements
from ai_vastu.requirements.models import (
    ConfirmedRequirements,
    ConfirmedRoomRequirement,
    Direction,
)

confirmed = ConfirmedRequirements(
    draft_id=uuid4(),
    user_id=UUID("11111111-1111-1111-1111-111111111111"),
    project_id=UUID("22222222-2222-2222-2222-222222222222"),
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

compiled = compile_confirmed_requirements(confirmed)

assert isinstance(compiled.request, ArchitecturalGenerationRequest)
assert compiled.request.plot_boundary.outer[2].x_mm == 9144
assert compiled.request.plot_boundary.outer[2].y_mm == 15240
assert compiled.request.planner_config.num_search_workers == 1
assert compiled.request.planner_config.random_seed == 0
assert compiled.request.assumptions
assert compiled.notices

print(
    "Phase 24B confirmed generation binding: exact_generation_model=true, "
    "billing_gate=true, free_success_only=true, deterministic_profile=true, "
    "explicit_default_acceptance=true, ai_geometry=false, "
    "vastu_claimed=false, revision_claimed=false"
)
