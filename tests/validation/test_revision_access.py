from uuid import UUID

import pytest

from ai_vastu.plan_schema import Assumption, AssumptionSource, RoomType, WallCategory
from ai_vastu.validation.revision_access import validate_changed_revision_access
from tests.architectural_geometry.test_circulation import _door, _floor, _room, _wall
from tests.plan_schema.sample import sample_plan


def document():
    living = _room(1, RoomType.LIVING, 0, 0, 4000, 4000)
    bedroom = _room(2, RoomType.BEDROOM, 4000, 0, 8000, 4000)
    entry = _wall(1, 0, 0, 4000, 0, WallCategory.EXTERNAL)
    shared = _wall(2, 4000, 0, 4000, 4000, WallCategory.INTERNAL)
    floor = _floor((living, bedroom), (entry, shared), (_door(1, entry), _door(2, shared)))
    return sample_plan().model_copy(update={
        "floors": (floor,), "content_hash": None,
        "assumptions": (Assumption(id=UUID(int=500), code="PHASE24_CONFIRMED_CONTEXT",
            description="Confirmed fixture", source=AssumptionSource.USER,
            confirmed_by_user=True),),
    })


def test_changed_geometry_cannot_disconnect_required_room():
    prior = document()
    floor = prior.floors[0]
    changed = prior.model_copy(update={"floors": (floor.model_copy(update={
        "openings": (floor.openings[0],),
    }),)})
    with pytest.raises(ValueError, match="CIRCULATION_DISCONNECTED"):
        validate_changed_revision_access(prior=prior, document=changed)


def test_bedroom_swap_cannot_provide_public_room_access():
    prior = document()
    first, second = prior.floors[0].rooms
    changed = prior.model_copy(update={"floors": (prior.floors[0].model_copy(update={
        "rooms": (first.model_copy(update={"room_type": RoomType.BEDROOM}),
                  second.model_copy(update={"room_type": RoomType.LIVING})),
    }),)})
    with pytest.raises(ValueError, match="CIRCULATION_DISCONNECTED"):
        validate_changed_revision_access(prior=prior, document=changed)


def test_legacy_identical_snapshot_can_be_saved_without_requalification():
    prior = document()
    prior = prior.model_copy(update={"floors": (prior.floors[0].model_copy(update={
        "openings": (),
    }),)})
    snapshot = prior.model_copy(update={"revision_id": UUID(int=900)})
    validate_changed_revision_access(prior=prior, document=snapshot)


def test_saved_parking_cannot_be_removed_or_made_shallow():
    prior = document()
    floor = prior.floors[0]
    parking = _room(3, RoomType.PARKING, 0, 4000, 4000, 10000)
    prior = prior.model_copy(update={"floors": (floor.model_copy(update={
        "rooms": (*floor.rooms, parking),
    }),)})
    removed = prior.model_copy(update={"floors": (floor,)})
    with pytest.raises(ValueError, match="VEHICLE_ACCESS_INVALID"):
        validate_changed_revision_access(prior=prior, document=removed)
    shallow = parking.model_copy(update={"polygon": _room(
        3, RoomType.PARKING, 0, 4000, 4000, 7000,
    ).polygon})
    changed = prior.model_copy(update={"floors": (floor.model_copy(update={
        "rooms": (*floor.rooms, shallow),
    }),)})
    with pytest.raises(ValueError, match="VEHICLE_ACCESS_INVALID"):
        validate_changed_revision_access(prior=prior, document=changed)


def test_valid_physical_change_is_allowed():
    prior = document()
    floor = prior.floors[0]
    opening = floor.openings[1].model_copy(update={"width_mm": 900})
    changed = prior.model_copy(update={"floors": (floor.model_copy(update={
        "openings": (floor.openings[0], opening),
    }),)})
    validate_changed_revision_access(prior=prior, document=changed)
