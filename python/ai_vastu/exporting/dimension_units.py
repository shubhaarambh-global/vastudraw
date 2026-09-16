from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from math import isfinite

from .models import DimensionDisplayUnit

_EIGHTHS_PER_INCH = 8
_EIGHTHS_PER_FOOT = 12 * _EIGHTHS_PER_INCH
_MM_PER_INCH = Decimal("25.4")


def _round_decimal_to_int(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _fraction_text(eighths: int) -> str:
    if eighths == 0:
        return ""
    from math import gcd

    divisor = gcd(eighths, _EIGHTHS_PER_INCH)
    return f"{eighths // divisor}/{_EIGHTHS_PER_INCH // divisor}"


def format_dimension_length_mm(
    length_mm: float | int,
    unit: DimensionDisplayUnit,
) -> str:
    """Format dimensions without changing canonical millimetre geometry."""

    numeric = float(length_mm)
    if not isfinite(numeric) or numeric < 0:
        raise ValueError("Dimension length must be a finite non-negative value.")

    decimal_mm = Decimal(str(numeric))
    if unit is DimensionDisplayUnit.METRES:
        metres = (decimal_mm / Decimal("1000")).quantize(
            Decimal("0.001"),
            rounding=ROUND_HALF_UP,
        )
        return f"{metres:.3f} m"

    total_eighths = _round_decimal_to_int((decimal_mm / _MM_PER_INCH) * Decimal(_EIGHTHS_PER_INCH))
    feet, remaining = divmod(total_eighths, _EIGHTHS_PER_FOOT)
    inches, eighths = divmod(remaining, _EIGHTHS_PER_INCH)
    fraction = _fraction_text(eighths)
    inch_text = f"{inches} {fraction}" if fraction else str(inches)
    return f"{feet}'-{inch_text}\""
