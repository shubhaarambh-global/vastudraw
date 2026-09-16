from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ai_vastu.plan_schema import IntPolygon


class BooleanOperation(StrEnum):
    UNION = "union"
    INTERSECTION = "intersection"
    DIFFERENCE = "difference"
    XOR = "xor"


@dataclass(frozen=True, slots=True)
class GeometryResult:
    polygons: tuple[IntPolygon, ...]

    @property
    def is_empty(self) -> bool:
        return not self.polygons
