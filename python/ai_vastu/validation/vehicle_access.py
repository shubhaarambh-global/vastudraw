"""Canonical vehicle-access policy through the qualified geometry boundary."""

from ai_vastu.geometry import measure_vehicle_access_failures
from ai_vastu.plan_schema import PlanDocument


def validate_document_vehicle_access(document: PlanDocument) -> tuple[str, ...]:
    """Fail closed on inaccessible bays using canonical road/wall/opening geometry."""
    return measure_vehicle_access_failures(document)
