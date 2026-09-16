from __future__ import annotations

from ai_vastu.geometry import VerifiedGeometryKernel, area2_polygon
from ai_vastu.plan_schema import IntPolygon

from .models import BasisPoints, GeometrySemantic, SubjectAttribute, VastuFact


def area_overlap_basis_points(
    *,
    subject: IntPolygon,
    zone: IntPolygon,
    kernel: VerifiedGeometryKernel | None = None,
) -> BasisPoints:
    """Return subject-area overlap with zone in basis points, deterministically.

    The ratio is computed from exact doubled integer areas. The final basis-point
    value uses integer half-up rounding and never changes canonical geometry.
    """
    subject_area2 = area2_polygon(subject)
    if subject_area2 <= 0:
        raise ValueError("Subject polygon must have positive area.")

    geometry = kernel or VerifiedGeometryKernel()
    intersection = geometry.intersection((subject,), (zone,))
    overlap_area2 = sum(area2_polygon(polygon) for polygon in intersection.polygons)
    numerator = overlap_area2 * 10_000
    return min(10_000, (numerator + subject_area2 // 2) // subject_area2)


def make_area_overlap_fact(
    *,
    entity_id: str,
    entity_type: str,
    metric_key: str,
    subject: IntPolygon,
    zone: IntPolygon,
    attributes: tuple[SubjectAttribute, ...] = (),
    evidence: tuple[str, ...] = (),
    kernel: VerifiedGeometryKernel | None = None,
) -> VastuFact:
    return VastuFact(
        entity_id=entity_id,
        entity_type=entity_type,
        attributes=attributes,
        geometry_semantic=GeometrySemantic.AREA_OVERLAP_PERCENT,
        metric_key=metric_key,
        value=area_overlap_basis_points(subject=subject, zone=zone, kernel=kernel),
        evidence=evidence,
    )
