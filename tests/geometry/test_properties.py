from hypothesis import given, settings
from hypothesis import strategies as st

from ai_vastu.geometry import VerifiedGeometryKernel
from ai_vastu.plan_schema import IntPoint, IntPolygon


def rect(x: int, y: int, width: int, height: int) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=x, y_mm=y),
            IntPoint(x_mm=x + width, y_mm=y),
            IntPoint(x_mm=x + width, y_mm=y + height),
            IntPoint(x_mm=x, y_mm=y + height),
        )
    )


rectangles = st.tuples(
    st.integers(-100_000, 100_000),
    st.integers(-100_000, 100_000),
    st.integers(1, 10_000),
    st.integers(1, 10_000),
).map(lambda v: rect(*v))


@settings(max_examples=500, deadline=None)
@given(rectangles)
def test_identity_difference_is_empty(a: IntPolygon) -> None:
    kernel = VerifiedGeometryKernel()
    assert kernel.difference((a,), (a,)).is_empty


@settings(max_examples=500, deadline=None)
@given(rectangles)
def test_identity_intersection_preserves_area(a: IntPolygon) -> None:
    kernel = VerifiedGeometryKernel()
    out = kernel.intersection((a,), (a,))
    assert sum(kernel.area2(p) for p in out.polygons) == kernel.area2(a)


@settings(max_examples=500, deadline=None)
@given(rectangles, rectangles)
def test_intersection_area_never_exceeds_either_input(a: IntPolygon, b: IntPolygon) -> None:
    kernel = VerifiedGeometryKernel()
    out = kernel.intersection((a,), (b,))
    area = sum(kernel.area2(p) for p in out.polygons)
    assert area <= kernel.area2(a)
    assert area <= kernel.area2(b)


@settings(max_examples=500, deadline=None)
@given(rectangles, rectangles)
def test_union_area_is_at_least_each_input(a: IntPolygon, b: IntPolygon) -> None:
    kernel = VerifiedGeometryKernel()
    out = kernel.union((a, b))
    area = sum(kernel.area2(p) for p in out.polygons)
    assert area >= kernel.area2(a)
    assert area >= kernel.area2(b)


@settings(max_examples=500, deadline=None)
@given(rectangles)
def test_zero_offset_is_identity(a: IntPolygon) -> None:
    kernel = VerifiedGeometryKernel()
    out = kernel.offset(a, 0)
    assert out.polygons == (a,)
