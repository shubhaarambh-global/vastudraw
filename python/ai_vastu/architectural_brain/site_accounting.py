from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from ai_vastu.plan_schema import Floor, IntPolygon

from .models import (
    ResidualRegion,
    SiteAccounting,
    SiteAccountingAnalysis,
    SpaceAllocation,
)

_BASE_NUMERICAL_TOLERANCE_MM2 = 10_000


def close_site_accounting(
    *,
    envelope_area_mm2: int,
    allocations: Iterable[SpaceAllocation],
) -> SiteAccounting:
    if envelope_area_mm2 <= 0:
        raise ValueError("envelope_area_mm2 must be positive.")
    items = tuple(allocations)
    classified = sum(item.area_mm2 for item in items)
    if classified > envelope_area_mm2:
        raise ValueError("Classified area exceeds the confirmed envelope.")
    residual = envelope_area_mm2 - classified
    allocation_bp = min(
        10_000,
        (classified * 10_000 + envelope_area_mm2 // 2) // envelope_area_mm2,
    )
    return SiteAccounting(
        envelope_area_mm2=envelope_area_mm2,
        allocations=items,
        classified_area_mm2=classified,
        residual_area_mm2=residual,
        allocation_basis_points=allocation_bp,
    )


def require_no_unexplained_residual(
    accounting: SiteAccounting,
    *,
    tolerance_mm2: int = _BASE_NUMERICAL_TOLERANCE_MM2,
) -> None:
    if accounting.residual_area_mm2 > tolerance_mm2:
        raise ValueError(
            "Unexplained residual site area exceeds tolerance; classify it as "
            "setback/open-space/courtyard/landscape/utility or allocate it to the plan."
        )


def _polygon_shape(polygon: IntPolygon) -> Polygon:
    shell = [(point.x_mm, point.y_mm) for point in polygon.outer]
    holes = [[(point.x_mm, point.y_mm) for point in hole] for hole in polygon.holes]
    shape = Polygon(shell=shell, holes=holes)
    if shape.is_empty or not shape.is_valid:
        raise ValueError("Site accounting requires valid non-empty polygons.")
    return shape


def _room_category(
    room_type: str,
) -> Literal[
    "ROOM",
    "CIRCULATION",
    "PARKING",
    "PORCH",
    "COURTYARD",
]:
    if room_type in {"parking", "garage"}:
        return "PARKING"
    if room_type in {
        "lobby",
        "corridor",
        "foyer",
        "passage",
        "circulation",
    }:
        return "CIRCULATION"
    if room_type in {"verandah", "porch"}:
        return "PORCH"
    if room_type == "courtyard":
        return "COURTYARD"
    return "ROOM"


def _site_space_category(
    kind: str,
) -> Literal[
    "LIGHTWELL",
    "LANDSCAPE",
    "OPEN_SPACE",
    "UTILITY_YARD",
    "VEHICLE_ACCESS",
    "SHAFT",
    "PORCH",
]:
    mapping = {
        "LIGHTWELL": "LIGHTWELL",
        "LANDSCAPE": "LANDSCAPE",
        "OPEN_SPACE": "OPEN_SPACE",
        "UTILITY_YARD": "UTILITY_YARD",
        "VEHICLE_ACCESS": "VEHICLE_ACCESS",
        "SHAFT": "SHAFT",
        "PORCH": "PORCH",
    }
    try:
        return mapping[kind]  # type: ignore[return-value]
    except KeyError as exc:
        raise ValueError(f"Unsupported purposeful site-space kind: {kind!r}.") from exc


def _numerical_lattice_tolerance_mm2(
    envelope: IntPolygon,
    *,
    solver_step_mm: int,
) -> int:
    """Allow only the deterministic positive-edge lattice residue.

    CP-SAT dimensions are represented in complete solver cells. A rectangular
    9144 mm dimension on a 10 mm lattice therefore has a representable extent
    of 9140 mm. That 4 mm strip is numerical residue, not architectural dead
    space.
    """

    if solver_step_mm <= 1 or envelope.holes:
        return _BASE_NUMERICAL_TOLERANCE_MM2

    points = envelope.outer
    xs = {point.x_mm for point in points}
    ys = {point.y_mm for point in points}

    if len(xs) != 2 or len(ys) != 2:
        return _BASE_NUMERICAL_TOLERANCE_MM2

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    width = max_x - min_x
    depth = max_y - min_y

    lattice_width = width // solver_step_mm * solver_step_mm
    lattice_depth = depth // solver_step_mm * solver_step_mm

    exact_area = width * depth
    lattice_area = lattice_width * lattice_depth
    lattice_residue = max(0, exact_area - lattice_area)

    return max(
        _BASE_NUMERICAL_TOLERANCE_MM2,
        lattice_residue,
    )


def _residual_regions(
    residual_geometry: BaseGeometry,
) -> tuple[ResidualRegion, ...]:
    if residual_geometry.is_empty:
        return ()

    geometries: tuple[Polygon, ...]

    if isinstance(residual_geometry, Polygon):
        geometries = (residual_geometry,)
    elif isinstance(
        residual_geometry,
        (MultiPolygon, GeometryCollection),
    ):
        geometries = tuple(
            geometry for geometry in residual_geometry.geoms if isinstance(geometry, Polygon)
        )
    else:
        geometries = ()

    regions: list[ResidualRegion] = []
    for geometry in geometries:
        area_mm2 = round(geometry.area)
        if area_mm2 <= 0:
            continue

        centroid = geometry.centroid
        min_x, min_y, max_x, max_y = geometry.bounds

        regions.append(
            ResidualRegion(
                area_mm2=area_mm2,
                centroid_x_mm=round(centroid.x),
                centroid_y_mm=round(centroid.y),
                min_x_mm=round(min_x),
                min_y_mm=round(min_y),
                max_x_mm=round(max_x),
                max_y_mm=round(max_y),
            )
        )

    return tuple(
        sorted(
            regions,
            key=lambda item: (
                -item.area_mm2,
                item.min_x_mm,
                item.min_y_mm,
                item.max_x_mm,
                item.max_y_mm,
            ),
        )
    )


def analyze_floor_site_accounting(
    *,
    envelope: IntPolygon,
    floor: Floor,
    solver_step_mm: int,
) -> SiteAccountingAnalysis:
    """Measure purposeful spatial utilization from canonical geometry.

    Classified land is the geometric union of:
    - canonical room/program polygons; and
    - explicit PurposefulSiteSpace polygons.

    No residual geometry is silently promoted to open space. Purposeful site
    polygons must be explicit, inside the confirmed envelope, and must not
    overlap any other classified polygon.
    """

    envelope_shape = _polygon_shape(envelope)
    envelope_area_mm2 = round(envelope_shape.area)

    room_shapes = tuple(_polygon_shape(room.polygon) for room in floor.rooms)
    site_space_shapes = tuple(_polygon_shape(space.polygon) for space in floor.site_spaces)

    classified_shapes = (
        *room_shapes,
        *site_space_shapes,
    )

    for shape in classified_shapes:
        if not envelope_shape.covers(shape):
            raise ValueError(
                "Canonical classified geometry extends outside the confirmed buildable envelope."
            )

    if classified_shapes:
        classified_union = unary_union(classified_shapes)
        classified_union_area_mm2 = round(classified_union.area)
        residual_geometry = envelope_shape.difference(classified_union)
    else:
        classified_union_area_mm2 = 0
        residual_geometry = envelope_shape

    room_allocations = tuple(
        SpaceAllocation(
            category=_room_category(room.room_type.value),
            label=f"{room.room_type.value}:{room.id}",
            area_mm2=round(shape.area),
        )
        for room, shape in zip(
            floor.rooms,
            room_shapes,
            strict=True,
        )
    )

    site_space_allocations = tuple(
        SpaceAllocation(
            category=_site_space_category(space.kind.value),
            label=f"{space.kind.value}:{space.id}",
            area_mm2=round(shape.area),
        )
        for space, shape in zip(
            floor.site_spaces,
            site_space_shapes,
            strict=True,
        )
    )

    allocations = (
        *room_allocations,
        *site_space_allocations,
    )

    allocation_sum = sum(item.area_mm2 for item in allocations)

    if allocation_sum != classified_union_area_mm2:
        raise ValueError(
            "Canonical classified polygons overlap; site accounting cannot "
            "double-count room or purposeful-site geometry."
        )

    accounting = close_site_accounting(
        envelope_area_mm2=envelope_area_mm2,
        allocations=allocations,
    )

    tolerance_mm2 = _numerical_lattice_tolerance_mm2(
        envelope,
        solver_step_mm=solver_step_mm,
    )

    return SiteAccountingAnalysis(
        accounting=accounting,
        residual_regions=_residual_regions(residual_geometry),
        numerical_tolerance_mm2=tolerance_mm2,
        unexplained_residual_area_mm2=max(
            0,
            accounting.residual_area_mm2 - tolerance_mm2,
        ),
    )


def require_geometric_site_accounting_closed(
    analysis: SiteAccountingAnalysis,
) -> None:
    if analysis.unexplained_residual_area_mm2 > 0:
        residual_m2 = analysis.unexplained_residual_area_mm2 / 1_000_000
        raise ValueError(
            "Unexplained geometric site residual remains after numerical "
            f"lattice tolerance: {residual_m2:.2f} m2. Every remaining region "
            "must be allocated to the program or explicitly classified as "
            "courtyard, shaft, setback, landscape, utility yard, porch, "
            "vehicle access, or other purposeful open space."
        )
