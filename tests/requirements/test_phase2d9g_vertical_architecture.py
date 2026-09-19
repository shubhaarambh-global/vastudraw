from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import UUID

import pytest

from ai_vastu.architectural_brain.candidate_dedup import spatially_equivalent
from ai_vastu.architectural_brain.critic import critique_plan
from ai_vastu.architectural_brain.scoring import score_plan_document
from ai_vastu.architectural_geometry import (
    WetStackRelationship,
    build_circulation_graph,
    evaluate_wet_stacks,
    plan_vertical_architecture,
    validate_whole_building,
)
from ai_vastu.generation import generate_architectural_plan
from ai_vastu.multi_candidate import (
    default_candidate_strategies,
    run_multi_candidate_generation,
)
from ai_vastu.plan_schema import Floor, IntPoint, IntPolygon, PlanDocument, RoomType
from ai_vastu.requirements.finalization import build_canonical_plan_document
from ai_vastu.solver import PlannerSearchVariant
from tests.exporting.helpers import rectangle
from tests.requirements.test_phase2d9f_multifloor import _building

_CIRCULATION_CAPABLE = {
    RoomType.LOBBY,
    RoomType.CORRIDOR,
    RoomType.FOYER,
    RoomType.LIVING,
    RoomType.DRAWING,
    RoomType.DINING,
    RoomType.FAMILY_LOUNGE,
    RoomType.VERANDAH,
}


@pytest.fixture(scope="module")
def buildings() -> dict[int, tuple[Any, Any, Any]]:
    return {floor_count: _building(floor_count) for floor_count in (1, 2, 3, 4)}


def _floors(result: Any) -> tuple[Floor, ...]:
    return tuple(item.geometry_result.floor for item in result.floor_results)


def _expected_program(compiled: Any) -> Counter[str]:
    return Counter(
        requirement.room_type.value
        for requirement in compiled.request.room_requirements
        for _ in range(requirement.quantity)
    )


def _revalidate(
    compiled: Any,
    result: Any,
    floors: tuple[Floor, ...],
    *,
    expected_program: Counter[str] | None = None,
) -> Any:
    return validate_whole_building(
        floors=floors,
        expected_floor_count=compiled.request.floor_count,
        expected_program=expected_program or _expected_program(compiled),
        core_plan=result.vertical_core_plan,
        internal_door_width_mm=compiled.request.circulation_config.internal_door_width_mm,
        edge_margin_mm=compiled.request.circulation_config.edge_margin_mm,
    )


def _codes(validation: Any) -> set[str]:
    return {item.code for item in validation.diagnostics}


def _shift(polygon: IntPolygon, dx: int, dy: int) -> IntPolygon:
    return IntPolygon(
        outer=tuple(
            IntPoint(x_mm=point.x_mm + dx, y_mm=point.y_mm + dy)
            for point in polygon.outer
        )
    )


def _move_core(document: PlanDocument, dx: int, dy: int) -> PlanDocument:
    updated_floors = []
    for floor in document.floors:
        stair_room = next(room for room in floor.rooms if room.room_type is RoomType.STAIRCASE)
        footprint = _shift(stair_room.polygon, dx, dy)
        rooms = tuple(
            room.model_copy(update={"polygon": footprint})
            if room.id == stair_room.id
            else room
            for room in floor.rooms
        )
        stairs = tuple(stair.model_copy(update={"footprint": footprint}) for stair in floor.stairs)
        updated_floors.append(floor.model_copy(update={"rooms": rooms, "stairs": stairs}))
    return document.model_copy(update={"floors": tuple(updated_floors), "content_hash": None})


def test_ground_only_path_has_no_interfloor_stair(
    buildings: dict[int, tuple[Any, Any, Any]],
) -> None:
    confirmed, compiled, result = buildings[1]
    assert result.vertical_circulation_status == "GROUND_ONLY"
    assert result.vertical_core_plan is None
    assert result.floor_results == ()
    assert result.geometry_result.floor.stairs == ()
    assert all(
        room.room_type is not RoomType.STAIRCASE
        for room in result.geometry_result.floor.rooms
    )
    canonical = build_canonical_plan_document(
        confirmed=confirmed,
        compiled=compiled,
        result=result,
    )
    assert canonical.document.floors[0].stairs == ()


@pytest.mark.parametrize("floor_count", (2, 3, 4))
def test_multifloor_generation_has_one_continuous_real_core(
    buildings: dict[int, tuple[Any, Any, Any]],
    floor_count: int,
) -> None:
    _confirmed, _compiled, result = buildings[floor_count]
    assert result.disposition.value == "ACCEPTED"
    assert result.vertical_circulation_status == "VALIDATED"
    assert result.building_validation.accepted
    assert result.vertical_core_plan.served_floor_indices == tuple(range(floor_count))
    assert len(result.building_validation.circulation.vertical_transfers) == floor_count - 1

    footprints = []
    for floor in _floors(result):
        stair_room = next(room for room in floor.rooms if room.room_type is RoomType.STAIRCASE)
        assert len(floor.stairs) == 1
        stair = floor.stairs[0]
        assert stair.footprint == stair_room.polygon == result.vertical_core_plan.footprint
        assert stair.riser_mm * stair.number_of_risers == floor.floor_to_floor_mm
        assert floor.elevation_mm == floor.index * floor.floor_to_floor_mm
        footprints.append(stair.footprint)
    assert all(footprint == footprints[0] for footprint in footprints)


@pytest.mark.parametrize("floor_count", (2, 3, 4))
def test_stair_has_real_circulation_space_access_on_every_served_floor(
    buildings: dict[int, tuple[Any, Any, Any]],
    floor_count: int,
) -> None:
    _confirmed, _compiled, result = buildings[floor_count]
    for floor in _floors(result):
        stair_room = next(room for room in floor.rooms if room.room_type is RoomType.STAIRCASE)
        room_index = {room.id: room for room in floor.rooms}
        graph = build_circulation_graph(
            floor,
            require_external_entry=floor.index == 0,
            anchor_room_ids=() if floor.index == 0 else (stair_room.id,),
        )
        assert graph.connected
        assert any(
            stair_room.id in door.room_ids
            and any(
                room_id != stair_room.id
                and room_index[room_id].room_type in _CIRCULATION_CAPABLE
                for room_id in door.room_ids
            )
            for door in graph.doors
        )


def test_isolated_upper_floor_stair_fails_closed(
    buildings: dict[int, tuple[Any, Any, Any]],
) -> None:
    _confirmed, compiled, result = buildings[2]
    floors = list(_floors(result))
    upper = floors[1]
    stair_room = next(room for room in upper.rooms if room.room_type is RoomType.STAIRCASE)
    graph = build_circulation_graph(
        upper,
        require_external_entry=False,
        anchor_room_ids=(stair_room.id,),
    )
    access_ids = {
        door.opening_id for door in graph.doors if stair_room.id in door.room_ids
    }
    floors[1] = upper.model_copy(
        update={
            "openings": tuple(
                opening for opening in upper.openings if opening.id not in access_ids
            )
        }
    )
    validation = _revalidate(compiled, result, tuple(floors))
    assert not validation.accepted
    assert {"STAIR_ACCESS_INVALID", "VERTICAL_CIRCULATION_DISCONNECTED"} <= _codes(
        validation
    )


def test_missing_intermediate_core_fails_g_plus_2(
    buildings: dict[int, tuple[Any, Any, Any]],
) -> None:
    _confirmed, compiled, result = buildings[3]
    floors = list(_floors(result))
    middle = floors[1]
    floors[1] = middle.model_copy(
        update={
            "rooms": tuple(
                room for room in middle.rooms if room.room_type is not RoomType.STAIRCASE
            ),
            "stairs": (),
        }
    )
    validation = _revalidate(compiled, result, tuple(floors))
    assert not validation.accepted
    assert "VERTICAL_CORE_MISSING" in _codes(validation)
    assert len(validation.circulation.vertical_transfers) == 0


def test_unreachable_upper_room_fails_complete_building_graph(
    buildings: dict[int, tuple[Any, Any, Any]],
) -> None:
    _confirmed, compiled, result = buildings[2]
    floors = list(_floors(result))
    upper = floors[1]
    room_index = {room.id: room for room in upper.rooms}
    stair_id = next(
        room.id for room in upper.rooms if room.room_type is RoomType.STAIRCASE
    )
    graph = build_circulation_graph(
        upper,
        require_external_entry=False,
        anchor_room_ids=(stair_id,),
    )
    bedroom_door = next(
        door
        for door in graph.doors
        if stair_id not in door.room_ids
        and any(room_index[room_id].room_type is RoomType.BEDROOM for room_id in door.room_ids)
    )
    floors[1] = upper.model_copy(
        update={
            "openings": tuple(
                opening for opening in upper.openings if opening.id != bedroom_door.opening_id
            )
        }
    )
    validation = _revalidate(compiled, result, tuple(floors))
    assert not validation.accepted
    assert "VERTICAL_CIRCULATION_DISCONNECTED" in _codes(validation)
    assert validation.circulation.disconnected_nodes


def test_sanitary_room_cannot_be_required_stair_transit(
    buildings: dict[int, tuple[Any, Any, Any]],
) -> None:
    _confirmed, compiled, result = buildings[2]
    floors = list(_floors(result))
    upper = floors[1]
    lobby = next(room for room in upper.rooms if room.room_type is RoomType.LOBBY)
    mutated_rooms = tuple(
        room.model_copy(update={"room_type": RoomType.COMMON_TOILET})
        if room.id == lobby.id
        else room
        for room in upper.rooms
    )
    floors[1] = upper.model_copy(update={"rooms": mutated_rooms})
    actual_program = Counter(
        room.room_type.value for floor in floors for room in floor.rooms
    )
    validation = _revalidate(
        compiled,
        result,
        tuple(floors),
        expected_program=actual_program,
    )
    assert not validation.accepted
    assert "STAIR_ACCESS_INVALID" in _codes(validation)
    assert "VERTICAL_CIRCULATION_DISCONNECTED" in _codes(validation)


def test_stair_overlap_and_outside_floor_are_independently_rejected(
    buildings: dict[int, tuple[Any, Any, Any]],
) -> None:
    _confirmed, compiled, result = buildings[2]
    original = list(_floors(result))
    upper = original[1]
    stair = upper.stairs[0]
    non_stair = next(room for room in upper.rooms if room.room_type is not RoomType.STAIRCASE)
    overlapping_rooms = tuple(
        room.model_copy(update={"polygon": stair.footprint})
        if room.id == non_stair.id
        else room
        for room in upper.rooms
    )
    overlap_floors = (
        original[0],
        upper.model_copy(update={"rooms": overlapping_rooms}),
    )
    assert "STAIR_ROOM_OVERLAP" in _codes(
        _revalidate(compiled, result, overlap_floors)
    )

    outside_floors = (
        original[0],
        upper.model_copy(update={"boundary": rectangle(100, 0, 10_000, 10_000)}),
    )
    assert "STAIR_OUTSIDE_FLOOR_FOOTPRINT" in _codes(
        _revalidate(compiled, result, outside_floors)
    )


def test_wet_stack_evidence_distinguishes_aligned_proximate_and_dispersed(
    buildings: dict[int, tuple[Any, Any, Any]],
) -> None:
    _confirmed, _compiled, result = buildings[2]
    lower, upper = _floors(result)
    lower_toilet = next(
        room for room in lower.rooms if room.room_type is RoomType.COMMON_TOILET
    )
    upper_source = next(room for room in upper.rooms if room.room_type is RoomType.BEDROOM)

    def evaluation(polygon: IntPolygon) -> Any:
        wet_room = upper_source.model_copy(
            update={"room_type": RoomType.COMMON_TOILET, "polygon": polygon}
        )
        wet_upper = upper.model_copy(update={"rooms": (wet_room,)})
        return evaluate_wet_stacks((lower, wet_upper))

    aligned = evaluation(lower_toilet.polygon)
    toilet_xs = [point.x_mm for point in lower_toilet.polygon.outer]
    toilet_width = max(toilet_xs) - min(toilet_xs)
    proximate = evaluation(_shift(lower_toilet.polygon, toilet_width + 100, 0))
    dispersed = evaluation(rectangle(7_500, 7_500, 9_000, 9_500))
    assert aligned.pairs[0].relationship is WetStackRelationship.ALIGNED
    assert proximate.pairs[0].relationship is WetStackRelationship.PROXIMATE
    assert dispersed.pairs[0].relationship is WetStackRelationship.DISPERSED
    assert aligned.score_basis_points > proximate.score_basis_points > dispersed.score_basis_points


def test_solver_applies_soft_wet_stack_coordination_before_geometry(
    buildings: dict[int, tuple[Any, Any, Any]],
) -> None:
    _confirmed, compiled, _result = buildings[2]
    request = compiled.request
    source = next(
        requirement
        for requirement in request.floor_requirements[0]
        if requirement.room_type is RoomType.COMMON_TOILET
    )
    upper_wet = source.model_copy(
        update={
            "id": UUID("2d9f0000-0000-0000-0000-000000000001"),
            "floor_preference": (1,),
        }
    )
    wet_request = request.model_copy(
        update={
            "room_requirements": (*request.room_requirements, upper_wet),
            "floor_requirements": (
                request.floor_requirements[0],
                (*request.floor_requirements[1], upper_wet),
            ),
        }
    )
    generated = generate_architectural_plan(wet_request)
    assert generated.disposition.value == "ACCEPTED"
    assert any(
        contribution.kind == "WET_STACK_PROXIMITY"
        for contribution in generated.floor_results[1].planner_result.objective_contributions
    )
    assert generated.building_validation.wet_stack.pairs
    assert generated.building_validation.wet_stack.dispersed_count == 0


def test_candidate_core_strategy_is_deterministic_and_materially_distinct(
    buildings: dict[int, tuple[Any, Any, Any]],
) -> None:
    _confirmed, compiled, _result = buildings[2]
    request = compiled.request
    common = {
        "seed_id": request.floor_id,
        "buildable_area": request.buildable_area,
        "floor_buildable_areas": request.floor_buildable_areas,
        "floor_count": request.floor_count,
        "floor_height_mm": request.floor_to_floor_mm,
        "solver_step_mm": request.planner_config.solver_step_mm,
    }
    first = plan_vertical_architecture(
        **common,
        search_variant=PlannerSearchVariant.LOWER_LEFT,
    )
    repeated = plan_vertical_architecture(
        **common,
        search_variant=PlannerSearchVariant.LOWER_LEFT,
    )
    alternate = plan_vertical_architecture(
        **common,
        search_variant=PlannerSearchVariant.LOWER_RIGHT,
    )
    assert first == repeated
    assert first.footprint != alternate.footprint
    assert first.core_id != alternate.core_id


def test_vertical_core_dedup_ignores_jitter_but_keeps_material_difference(
    buildings: dict[int, tuple[Any, Any, Any]],
) -> None:
    confirmed, compiled, result = buildings[2]
    document = build_canonical_plan_document(
        confirmed=confirmed,
        compiled=compiled,
        result=result,
    ).document
    assert spatially_equivalent(document, _move_core(document, 50, 0))
    assert not spatially_equivalent(document, _move_core(document, 700, 0))


def test_multicandidate_generation_keeps_material_core_alternatives(
    buildings: dict[int, tuple[Any, Any, Any]],
) -> None:
    confirmed, compiled, _result = buildings[2]
    strategies = default_candidate_strategies()
    outcome = run_multi_candidate_generation(
        confirmed=confirmed,
        compiled=compiled,
        strategies=(strategies[0], strategies[2]),
        max_alternatives=2,
    )
    assert len(outcome.selected_artifacts) == 2
    cores = {
        artifact.generation.vertical_core_plan.footprint
        for artifact in outcome.selected_artifacts
    }
    assert len(cores) == 2
    assert not spatially_equivalent(
        outcome.selected_artifacts[0].canonical.document,
        outcome.selected_artifacts[1].canonical.document,
    )


def test_multifloor_canonical_serialization_hash_includes_real_stairs(
    buildings: dict[int, tuple[Any, Any, Any]],
) -> None:
    confirmed, compiled, result = buildings[3]
    document = build_canonical_plan_document(
        confirmed=confirmed,
        compiled=compiled,
        result=result,
    ).document.with_content_hash()
    parsed = PlanDocument.model_validate_json(document.to_canonical_json())
    assert parsed == document
    assert parsed.compute_content_hash() == document.content_hash
    assert all(len(floor.stairs) == 1 for floor in parsed.floors)
    assert parsed.validation.valid


def test_architectural_critic_and_quality_score_review_the_complete_building(
    buildings: dict[int, tuple[Any, Any, Any]],
) -> None:
    confirmed, compiled, result = buildings[2]
    document = build_canonical_plan_document(
        confirmed=confirmed,
        compiled=compiled,
        result=result,
    ).document
    critique = critique_plan(document)
    quality = score_plan_document(document)
    service = next(metric for metric in quality.metrics if metric.key == "service_planning")
    assert not any(
        finding.code.startswith("VERTICAL_") or finding.code == "CIRCULATION_DISCONNECTED"
        for finding in critique.findings
    )
    assert service.status.value == "EVALUATED"
    assert service.score_basis_points == result.building_validation.wet_stack.score_basis_points
