from ai_vastu.geometry import area2_polygon, signed_area2_ring
from ai_vastu.plan_schema import IntPoint, IntPolygon


def test_exact_half_square_mm_area_is_preserved_as_twice_area() -> None:
    triangle = IntPolygon(
        outer=(IntPoint(x_mm=0, y_mm=0), IntPoint(x_mm=1, y_mm=0), IntPoint(x_mm=0, y_mm=1))
    )
    assert area2_polygon(triangle) == 1
    assert signed_area2_ring(triangle.outer) == 1


def test_hole_area_is_subtracted_exactly() -> None:
    polygon = IntPolygon(
        outer=(
            IntPoint(x_mm=0, y_mm=0),
            IntPoint(x_mm=10, y_mm=0),
            IntPoint(x_mm=10, y_mm=10),
            IntPoint(x_mm=0, y_mm=10),
        ),
        holes=(
            (
                IntPoint(x_mm=2, y_mm=2),
                IntPoint(x_mm=2, y_mm=8),
                IntPoint(x_mm=8, y_mm=8),
                IntPoint(x_mm=8, y_mm=2),
            ),
        ),
    )
    assert area2_polygon(polygon) == 128
