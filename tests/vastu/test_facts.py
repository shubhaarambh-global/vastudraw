from __future__ import annotations

from ai_vastu.plan_schema import IntPoint, IntPolygon
from ai_vastu.vastu import area_overlap_basis_points, make_area_overlap_fact


def rectangle(x0: int, y0: int, x1: int, y1: int) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=x0, y_mm=y0),
            IntPoint(x_mm=x1, y_mm=y0),
            IntPoint(x_mm=x1, y_mm=y1),
            IntPoint(x_mm=x0, y_mm=y1),
        )
    )


def test_area_overlap_fact_uses_exact_integer_geometry() -> None:
    subject = rectangle(0, 0, 10_000, 10_000)
    half = rectangle(0, 0, 5_000, 10_000)
    assert area_overlap_basis_points(subject=subject, zone=half) == 5_000


def test_area_overlap_fact_can_represent_full_containment() -> None:
    subject = rectangle(1_000, 1_000, 2_000, 2_000)
    zone = rectangle(0, 0, 3_000, 3_000)
    fact = make_area_overlap_fact(
        entity_id="space-01",
        entity_type="synthetic_space",
        metric_key="synthetic_zone_overlap_bp",
        subject=subject,
        zone=zone,
    )
    assert fact.value == 10_000
