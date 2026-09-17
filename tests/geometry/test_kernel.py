import pytest

from ai_vastu.geometry import InvalidGeometryError, VerifiedGeometryKernel
from ai_vastu.plan_schema import IntPoint, IntPolygon


def rect(x1: int, y1: int, x2: int, y2: int) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=x1, y_mm=y1),
            IntPoint(x_mm=x2, y_mm=y1),
            IntPoint(x_mm=x2, y_mm=y2),
            IntPoint(x_mm=x1, y_mm=y2),
        )
    )


def test_intersection_union_difference_are_exact() -> None:
    kernel = VerifiedGeometryKernel()
    a = rect(0, 0, 100, 100)
    b = rect(50, 0, 150, 100)

    intersection = kernel.intersection((a,), (b,))
    union = kernel.union((a, b))
    difference = kernel.difference((a,), (b,))

    assert sum(kernel.area2(p) for p in intersection.polygons) == 10_000
    assert sum(kernel.area2(p) for p in union.polygons) == 30_000
    assert sum(kernel.area2(p) for p in difference.polygons) == 10_000


def test_contains_including_boundary() -> None:
    kernel = VerifiedGeometryKernel()
    outer = rect(0, 0, 100, 100)
    inside = rect(0, 20, 50, 80)
    outside = rect(90, 90, 110, 110)
    assert kernel.contains(outer, inside)
    assert not kernel.contains(outer, outside)


def test_offset_rectangle_expands_by_exact_integer_mm() -> None:
    kernel = VerifiedGeometryKernel()
    result = kernel.offset(rect(0, 0, 100, 100), 10)
    assert len(result.polygons) == 1
    assert kernel.area2(result.polygons[0]) == 28_800


def test_invalid_self_intersection_fails_closed() -> None:
    bowtie = IntPolygon(
        outer=(
            IntPoint(x_mm=0, y_mm=0),
            IntPoint(x_mm=100, y_mm=100),
            IntPoint(x_mm=0, y_mm=100),
            IntPoint(x_mm=100, y_mm=0),
        )
    )
    kernel = VerifiedGeometryKernel()
    with pytest.raises(InvalidGeometryError):
        kernel.union((bowtie,))


def test_union_preserves_an_explicit_hole() -> None:
    kernel = VerifiedGeometryKernel()
    donut = IntPolygon(
        outer=(
            IntPoint(x_mm=0, y_mm=0),
            IntPoint(x_mm=100, y_mm=0),
            IntPoint(x_mm=100, y_mm=100),
            IntPoint(x_mm=0, y_mm=100),
        ),
        holes=(
            (
                IntPoint(x_mm=25, y_mm=25),
                IntPoint(x_mm=25, y_mm=75),
                IntPoint(x_mm=75, y_mm=75),
                IntPoint(x_mm=75, y_mm=25),
            ),
        ),
    )
    result = kernel.union((donut,))
    assert len(result.polygons) == 1
    assert len(result.polygons[0].holes) == 1
    assert kernel.area2(result.polygons[0]) == 15_000
