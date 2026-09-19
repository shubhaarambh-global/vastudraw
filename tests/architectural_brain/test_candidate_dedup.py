from tests.exporting.helpers import (
    export_plan,
    rectangle,
)

from ai_vastu.architectural_brain.candidate_dedup import (
    duplicate_reason_code,
    semantic_topology_signature,
    spatially_equivalent,
)
from ai_vastu.architectural_brain.models import (
    TopologyEdge,
)


def test_semantic_topology_ignores_order_and_weights() -> None:
    first = (
        TopologyEdge(
            source_room_type="living",
            target_room_type="kitchen",
            relation="NEAR",
            weight=60,
        ),
        TopologyEdge(
            source_room_type="living",
            target_room_type="bedroom",
            relation="AVOID",
            weight=90,
        ),
    )

    second = (
        TopologyEdge(
            source_room_type="bedroom",
            target_room_type="living",
            relation="AVOID",
            weight=100,
        ),
        TopologyEdge(
            source_room_type="kitchen",
            target_room_type="living",
            relation="NEAR",
            weight=75,
        ),
    )

    assert semantic_topology_signature(first) == semantic_topology_signature(second)


def test_different_relation_changes_topology_signature() -> None:
    near = (
        TopologyEdge(
            source_room_type="living",
            target_room_type="kitchen",
            relation="NEAR",
            weight=80,
        ),
    )

    adjacent = (
        TopologyEdge(
            source_room_type="living",
            target_room_type="kitchen",
            relation="ADJACENT",
            weight=80,
        ),
    )

    assert semantic_topology_signature(near) != semantic_topology_signature(adjacent)


def test_small_solver_jitter_does_not_create_fake_candidate() -> None:
    document = export_plan()
    floor = document.floors[0]

    room = floor.rooms[0]
    min_x = min(point.x_mm for point in room.polygon.outer)
    min_y = min(point.y_mm for point in room.polygon.outer)
    max_x = max(point.x_mm for point in room.polygon.outer)
    max_y = max(point.y_mm for point in room.polygon.outer)

    moved_room = room.model_copy(
        update={
            "polygon": rectangle(
                min_x + 50,
                min_y,
                max_x + 50,
                max_y,
            )
        }
    )

    moved_floor = floor.model_copy(
        update={
            "rooms": (
                moved_room,
                *floor.rooms[1:],
            )
        }
    )

    moved_document = document.model_copy(
        update={
            "floors": (moved_floor,),
            "content_hash": None,
        }
    )

    assert spatially_equivalent(
        document,
        moved_document,
    )


def test_material_room_change_creates_distinct_spatial_signature() -> None:
    document = export_plan()
    floor = document.floors[0]

    room = floor.rooms[0]
    min_x = min(point.x_mm for point in room.polygon.outer)
    min_y = min(point.y_mm for point in room.polygon.outer)
    max_x = max(point.x_mm for point in room.polygon.outer)
    max_y = max(point.y_mm for point in room.polygon.outer)

    moved_room = room.model_copy(
        update={
            "polygon": rectangle(
                min_x + 600,
                min_y,
                max_x + 600,
                max_y,
            )
        }
    )

    moved_floor = floor.model_copy(
        update={
            "rooms": (
                moved_room,
                *floor.rooms[1:],
            )
        }
    )

    moved_document = document.model_copy(
        update={
            "floors": (moved_floor,),
            "content_hash": None,
        }
    )

    assert not spatially_equivalent(
        document,
        moved_document,
    )


def test_same_spatial_and_topology_is_duplicate() -> None:
    assert (
        duplicate_reason_code(
            topology_signature="topology-a",
            spatial_signature="space-a",
            prior_topology_signature="topology-a",
            prior_spatial_signature="space-a",
        )
        == "DUPLICATE_TOPOLOGY_AND_SPATIAL"
    )


def test_same_spatial_with_different_topology_is_still_duplicate() -> None:
    assert (
        duplicate_reason_code(
            topology_signature="topology-b",
            spatial_signature="space-a",
            prior_topology_signature="topology-a",
            prior_spatial_signature="space-a",
        )
        == "DUPLICATE_SPATIAL_CANDIDATE"
    )


def test_same_topology_but_different_spatial_plan_is_allowed() -> None:
    assert (
        duplicate_reason_code(
            topology_signature="topology-a",
            spatial_signature="space-b",
            prior_topology_signature="topology-a",
            prior_spatial_signature="space-a",
        )
        is None
    )
