from __future__ import annotations

from uuid import UUID

import pytest

from ai_vastu.architectural_brain.candidate_dedup import spatially_equivalent
from ai_vastu.requirements.finalization import (
    Phase24FinalizationError,
    _validate_building_program,
    build_canonical_plan_document,
)
from ai_vastu.requirements.generation_adapter import (
    compile_confirmed_requirements,
    run_compiled_generation,
)
from tests.exporting.helpers import export_plan, rectangle
from tests.requirements.test_phase26c4a_residential_planning import _confirmed


def _building(floor_count: int):
    base = _confirmed(bedroom_count=max(2, floor_count))
    confirmed = base.model_copy(
        update={
            "floor_count": floor_count,
            "rooms": tuple(
                item.model_copy(update={"floor_preference": None}) for item in base.rooms
            ),
        }
    )
    compiled = compile_confirmed_requirements(confirmed)
    result = run_compiled_generation(compiled)
    return confirmed, compiled, result


def test_ground_only_remains_one_floor_and_canonical() -> None:
    confirmed, compiled, result = _building(1)
    assert result.disposition.value == "ACCEPTED"
    canonical = build_canonical_plan_document(
        confirmed=confirmed,
        compiled=compiled,
        result=result,
    )
    assert len(canonical.document.floors) == 1
    assert canonical.document.floors[0].index == 0


@pytest.mark.parametrize("floor_count", (2, 3, 4))
def test_supported_floor_counts_create_complete_canonical_buildings(floor_count: int) -> None:
    confirmed, compiled, result = _building(floor_count)
    assert result.disposition.value == "ACCEPTED"
    assert len(result.floor_results) == floor_count
    canonical = build_canonical_plan_document(
        confirmed=confirmed,
        compiled=compiled,
        result=result,
    )
    assert [floor.index for floor in canonical.document.floors] == list(range(floor_count))


def test_program_distribution_assigns_each_requested_room_exactly_once() -> None:
    _confirmed_building, compiled, result = _building(3)
    assert result.disposition.value == "ACCEPTED"
    expected = {
        item.room_type.value: sum(
            requirement.quantity
            for requirement in compiled.request.room_requirements
            if requirement.room_type is item.room_type
        )
        for item in compiled.request.room_requirements
    }
    actual = {}
    for floor in result.floor_results:
        for room in floor.geometry_result.floor.rooms:
            actual[room.room_type.value] = actual.get(room.room_type.value, 0) + 1
    assert actual == expected
    assert all(
        room.room_type.value != "parking"
        for floor in result.floor_results[1:]
        for room in floor.geometry_result.floor.rooms
    )


def test_program_completeness_rejects_missing_and_duplicate_rooms() -> None:
    confirmed, compiled, result = _building(2)
    floors = tuple(item.geometry_result.floor for item in result.floor_results)
    missing = floors[1].model_copy(update={"rooms": floors[1].rooms[:-1]})
    duplicate = floors[1].model_copy(
        update={"rooms": (*floors[1].rooms, floors[1].rooms[0])}
    )

    with pytest.raises(Phase24FinalizationError, match="BUILDING_PROGRAM_INCOMPLETE"):
        _validate_building_program(
            confirmed=confirmed,
            compiled=compiled,
            floors=(floors[0], missing),
        )
    with pytest.raises(Phase24FinalizationError, match="BUILDING_PROGRAM_INCOMPLETE"):
        _validate_building_program(
            confirmed=confirmed,
            compiled=compiled,
            floors=(floors[0], duplicate),
        )


def test_multifloor_topology_partitions_remain_floor_specific() -> None:
    _, compiled, _ = _building(2)
    assert {item.room_type.value for item in compiled.request.floor_requirements[0]} != {
        item.room_type.value for item in compiled.request.floor_requirements[1]
    }
    assert all(
        item.floor_preference == (floor_index,)
        for floor_index, floor in enumerate(compiled.request.floor_requirements)
        for item in floor
    )


def test_multifloor_dedup_includes_upper_floor_geometry() -> None:
    base = export_plan()
    upper = base.floors[0].model_copy(
        update={
            "id": UUID("aaaaaaaa-0000-0000-0000-000000000001"),
            "index": 1,
            "name": "First Floor",
        }
    )
    first = base.model_copy(update={"floors": (base.floors[0], upper)})
    jittered_upper_room = upper.rooms[0].model_copy(
        update={"polygon": rectangle(50, 0, 5_050, 8_000)}
    )
    jittered = first.model_copy(
        update={
            "floors": (
                first.floors[0],
                upper.model_copy(update={"rooms": (jittered_upper_room, *upper.rooms[1:])}),
            )
        }
    )
    material_upper_room = upper.rooms[0].model_copy(
        update={"polygon": rectangle(700, 0, 5_700, 8_000)}
    )
    material = first.model_copy(
        update={
            "floors": (
                first.floors[0],
                upper.model_copy(update={"rooms": (material_upper_room, *upper.rooms[1:])}),
            )
        }
    )
    assert spatially_equivalent(first, jittered)
    assert not spatially_equivalent(first, material)