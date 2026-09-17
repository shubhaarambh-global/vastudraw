from __future__ import annotations

from uuid import UUID

from ai_vastu.requirements.models import (
    ConfirmedRequirements,
    ConfirmedRoomRequirement,
    Direction,
    VastuMode,
)


def confirmed() -> ConfirmedRequirements:
    return ConfirmedRequirements(
        draft_id=UUID("10000000-0000-0000-0000-000000000026"),
        user_id=UUID("20000000-0000-0000-0000-000000000026"),
        project_id=UUID("30000000-0000-0000-0000-000000000026"),
        user_confirmed=True,
        plot_width_mm=9144,
        plot_depth_mm=15240,
        north_rotation_deg=0,
        road_side=Direction.E,
        entrance_facing=None,
        floor_count=1,
        bedroom_count=2,
        parking_count=1,
        vastu_mode=VastuMode.BALANCED,
        rooms=[
            ConfirmedRoomRequirement(room_type="bedroom", quantity=2),
            ConfirmedRoomRequirement(room_type="living room"),
            ConfirmedRoomRequirement(room_type="dining area"),
            ConfirmedRoomRequirement(room_type="kitchen"),
            ConfirmedRoomRequirement(room_type="common toilet"),
        ],
    )
