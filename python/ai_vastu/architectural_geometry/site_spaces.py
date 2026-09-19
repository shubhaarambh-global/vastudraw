from __future__ import annotations

from uuid import UUID, uuid5

from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

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
_MAX_AUTOMATIC_OPEN_SPACE_BASIS_POINTS = 2_500

_SERVICE_ROOM_TYPES = {
    "kitchen",
    "utility",
    "laundry",
}
_PARKING_ROOM_TYPES = {
    "parking",
    "garage",
}


def _polygon_shape(polygon: IntPolygon) -> Polygon:
    shell = [(point.x_mm, point.y_mm) for point in polygon.outer]
    holes = [[(point.x_mm, point.y_mm) for point in ring] for ring in polygon.holes]
    return Polygon(
        shell=shell,
        holes=holes,
    )


def _polygon_components(
    geometry: BaseGeometry,
) -> tuple[Polygon, ...]:
    if geometry.is_empty:
        return ()

    if isinstance(geometry, Polygon):
        return (geometry,)

    if isinstance(geometry, MultiPolygon):
        return tuple(
            sorted(
                geometry.geoms,
                key=lambda item: (
                    item.bounds[0],
                    item.bounds[1],
                    item.bounds[2],
                    item.bounds[3],
                ),
            )
        )

    polygons = tuple(item for item in getattr(geometry, "geoms", ()) if isinstance(item, Polygon))

    return tuple(
        sorted(
            polygons,
            key=lambda item: (
                item.bounds[0],
                item.bounds[1],
                item.bounds[2],
                item.bounds[3],
            ),
        )
    )


def _rectangle_bounds(
    polygon: Polygon,
) -> tuple[int, int, int, int] | None:
    if polygon.interiors:
        return None

    min_x, min_y, max_x, max_y = (round(value) for value in polygon.bounds)

    if min_x >= max_x or min_y >= max_y:
        return None

    rectangle = box(
        min_x,
        min_y,
        max_x,
        max_y,
    )

    # Residual geometry comes from integer orthogonal room polygons.
    # A tiny tolerance avoids rejecting mathematically identical
    # rectangles because Shapely operates in floating point.
    if polygon.symmetric_difference(rectangle).area > 1.0:
        return None

    return (
        min_x,
        min_y,
        max_x,
        max_y,
    )


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


def _road_segment(
    envelope: Polygon,
    *,
    side: PlannerBoundarySide,
    solver_step_mm: int,
) -> LineString:
    min_x, min_y, max_x, max_y = (round(value) for value in envelope.bounds)

    step = max(
        1,
        solver_step_mm,
    )

    # Match the CP-SAT positive-side lattice projection used by
    # architectural wall/boundary detection.
    lattice_max_x = min_x + ((max_x - min_x) // step) * step
    lattice_max_y = min_y + ((max_y - min_y) // step) * step

    if side is PlannerBoundarySide.SOUTH:
        return LineString(
            (
                (min_x, min_y),
                (max_x, min_y),
            )
        )

    if side is PlannerBoundarySide.NORTH:
        return LineString(
            (
                (min_x, lattice_max_y),
                (max_x, lattice_max_y),
            )
        )

    if side is PlannerBoundarySide.WEST:
        return LineString(
            (
                (min_x, min_y),
                (min_x, max_y),
            )
        )

    return LineString(
        (
            (lattice_max_x, min_y),
            (lattice_max_x, max_y),
        )
    )


def _shared_boundary_length(
    first: Polygon,
    second: BaseGeometry,
) -> float:
    return first.boundary.intersection(second).length


def _touches_envelope_boundary(
    polygon: Polygon,
    envelope: Polygon,
) -> bool:
    return polygon.boundary.intersection(envelope.boundary).length > 0


def _adjacent_to_room_type(
    polygon: Polygon,
    room_shapes: tuple[
        tuple[RoomGeometry, Polygon],
        ...,
    ],
    room_types: set[str],
) -> bool:
    return any(
        room.room_type.value in room_types
        and _shared_boundary_length(
            polygon,
            shape.boundary,
        )
        > 0
        for room, shape in room_shapes
    )


def _parking_has_direct_road_access(
    room_shapes: tuple[
        tuple[RoomGeometry, Polygon],
        ...,
    ],
    road_segment: LineString | None,
) -> bool:
    if road_segment is None:
        return False

    return any(
        room.room_type.value in _PARKING_ROOM_TYPES
        and _shared_boundary_length(
            shape,
            road_segment,
        )
        > 0
        for room, shape in room_shapes
    )


def _vehicle_access_eligible(
    *,
    polygon: Polygon,
    bounds: tuple[int, int, int, int],
    road_side: PlannerBoundarySide | None,
    road_segment: LineString | None,
    room_shapes: tuple[
        tuple[RoomGeometry, Polygon],
        ...,
    ],
    direct_parking_access: bool,
) -> bool:
    if road_side is None or road_segment is None or direct_parking_access:
        return False

    if (
        _shared_boundary_length(
            polygon,
            road_segment,
        )
        <= 0
    ):
        return False

    if not _adjacent_to_room_type(
        polygon,
        room_shapes,
        _PARKING_ROOM_TYPES,
    ):
        return False

    min_x, min_y, max_x, max_y = bounds
    width_mm = max_x - min_x
    depth_mm = max_y - min_y

    if polygon.area < _MIN_VEHICLE_ACCESS_AREA_MM2:
        return False

    if road_side in {
        PlannerBoundarySide.NORTH,
        PlannerBoundarySide.SOUTH,
    }:
        return width_mm >= _MIN_VEHICLE_ACCESS_WIDTH_MM

    return depth_mm >= _MIN_VEHICLE_ACCESS_WIDTH_MM


def _utility_yard_eligible(
    *,
    polygon: Polygon,
    bounds: tuple[int, int, int, int],
    envelope: Polygon,
    room_shapes: tuple[
        tuple[RoomGeometry, Polygon],
        ...,
    ],
) -> bool:
    if not _touches_envelope_boundary(
        polygon,
        envelope,
    ):
        return False

    if not _adjacent_to_room_type(
        polygon,
        room_shapes,
        _SERVICE_ROOM_TYPES,
    ):
        return False

    min_x, min_y, max_x, max_y = bounds
    minimum_dimension = min(
        max_x - min_x,
        max_y - min_y,
    )
    area = round(polygon.area)

    return (
        minimum_dimension >= _MIN_UTILITY_YARD_WIDTH_MM
        and area >= _MIN_UTILITY_YARD_AREA_MM2
        and area <= _MAX_UTILITY_YARD_AREA_MM2
    )


def _lightwell_eligible(
    *,
    polygon: Polygon,
    bounds: tuple[int, int, int, int],
    envelope: Polygon,
) -> bool:
    if _touches_envelope_boundary(
        polygon,
        envelope,
    ):
        return False

    min_x, min_y, max_x, max_y = bounds
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
    area = round(polygon.area)

    if minimum_dimension <= 0:
        return False

    aspect_ratio = maximum_dimension / minimum_dimension

    return (
        area >= _MIN_LIGHTWELL_AREA_MM2
        and area <= _MAX_LIGHTWELL_AREA_MM2
        and minimum_dimension >= _MIN_LIGHTWELL_WIDTH_MM
        and maximum_dimension <= _MAX_LIGHTWELL_DIMENSION_MM
        and aspect_ratio <= _MAX_LIGHTWELL_ASPECT_RATIO
    )


def _open_space_eligible(
    *,
    polygon: Polygon,
    bounds: tuple[int, int, int, int],
    envelope: Polygon,
) -> bool:
    if not _touches_envelope_boundary(
        polygon,
        envelope,
    ):
        return False

    min_x, min_y, max_x, max_y = bounds
    minimum_dimension = min(
        max_x - min_x,
        max_y - min_y,
    )
    area = round(polygon.area)
    envelope_area = max(
        1,
        round(envelope.area),
    )
    basis_points = round(area * 10_000 / envelope_area)

    return (
        minimum_dimension >= _MIN_OPEN_SPACE_WIDTH_MM
        and area >= _MIN_OPEN_SPACE_AREA_MM2
        and basis_points <= _MAX_AUTOMATIC_OPEN_SPACE_BASIS_POINTS
    )


def _space_id(
    *,
    floor_id: UUID,
    kind: SiteSpaceKind,
    bounds: tuple[int, int, int, int],
) -> UUID:
    return uuid5(
        _SITE_SPACE_NAMESPACE,
        "|".join(
            (
                str(floor_id),
                kind.value,
                *(str(value) for value in bounds),
            )
        ),
    )


def derive_purposeful_site_spaces(
    *,
    floor_id: UUID,
    envelope: IntPolygon,
    rooms: tuple[RoomGeometry, ...],
    road_boundary_side: PlannerBoundarySide | None,
    solver_step_mm: int,
) -> tuple[PurposefulSiteSpace, ...]:
    """Classify only architecturally eligible residual rectangles.

    This function deliberately fails to classify arbitrary residual geometry.
    Any irregular, oversized or otherwise unsupported residual remains
    unexplained and is rejected later by Architectural Brain site accounting.
    """

    envelope_shape = _polygon_shape(envelope)
    room_shapes = tuple(
        (
            room,
            _polygon_shape(room.polygon),
        )
        for room in rooms
    )

    if room_shapes:
        occupied = unary_union(tuple(shape for _, shape in room_shapes))
        residual = envelope_shape.difference(occupied)
    else:
        residual = envelope_shape

    road_segment = (
        _road_segment(
            envelope_shape,
            side=road_boundary_side,
            solver_step_mm=solver_step_mm,
        )
        if road_boundary_side is not None
        else None
    )

    direct_parking_access = _parking_has_direct_road_access(
        room_shapes,
        road_segment,
    )

    spaces: list[PurposefulSiteSpace] = []

    for polygon in _polygon_components(residual):
        bounds = _rectangle_bounds(polygon)

        # Irregular/L-shaped residuals are intentionally NOT
        # auto-labelled as open space.
        if bounds is None:
            continue

        kind: SiteSpaceKind | None = None
        label: str | None = None

        if _vehicle_access_eligible(
            polygon=polygon,
            bounds=bounds,
            road_side=road_boundary_side,
            road_segment=road_segment,
            room_shapes=room_shapes,
            direct_parking_access=direct_parking_access,
        ):
            kind = SiteSpaceKind.VEHICLE_ACCESS
            label = "Road-to-parking vehicle access"

        elif _utility_yard_eligible(
            polygon=polygon,
            bounds=bounds,
            envelope=envelope_shape,
            room_shapes=room_shapes,
        ):
            kind = SiteSpaceKind.UTILITY_YARD
            label = "Service utility yard"

        elif _lightwell_eligible(
            polygon=polygon,
            bounds=bounds,
            envelope=envelope_shape,
        ):
            kind = SiteSpaceKind.LIGHTWELL
            label = "Internal lightwell"

        elif _open_space_eligible(
            polygon=polygon,
            bounds=bounds,
            envelope=envelope_shape,
        ):
            kind = SiteSpaceKind.OPEN_SPACE
            label = "Boundary-connected open space"

        if kind is None:
            continue

        spaces.append(
            PurposefulSiteSpace(
                id=_space_id(
                    floor_id=floor_id,
                    kind=kind,
                    bounds=bounds,
                ),
                kind=kind,
                polygon=_int_rectangle(bounds),
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
