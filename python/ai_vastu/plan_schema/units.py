from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import Field

INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1
MICRODEGREES_PER_DEGREE = 1_000_000
FULL_TURN_UDEG = 360 * MICRODEGREES_PER_DEGREE

MM = Annotated[int, Field(ge=INT64_MIN, le=INT64_MAX)]
NonNegativeMM = Annotated[int, Field(ge=0, le=INT64_MAX)]
PositiveMM = Annotated[int, Field(gt=0, le=INT64_MAX)]
MM2 = Annotated[int, Field(ge=0, le=INT64_MAX)]
PositiveMM2 = Annotated[int, Field(gt=0, le=INT64_MAX)]
MicroDegrees = Annotated[int, Field(ge=0, lt=FULL_TURN_UDEG)]
BasisPoints = Annotated[int, Field(ge=0, le=10_000)]
Priority100 = Annotated[int, Field(ge=0, le=100)]


class LengthUnit(StrEnum):
    MM = "mm"
    CM = "cm"
    M = "m"
    IN = "in"
    FT = "ft"


_LENGTH_TO_MM: dict[LengthUnit, Decimal] = {
    LengthUnit.MM: Decimal("1"),
    LengthUnit.CM: Decimal("10"),
    LengthUnit.M: Decimal("1000"),
    LengthUnit.IN: Decimal("25.4"),
    LengthUnit.FT: Decimal("304.8"),
}


@dataclass(frozen=True, slots=True)
class QuantizedLength:
    input_value: str
    input_unit: LengthUnit
    exact_mm: str
    mm: int
    rounding_delta_mm: str


@dataclass(frozen=True, slots=True)
class QuantizedAngle:
    input_degrees: str
    normalized_degrees: str
    microdegrees: int
    rounding_delta_degrees: str


def _decimal(value: Decimal | int | str) -> Decimal:
    if isinstance(value, (bool, float)):
        raise TypeError("Use Decimal, int, or str; binary floating-point input is not accepted.")
    try:
        result = value if isinstance(value, Decimal) else Decimal(value)
    except Exception as exc:  # pragma: no cover - Decimal gives several concrete exceptions
        raise ValueError(f"Invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise ValueError("Measurement must be finite.")
    return result


def _plain_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized.quantize(Decimal("1")), "f")
    return format(normalized, "f")


def quantize_length_mm(value: Decimal | int | str, unit: LengthUnit) -> QuantizedLength:
    """Convert a non-negative external length to canonical integer millimetres.

    Rounding is deterministic ROUND_HALF_UP to the nearest millimetre. Exact input and
    the rounding delta are returned so no quantization is silent.
    """

    numeric = _decimal(value)
    if numeric < 0:
        raise ValueError("Length measurements must be non-negative.")
    exact_mm = numeric * _LENGTH_TO_MM[unit]
    quantized = exact_mm.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    mm = int(quantized)
    if mm > INT64_MAX:
        raise OverflowError("Length exceeds canonical int64 millimetre range.")
    delta = quantized - exact_mm
    return QuantizedLength(
        input_value=_plain_decimal(numeric),
        input_unit=unit,
        exact_mm=_plain_decimal(exact_mm),
        mm=mm,
        rounding_delta_mm=_plain_decimal(delta),
    )


def quantize_angle_udeg(value_degrees: Decimal | int | str) -> QuantizedAngle:
    """Normalize degrees to [0, 360) and quantize to integer microdegrees."""

    numeric = _decimal(value_degrees)
    normalized = numeric % Decimal("360")
    exact_udeg = normalized * Decimal(MICRODEGREES_PER_DEGREE)
    quantized_udeg = exact_udeg.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    microdegrees = int(quantized_udeg) % FULL_TURN_UDEG
    quantized_degrees = Decimal(microdegrees) / Decimal(MICRODEGREES_PER_DEGREE)
    delta = quantized_degrees - normalized
    return QuantizedAngle(
        input_degrees=_plain_decimal(numeric),
        normalized_degrees=_plain_decimal(normalized),
        microdegrees=microdegrees,
        rounding_delta_degrees=_plain_decimal(delta),
    )
