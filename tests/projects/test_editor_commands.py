from uuid import uuid4

import pytest
from pydantic import ValidationError
from tests.exporting.helpers import export_plan

from app.editor_command_routes import EditorCommandsRequest, RoomLockCommand, apply_room_locks


def test_room_lock_changes_metadata_only_and_preserves_immutable_base() -> None:
    base = export_plan().with_content_hash()
    before = base.model_dump_json()
    room = base.floors[0].rooms[0]
    changed = apply_room_locks(
        base, [RoomLockCommand(kind="ROOM_LOCK", room_id=room.id, locked=True)]
    )
    assert base.model_dump_json() == before
    assert changed.revision_id != base.revision_id
    assert changed.content_hash == changed.compute_content_hash()
    assert changed.floors[0].rooms[0].locked
    assert changed.floors[0].walls == base.floors[0].walls
    assert changed.floors[0].openings == base.floors[0].openings
    assert changed.floors[0].rooms[0].polygon == room.polygon
    unlocked = apply_room_locks(
        changed, [RoomLockCommand(kind="ROOM_LOCK", room_id=room.id, locked=False)]
    )
    assert unlocked.floors == base.floors


def test_unknown_and_noop_locks_fail_without_mutating_base() -> None:
    base = export_plan().with_content_hash()
    with pytest.raises(ValueError, match="Unknown"):
        apply_room_locks(base, [RoomLockCommand(kind="ROOM_LOCK", room_id=uuid4(), locked=True)])
    with pytest.raises(ValueError, match="No effective"):
        apply_room_locks(
            base,
            [RoomLockCommand(kind="ROOM_LOCK", room_id=base.floors[0].rooms[0].id, locked=False)],
        )
    assert base.content_hash == base.compute_content_hash()


@pytest.mark.parametrize(
    "command",
    [
        {"kind": "ROOM_LOCK", "room_id": str(uuid4()), "locked": 1},
        {
            "kind": "ROOM_SET_DIMENSION",
            "room_id": str(uuid4()),
            "axis": "WIDTH",
            "target_mm": 3500.5,
        },
        {
            "kind": "ROOM_SET_DIMENSION",
            "room_id": str(uuid4()),
            "axis": "WIDTH",
            "target_mm": "3500",
        },
        {"kind": "WALL_MOVE_PARALLEL", "wall_id": str(uuid4()), "delta_mm": 100},
    ],
)
def test_exact_editor_wire_rejects_unsafe_coercion_and_unsupported_geometry(command) -> None:
    with pytest.raises(ValidationError):
        EditorCommandsRequest.model_validate_json(
            __import__("json").dumps(
                {
                    "protocol_version": "1.0.0",
                    "project_id": str(uuid4()),
                    "base_revision_id": str(uuid4()),
                    "commands": [command],
                }
            )
        )
