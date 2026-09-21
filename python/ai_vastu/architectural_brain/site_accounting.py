from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from ai_vastu.geometry import measure_site_partition
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

    classified_polygons = (
        *(room.polygon for room in floor.rooms),
        *(space.polygon for space in floor.site_spaces),
    )
    measurement = measure_site_partition(envelope, classified_polygons)
    room_areas = measurement.classified_item_areas_mm2[: len(floor.rooms)]
    site_space_areas = measurement.classified_item_areas_mm2[len(floor.rooms) :]

    room_allocations = tuple(
        SpaceAllocation(
            category=_room_category(room.room_type.value),
            label=f"{room.room_type.value}:{room.id}",
            area_mm2=area_mm2,
        )
        for room, area_mm2 in zip(
            floor.rooms,
            room_areas,
            strict=True,
        )
    )

    site_space_allocations = tuple(
        SpaceAllocation(
            category=_site_space_category(space.kind.value),
            label=f"{space.kind.value}:{space.id}",
            area_mm2=area_mm2,
        )
        for space, area_mm2 in zip(
            floor.site_spaces,
            site_space_areas,
            strict=True,
        )
    )

    allocations = (
        *room_allocations,
        *site_space_allocations,
    )

    allocation_sum = sum(item.area_mm2 for item in allocations)

    if allocation_sum != measurement.classified_union_area_mm2:
        raise ValueError(
            "Canonical classified polygons overlap; site accounting cannot "
            "double-count room or purposeful-site geometry."
        )

    accounting = close_site_accounting(
        envelope_area_mm2=measurement.envelope_area_mm2,
        allocations=allocations,
    )

    tolerance_mm2 = _numerical_lattice_tolerance_mm2(
        envelope,
        solver_step_mm=solver_step_mm,
    )

    return SiteAccountingAnalysis(
        accounting=accounting,
        residual_regions=tuple(
            ResidualRegion(
                area_mm2=region.area_mm2,
                centroid_x_mm=region.centroid_x_mm,
                centroid_y_mm=region.centroid_y_mm,
                min_x_mm=region.min_x_mm,
                min_y_mm=region.min_y_mm,
                max_x_mm=region.max_x_mm,
                max_y_mm=region.max_y_mm,
            )
            for region in measurement.residual_regions
        ),
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
