from ai_vastu.geometry import ShapelyGeometryValidator, measure_site_residual_polygons
from ai_vastu.plan_schema import IntPoint, IntPolygon


def _rect(x0: int, y0: int, x1: int, y1: int) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=x0, y_mm=y0),
            IntPoint(x_mm=x1, y_mm=y0),
            IntPoint(x_mm=x1, y_mm=y1),
            IntPoint(x_mm=x0, y_mm=y1),
        )
    )


def test_residual_measurement_handles_shared_boundary_notches_without_self_intersection() -> None:
    envelope = _rect(0, 0, 10_000, 8_000)
    occupied = (
        _rect(0, 0, 6_760, 3_250),
        _rect(6_760, 0, 10_000, 2_000),
        _rect(2_000, 3_250, 6_760, 6_000),
    )

    result = measure_site_residual_polygons(
        envelope,
        occupied,
        road_boundary_side="EAST",
        solver_step_mm=10,
    )

    validator = ShapelyGeometryValidator()
    validator.validate_all(item.polygon for item in result.polygons)

    occupied_area = (
        6_760 * 3_250
        + (10_000 - 6_760) * 2_000
        + (6_760 - 2_000) * (6_000 - 3_250)
    )
    assert sum(item.area_mm2 for item in result.polygons) == 80_000_000 - occupied_area
