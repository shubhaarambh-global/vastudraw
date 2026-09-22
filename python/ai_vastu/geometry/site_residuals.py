from __future__ import annotations

from ai_vastu.plan_schema import IntPolygon

from .shapely_validator import (
    measure_site_residual_polygons_shapely,
    polygon_has_usable_core_shapely,
)
from .types import SiteResidualPolygonMeasurement


def polygon_has_usable_core(
    polygon: IntPolygon,
    *,
    minimum_width_mm: int,
) -> bool:
    """Return whether a residual polygon has a meaningful usable core.

    The implementation lives inside the geometry vendor adapter so architectural
    modules never import or expose vendor geometry types.
    """

    return polygon_has_usable_core_shapely(
        polygon,
        minimum_width_mm=minimum_width_mm,
    )


def measure_site_residual_polygons(
    envelope: IntPolygon,
    occupied_polygons: tuple[IntPolygon, ...],
    *,
    road_boundary_side: str | None,
    solver_step_mm: int,
) -> SiteResidualPolygonMeasurement:
    """Return exact residual polygons through the geometry adapter boundary."""

    return measure_site_residual_polygons_shapely(
        envelope,
        occupied_polygons,
        road_boundary_side=road_boundary_side,
        solver_step_mm=solver_step_mm,
    )
