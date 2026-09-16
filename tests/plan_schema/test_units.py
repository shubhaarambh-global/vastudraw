from decimal import Decimal

import pytest

from ai_vastu.plan_schema import LengthUnit, quantize_angle_udeg, quantize_length_mm


def test_exact_metric_and_imperial_conversions() -> None:
    assert quantize_length_mm("30", LengthUnit.FT).mm == 9_144
    assert quantize_length_mm("50", LengthUnit.FT).mm == 15_240
    assert quantize_length_mm("10", LengthUnit.M).mm == 10_000


def test_submillimetre_input_is_explicitly_quantized() -> None:
    result = quantize_length_mm(Decimal("0.125"), LengthUnit.IN)
    assert result.exact_mm == "3.175"
    assert result.mm == 3
    assert result.rounding_delta_mm == "-0.175"


def test_half_up_rounding_is_deterministic() -> None:
    assert quantize_length_mm("2.5", LengthUnit.MM).mm == 3


def test_float_input_is_rejected() -> None:
    with pytest.raises(TypeError, match="binary floating-point"):
        quantize_length_mm(3.65, LengthUnit.M)  # type: ignore[arg-type]


def test_angle_is_fixed_point_and_normalized() -> None:
    assert quantize_angle_udeg("13.72").microdegrees == 13_720_000
    assert quantize_angle_udeg("370").microdegrees == 10_000_000
    assert quantize_angle_udeg("-10").microdegrees == 350_000_000
