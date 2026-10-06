from uuid import UUID

import pytest

from ai_vastu.architectural_geometry import ArchitecturalGeometryResult
from ai_vastu.exporting import build_drawing_scene, build_professional_presentation
from ai_vastu.exporting.geometry import visible_wall_segments
from ai_vastu.generation import CirculationGenerationConfig, generate_architectural_plan
from ai_vastu.generation.errors import GenerationInputError
from ai_vastu.generation.service import _synthesize_vehicle_openings, _validate_vehicle_openings
from ai_vastu.plan_schema import AxisSegment, Opening, OpeningKind, Road, RoomGeometry, RoomType
from ai_vastu.solver import PlannerBoundarySide
from ai_vastu.validation.vehicle_access import validate_document_vehicle_access
from tests.exporting.helpers import export_plan

from .test_pipeline import _rectangle, _request


def _fixture(side: PlannerBoundarySide):
    request = _request()
    planning = request.planner_config.residential_planning.model_copy(update={
        "enabled": True, "require_road_connected_parking": True, "road_boundary_side": side,
    })
    request = request.model_copy(update={"planner_config": request.planner_config.model_copy(
        update={"residential_planning": planning}
    )})
    document = export_plan()
    floor = document.floors[0]
    boundary = _rectangle(9000, 7000)
    room = floor.rooms[0].model_copy(update={"room_type": RoomType.PARKING, "polygon": boundary})
    points = boundary.outer
    edge = {PlannerBoundarySide.SOUTH: 0, PlannerBoundarySide.EAST: 1,
            PlannerBoundarySide.NORTH: 2, PlannerBoundarySide.WEST: 3}[side]
    wall = floor.walls[0].model_copy(update={"axis": AxisSegment(
        start=points[edge], end=points[(edge + 1) % 4],
    )})
    floor = floor.model_copy(update={"rooms": (room,), "walls": (wall,), "openings": ()})
    geometry = ArchitecturalGeometryResult(source_problem_hash="0" * 64,
        source_planner_hash="1" * 64, floor=floor)
    return request, geometry, document


@pytest.mark.parametrize("side", tuple(PlannerBoundarySide))
def test_vehicle_gap_is_canonical_road_aligned_and_exported(side):
    request, geometry, document = _fixture(side)
    requests = _synthesize_vehicle_openings(geometry, request)
    assert requests == _synthesize_vehicle_openings(geometry, request)
    assert len(requests) == 1
    opening = Opening(id=UUID("77777777-7777-7777-7777-777777777777"),
                      **requests[0].model_dump())
    assert opening.kind is OpeningKind.OPENING
    assert opening.width_mm == 3000 and opening.sill_height_mm == 0
    floor = geometry.floor.model_copy(update={"openings": (opening,)})
    _validate_vehicle_openings(geometry.model_copy(update={"floor": floor}), request)
    road_edge = {PlannerBoundarySide.SOUTH: 0, PlannerBoundarySide.EAST: 1,
                 PlannerBoundarySide.NORTH: 2, PlannerBoundarySide.WEST: 3}[side]
    road = Road(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa0"),
                plot_edge_ids=(document.plot.edge_ids[road_edge],), primary_access=True)
    document = document.model_copy(update={"floors": (floor,), "roads": (road,),
                                           "content_hash": None})
    assert validate_document_vehicle_access(document) == ()
    scene = build_drawing_scene(document)
    presentation = build_professional_presentation(scene)
    assert len(presentation.plain_openings) == 1
    segments = visible_wall_segments(scene)
    assert len(segments) == 2
    gap_start = opening.offset_from_wall_start_mm
    gap_end = gap_start + opening.width_mm
    axis = floor.walls[0].axis
    # Actual exported strokes stop at the gap and resume after its full width.
    length = abs(axis.end.x_mm - axis.start.x_mm) + abs(axis.end.y_mm - axis.start.y_mm)
    drawn = sum(abs(s.end[0] - s.start[0]) + abs(s.end[1] - s.start[1])
                for s in segments)
    assert drawn == length - (gap_end - gap_start)


def test_parking_cannot_use_a_wall_shared_with_an_occupied_room():
    request, geometry, _ = _fixture(PlannerBoundarySide.SOUTH)
    occupied = geometry.floor.rooms[0].model_copy(update={
        "id": UUID("55555555-5555-5555-5555-555555555552"), "room_type": RoomType.LIVING,
    })
    geometry = geometry.model_copy(update={"floor": geometry.floor.model_copy(update={
        "rooms": (*geometry.floor.rooms, occupied),
    })})
    with pytest.raises(GenerationInputError, match="VEHICLE_ACCESS_INVALID"):
        _synthesize_vehicle_openings(geometry, request)


def test_missing_or_pedestrian_width_vehicle_opening_fails_closed():
    request, geometry, _ = _fixture(PlannerBoundarySide.SOUTH)
    with pytest.raises(GenerationInputError, match="VEHICLE_ACCESS_INVALID"):
        _validate_vehicle_openings(geometry, request)
    opening_request = _synthesize_vehicle_openings(geometry, request)[0]
    for update in ({"width_mm": 900}, {"sill_height_mm": 100}, {"height_mm": 1800}):
        opening = Opening(id=UUID("77777777-7777-7777-7777-777777777777"),
                          **opening_request.model_copy(update=update).model_dump())
        invalid_geometry = geometry.model_copy(update={"floor": geometry.floor.model_copy(update={
            "openings": (opening,),
        })})
        with pytest.raises(GenerationInputError, match="VEHICLE_ACCESS_INVALID"):
            _validate_vehicle_openings(invalid_geometry, request)


def test_final_document_vehicle_access_rejects_road_mismatch_and_occupied_transit():
    request, geometry, document = _fixture(PlannerBoundarySide.NORTH)
    gap = _synthesize_vehicle_openings(geometry, request)[0]
    opening = Opening(id=UUID("77777777-7777-7777-7777-777777777777"), **gap.model_dump())
    floor = geometry.floor.model_copy(update={"openings": (opening,)})
    road_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa0")
    wrong_road = Road(id=road_id, plot_edge_ids=(document.plot.edge_ids[0],))
    document = document.model_copy(update={"floors": (floor,), "roads": (wrong_road,),
                                           "content_hash": None})
    assert validate_document_vehicle_access(document) == ("VEHICLE_ACCESS_INVALID",)
    north_road = Road(id=road_id, plot_edge_ids=(document.plot.edge_ids[2],))
    document = document.model_copy(update={"roads": (north_road,)})
    assert validate_document_vehicle_access(document) == ()
    occupied = RoomGeometry(id=UUID("55555555-5555-5555-5555-555555555553"),
        room_type=RoomType.BEDROOM, name="Intervening bedroom",
        polygon=geometry.floor.rooms[0].polygon.model_copy(update={"outer": tuple(
            point.model_copy(update={"y_mm": 7000 + point.y_mm // 7})
            for point in geometry.floor.rooms[0].polygon.outer
        )}))
    floor = floor.model_copy(update={"rooms": (*floor.rooms, occupied)})
    document = document.model_copy(update={"floors": (floor,)})
    assert validate_document_vehicle_access(document) == ("VEHICLE_ACCESS_INVALID",)


def test_final_document_vehicle_strip_cannot_cross_a_closed_wall():
    request, geometry, document = _fixture(PlannerBoundarySide.NORTH)
    gap = _synthesize_vehicle_openings(geometry, request)[0]
    opening = Opening(id=UUID("77777777-7777-7777-7777-777777777777"), **gap.model_dump())
    points = geometry.floor.rooms[0].polygon.outer
    barrier = geometry.floor.walls[0].model_copy(update={
        "id": UUID("66666666-6666-6666-6666-666666666669"),
        "axis": AxisSegment(start=points[3].model_copy(update={"y_mm": 7500}),
                            end=points[2].model_copy(update={"y_mm": 7500})),
    })
    floor = geometry.floor.model_copy(update={"walls": (*geometry.floor.walls, barrier),
                                              "openings": (opening,)})
    road = Road(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa0"),
                plot_edge_ids=(document.plot.edge_ids[2],))
    document = document.model_copy(update={"floors": (floor,), "roads": (road,),
                                           "content_hash": None})
    assert validate_document_vehicle_access(document) == ("VEHICLE_ACCESS_INVALID",)


@pytest.mark.parametrize("obstruction", ("room", "wall", "full_height_gap"))
def test_final_document_qualifies_bay_interior_independently_of_road_strip(obstruction):
    request, geometry, document = _fixture(PlannerBoundarySide.SOUTH)
    gap = _synthesize_vehicle_openings(geometry, request)[0]
    opening = Opening(id=UUID("77777777-7777-7777-7777-777777777777"), **gap.model_dump())
    floor = geometry.floor.model_copy(update={"openings": (opening,)})
    road = Road(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa0"),
                plot_edge_ids=(document.plot.edge_ids[0],))
    document = document.model_copy(update={"floors": (floor,), "roads": (road,),
                                           "content_hash": None})
    assert validate_document_vehicle_access(document) == ()
    if obstruction == "room":
        occupied = floor.rooms[0].model_copy(update={
            "id": UUID("55555555-5555-5555-5555-555555555553"), "room_type": RoomType.LIVING,
        })
        floor = floor.model_copy(update={"rooms": (*floor.rooms, occupied)})
    else:
        axis = floor.walls[0].axis
        barrier = floor.walls[0].model_copy(update={
            "id": UUID("66666666-6666-6666-6666-666666666669"),
            "axis": AxisSegment(start=axis.start.model_copy(update={"y_mm": 1000}),
                                end=axis.end.model_copy(update={"y_mm": 1000})),
        })
        openings = floor.openings
        if obstruction == "full_height_gap":
            clear_gap = opening.model_copy(update={
                "id": UUID("77777777-7777-7777-7777-777777777778"),
                "wall_id": barrier.id, "offset_from_wall_start_mm": 0, "width_mm": 9000,
            })
            openings = (*openings, clear_gap)
        floor = floor.model_copy(update={"walls": (*floor.walls, barrier), "openings": openings})
    document = document.model_copy(update={"floors": (floor,)})
    expected = () if obstruction == "full_height_gap" else ("VEHICLE_ACCESS_INVALID",)
    assert validate_document_vehicle_access(document) == expected


def test_final_document_rejects_shallow_bay_even_with_vehicle_width_gap():
    request, geometry, document = _fixture(PlannerBoundarySide.SOUTH)
    gap = _synthesize_vehicle_openings(geometry, request)[0]
    opening = Opening(id=UUID("77777777-7777-7777-7777-777777777777"), **gap.model_dump())
    shallow = geometry.floor.rooms[0].model_copy(update={"polygon": _rectangle(9000, 5000)})
    floor = geometry.floor.model_copy(update={"rooms": (shallow,), "openings": (opening,)})
    road = Road(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa0"),
                plot_edge_ids=(document.plot.edge_ids[0],))
    document = document.model_copy(update={"floors": (floor,), "roads": (road,),
                                           "content_hash": None})
    assert validate_document_vehicle_access(document) == ("VEHICLE_ACCESS_INVALID",)


@pytest.mark.parametrize("side", tuple(PlannerBoundarySide))
def test_solved_parking_builds_vehicle_gap_without_using_it_as_dwelling_entry(side):
    request = _request()
    base = request.room_requirements[1]
    parking = base.model_copy(update={
        "room_type": RoomType.PARKING, "min_width_mm": 3000, "min_depth_mm": 3000,
        "preferred_width_mm": 3300, "preferred_depth_mm": 5800,
        "max_width_mm": 6500, "max_depth_mm": 6500, "min_area_mm2": 16_500_000,
    })
    opposite = {PlannerBoundarySide.SOUTH: PlannerBoundarySide.NORTH,
                PlannerBoundarySide.NORTH: PlannerBoundarySide.SOUTH,
                PlannerBoundarySide.EAST: PlannerBoundarySide.WEST,
                PlannerBoundarySide.WEST: PlannerBoundarySide.EAST}[side]
    planning = request.planner_config.residential_planning.model_copy(update={
        "enabled": True, "require_road_connected_parking": True, "road_boundary_side": side,
        "require_entrance_boundary_access": True, "entrance_boundary_side": opposite,
    })
    request = request.model_copy(update={
        "room_requirements": (request.room_requirements[0], parking),
        "planner_config": request.planner_config.model_copy(update={
            "solver_step_mm": 10, "clearance_reserve_mm": 230,
            "residential_planning": planning,
        }),
        "circulation_config": CirculationGenerationConfig(auto_generate=True),
    })
    result = generate_architectural_plan(request)
    assert result.disposition.value == "ACCEPTED", result
    assert result.geometry_result is not None
    floor = result.geometry_result.floor
    gaps = tuple(opening for opening in floor.openings if opening.kind is OpeningKind.OPENING)
    assert len(gaps) == 1 and gaps[0].width_mm == 3000
    assert sum(opening.kind is OpeningKind.DOOR for opening in floor.openings) == 1
    document = export_plan()
    road_edge = {PlannerBoundarySide.SOUTH: 0, PlannerBoundarySide.EAST: 1,
                 PlannerBoundarySide.NORTH: 2, PlannerBoundarySide.WEST: 3}[side]
    road = Road(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa0"),
                plot_edge_ids=(document.plot.edge_ids[road_edge],))
    document = document.model_copy(update={
        "floors": (floor,), "roads": (road,), "content_hash": None,
        "plot": document.plot.model_copy(update={"boundary": request.plot_boundary}),
        "buildable_area": request.buildable_area,
    })
    assert validate_document_vehicle_access(document) == ()
