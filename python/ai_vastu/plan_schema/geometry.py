from __future__ import annotations

from typing import Annotated

from pydantic import Field, model_validator

from .base import FrozenModel
from .units import MM, PositiveMM

Ring = Annotated[tuple["IntPoint", ...], Field(min_length=3)]


class IntPoint(FrozenModel):
    x_mm: MM
    y_mm: MM


class IntPolygon(FrozenModel):
    """Canonical integer-mm polygon storage.

    Topological validity is intentionally not proven in Phase 1; that belongs to the
    geometry/validation phases. Rings are open: callers must not repeat the first point.
    """

    outer: Ring
    holes: tuple[Ring, ...] = ()

    @model_validator(mode="after")
    def reject_explicit_ring_closure(self) -> IntPolygon:
        rings = (self.outer, *self.holes)
        for ring in rings:
            if ring[0] == ring[-1]:
                raise ValueError("Polygon rings are stored open; do not repeat the first point.")
        return self


class AxisSegment(FrozenModel):
    start: IntPoint
    end: IntPoint

    @model_validator(mode="after")
    def reject_zero_length(self) -> AxisSegment:
        if self.start == self.end:
            raise ValueError("Axis segment start and end must differ.")
        return self


class RectangleSize(FrozenModel):
    width_mm: PositiveMM
    height_mm: PositiveMM
