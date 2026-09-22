from __future__ import annotations

from uuid import UUID, uuid5

from ai_vastu.geometry import (
    ResidualPolygonMeasurement,
    measure_site_residual_polygons,
    polygon_has_usable_core,
)
from ai_vastu.plan_schema import (
    IntPoint,
    IntPolygon,
    PurposefulSiteSpace,
    RoomGeometry,
    SiteSpaceKind,
    SiteSpaceSource,
)
from ai_vastu.solver.models import PlannerBoundarySide

_SITE_SPACE_NAMESPACE = UUID("246960de-bb4f-55d0-bd52-071a747ea031")

_MIN_VEHICLE_ACCESS_AREA_MM2 = 3_000_000
_MIN_VEHICLE_ACCESS_WIDTH_MM = 3_000

_MIN_UTILITY_YARD_AREA_MM2 = 2_000_000
_MAX_UTILITY_YARD_AREA_MM2 = 20_000_000
_MIN_UTILITY_YARD_WIDTH_MM = 900

_MIN_LIGHTWELL_AREA_MM2 = 1_500_000
_MAX_LIGHTWELL_AREA_MM2 = 12_000_000
_MIN_LIGHTWELL_WIDTH_MM = 900
_MAX_LIGHTWELL_DIMENSION_MM = 3_500
_MAX_LIGHTWELL_ASPECT_RATIO = 2.5

_MIN_OPEN_SPACE_AREA_MM2 = 4_000_000
_MIN_OPEN_SPACE_WIDTH_MM = 1_200

_MIN_LANDSCAPE_AREA_MM2 = 500_000
_MIN_LANDSCAPE_WIDTH_MM = 600

_MIN_SHAFT_AREA_MM2 = 250_000
_MAX_SHAFT_AREA_MM2 = 4_000_000
_MIN_SHAFT_WIDTH_MM = 450
_MAX_SHAFT_DIMENSION_MM = 3_000

_SERVICE_ROOM_TYPES = {
    "kitchen",
    "utility",
    "laundry",
}
_SANITARY_ROOM_TYPES = {
    "attached_toilet",
    "common_toilet",
    "powder_room",
    "bath",
    "servant_toilet",
}
_SHAFT_ADJACENT_ROOM_TYPES = _SERVICE_ROOM_TYPES | _SANITARY_ROOM_TYPES
_PARKING_ROOM_TYPES = {
    "parking",
    "garage",
}


def _int_rectangle(
    bounds: tuple[int, int, int, int],
) -> IntPolygon:
    min_x, min_y, max_x, max_y = bounds

    return IntPolygon(
        outer=(
            IntPoint(
                x_mm=min_x,
                y_mm=min_y,
            ),
            IntPoint(
                x_mm=max_x,
                y_mm=min_y,
            ),
            IntPoint(
                x_mm=max_x,
                y_mm=max_y,
            ),
            IntPoint(
                x_mm=min_x,
                y_mm=max_y,
            ),
        )
    )


def _vehicle_access_eligible(
    *,
    candidate: ResidualPolygonMeasurement,
    road_side: PlannerBoundarySide | None,
    rooms: tuple[RoomGeometry, ...],
    direct_parking_access: bool,
) -> bool:
    if candidate.rectangle_bounds is None:
        return False

    if road_side is None or direct_parking_access:
        return False

    if candidate.road_boundary_shared_length_mm <= 0:
        return False

    if not any(
        rooms[index].room_type.value in _PARKING_ROOM_TYPES
        for index in candidate.adjacent_polygon_indexes
    ):
        return False

    min_x, min_y, max_x, max_y = candidate.bounds
    width_mm = max_x - min_x
    depth_mm = max_y - min_y

    if candidate.area_mm2 < _MIN_VEHICLE_ACCESS_AREA_MM2:
        return False

    if road_side in {
        PlannerBoundarySide.NORTH,
        PlannerBoundarySide.SOUTH,
    }:
        return width_mm >= _MIN_VEHICLE_ACCESS_WIDTH_MM

    return depth_mm >= _MIN_VEHICLE_ACCESS_WIDTH_MM


def _utility_yard_eligible(
    *,
    candidate: ResidualPolygonMeasurement,
    rooms: tuple[RoomGeometry, ...],
) -> bool:
    if candidate.rectangle_bounds is None:
        return False

    if not candidate.touches_envelope_boundary:
        return False

    if not any(
        rooms[index].room_type.value in _SERVICE_ROOM_TYPES
        for index in candidate.adjacent_polygon_indexes
    ):
        return False

    min_x, min_y, max_x, max_y = candidate.bounds
    minimum_dimension = min(
        max_x - min_x,
        max_y - min_y,
    )
    area = candidate.area_mm2

    return (
        minimum_dimension >= _MIN_UTILITY_YARD_WIDTH_MM
        and area >= _MIN_UTILITY_YARD_AREA_MM2
        and area <= _MAX_UTILITY_YARD_AREA_MM2
    )


def _lightwell_eligible(
    *,
    candidate: ResidualPolygonMeasurement,
) -> bool:
    if candidate.touches_envelope_boundary:
        return False

    min_x, min_y, max_x, max_y = candidate.bounds
    width_mm = max_x - min_x
    depth_mm = max_y - min_y
    minimum_dimension = min(
        width_mm,
        depth_mm,
    )
    maximum_dimension = max(
        width_mm,
        depth_mm,
    )
    area = candidate.area_mm2

    if minimum_dimension <= 0:
        return False

    aspect_ratio = maximum_dimension / minimum_dimension

    return (
        area >= _MIN_LIGHTWELL_AREA_MM2
        and area <= _MAX_LIGHTWELL_AREA_MM2
        and minimum_dimension >= _MIN_LIGHTWELL_WIDTH_MM
        and maximum_dimension <= _MAX_LIGHTWELL_DIMENSION_MM
        and aspect_ratio <= _MAX_LIGHTWELL_ASPECT_RATIO
        and polygon_has_usable_core(
            candidate.polygon,
            minimum_width_mm=_MIN_LIGHTWELL_WIDTH_MM,
        )
    )


def _shaft_eligible(
    *,
    candidate: ResidualPolygonMeasurement,
    rooms: tuple[RoomGeometry, ...],
) -> bool:
    if candidate.touches_envelope_boundary:
        return False

    if not (
        _MIN_SHAFT_AREA_MM2
        <= candidate.area_mm2
        <= _MAX_SHAFT_AREA_MM2
    ):
        return False

    min_x, min_y, max_x, max_y = candidate.bounds
    if max(max_x - min_x, max_y - min_y) > _MAX_SHAFT_DIMENSION_MM:
        return False

    if not any(
        rooms[index].room_type.value in _SHAFT_ADJACENT_ROOM_TYPES
        for index in candidate.adjacent_polygon_indexes
    ):
        return False

    return polygon_has_usable_core(
        candidate.polygon,
        minimum_width_mm=_MIN_SHAFT_WIDTH_MM,
    )


def _open_space_eligible(
    *,
    candidate: ResidualPolygonMeasurement,
) -> bool:
    if not candidate.touches_envelope_boundary:
        return False

    if candidate.area_mm2 < _MIN_OPEN_SPACE_AREA_MM2:
        return False

    return polygon_has_usable_core(
        candidate.polygon,
        minimum_width_mm=_MIN_OPEN_SPACE_WIDTH_MM,
    )


def _landscape_eligible(
    *,
    candidate: ResidualPolygonMeasurement,
) -> bool:
    if not candidate.touches_envelope_boundary:
        return False

    if candidate.area_mm2 < _MIN_LANDSCAPE_AREA_MM2:
        return False

    return polygon_has_usable_core(
        candidate.polygon,
        minimum_width_mm=_MIN_LANDSCAPE_WIDTH_MM,
    )


def _space_id(
    *,
    floor_id: UUID,
    kind: SiteSpaceKind,
    bounds: tuple[int, int, int, int],
    polygon: IntPolygon | None = None,
) -> UUID:
    identity_parts = [
        str(floor_id),
        kind.value,
        *(str(value) for value in bounds),
    ]

    if polygon is not None:
        identity_parts.append("outer")
        identity_parts.extend(
            f"{point.x_mm},{point.y_mm}"
            for point in polygon.outer
        )
        for hole_index, hole in enumerate(polygon.holes):
            identity_parts.append(f"hole:{hole_index}")
            identity_parts.extend(
                f"{point.x_mm},{point.y_mm}"
                for point in hole
            )

    return uuid5(
        _SITE_SPACE_NAMESPACE,
        "|".join(identity_parts),
    )


def derive_purposeful_site_spaces(
    *,
    floor_id: UUID,
    envelope: IntPolygon,
    rooms: tuple[RoomGeometry, ...],
    road_boundary_side: PlannerBoundarySide | None,
    solver_step_mm: int,
) -> tuple[PurposefulSiteSpace, ...]:
    """Classify architecturally supported residual site geometry.

    Residual construction is canonical and deterministic. Specialized vehicle,
    utility and lightwell classifications remain conservative, while legitimate
    boundary-connected polygonal open space may be represented explicitly.
    Unsupported residual geometry remains unexplained and therefore fail-closed
    in Architectural Brain site accounting.
    """

    measurement = measure_site_residual_polygons(
        envelope,
        tuple(room.polygon for room in rooms),
        road_boundary_side=(
            road_boundary_side.value if road_boundary_side is not None else None
        ),
        solver_step_mm=solver_step_mm,
    )

    direct_parking_access = any(
        rooms[index].room_type.value in _PARKING_ROOM_TYPES
        for index in measurement.road_adjacent_polygon_indexes
    )

    spaces: list[PurposefulSiteSpace] = []

    for candidate in measurement.polygons:
        bounds = candidate.bounds
        kind: SiteSpaceKind | None = None
        label: str | None = None

        if _vehicle_access_eligible(
            candidate=candidate,
            road_side=road_boundary_side,
            rooms=rooms,
            direct_parking_access=direct_parking_access,
        ):
            kind = SiteSpaceKind.VEHICLE_ACCESS
            label = "Road-to-parking vehicle access"

        elif _utility_yard_eligible(
            candidate=candidate,
            rooms=rooms,
        ):
            kind = SiteSpaceKind.UTILITY_YARD
            label = "Service utility yard"

        elif _lightwell_eligible(
            candidate=candidate,
        ):
            kind = SiteSpaceKind.LIGHTWELL
            label = "Internal lightwell"

        elif _shaft_eligible(
            candidate=candidate,
            rooms=rooms,
        ):
            kind = SiteSpaceKind.SHAFT
            label = "Internal service shaft"

        elif _open_space_eligible(
            candidate=candidate,
        ):
            kind = SiteSpaceKind.OPEN_SPACE
            label = "Boundary-connected open space"

        elif _landscape_eligible(
            candidate=candidate,
        ):
            kind = SiteSpaceKind.LANDSCAPE
            label = "Boundary-connected landscape strip"

        if kind is None:
            continue

        spaces.append(
            PurposefulSiteSpace(
                id=_space_id(
                    floor_id=floor_id,
                    kind=kind,
                    bounds=bounds,
                    polygon=(
                        candidate.polygon
                        if candidate.rectangle_bounds is None
                        else None
                    ),
                ),
                kind=kind,
                polygon=(
                    _int_rectangle(bounds)
                    if candidate.rectangle_bounds is not None
                    else candidate.polygon
                ),
                label=label,
                source=SiteSpaceSource.SYSTEM_DERIVED,
            )
        )

    return tuple(
        sorted(
            spaces,
            key=lambda item: (
                item.kind.value,
                str(item.id),
            ),
        )
    )
