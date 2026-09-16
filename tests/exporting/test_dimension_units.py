from __future__ import annotations

from io import StringIO

import ezdxf
from ezdxf.enums import InsertUnits

from ai_vastu.exporting import (
    DimensionDisplayUnit,
    DxfExportConfig,
    PdfExportConfig,
    RasterExportConfig,
    build_drawing_scene,
    render_dxf,
)
from ai_vastu.exporting.dimension_units import format_dimension_length_mm

from .helpers import export_plan


def test_dimension_formatter_defaults_to_architectural_feet_inches() -> None:
    assert (
        format_dimension_length_mm(
            9_144,
            DimensionDisplayUnit.FEET_INCHES,
        )
        == "30'-0\""
    )
    assert (
        format_dimension_length_mm(
            3_213,
            DimensionDisplayUnit.FEET_INCHES,
        )
        == "10'-6 1/2\""
    )
    assert (
        format_dimension_length_mm(
            10_000,
            DimensionDisplayUnit.FEET_INCHES,
        )
        == "32'-9 3/4\""
    )


def test_dimension_formatter_supports_three_decimal_metres() -> None:
    assert (
        format_dimension_length_mm(
            9_144,
            DimensionDisplayUnit.METRES,
        )
        == "9.144 m"
    )
    assert (
        format_dimension_length_mm(
            10_000,
            DimensionDisplayUnit.METRES,
        )
        == "10.000 m"
    )


def test_export_configs_default_to_feet_inches_display() -> None:
    assert RasterExportConfig().dimension_unit is DimensionDisplayUnit.FEET_INCHES
    assert PdfExportConfig().dimension_unit is DimensionDisplayUnit.FEET_INCHES
    assert DxfExportConfig().dimension_unit is DimensionDisplayUnit.FEET_INCHES


def test_dxf_keeps_mm_geometry_with_selected_dimension_text() -> None:
    scene = build_drawing_scene(export_plan())

    imperial = render_dxf(scene, DxfExportConfig())
    imperial_doc = ezdxf.read(StringIO(imperial.content.decode("utf-8")))
    assert imperial_doc.units == InsertUnits.Millimeters
    imperial_dimension = imperial_doc.modelspace().query('DIMENSION[layer=="AIA_DIM"]')[0]
    assert imperial_dimension.dxf.text == "32'-9 3/4\""

    metric = render_dxf(
        scene,
        DxfExportConfig(dimension_unit=DimensionDisplayUnit.METRES),
    )
    metric_doc = ezdxf.read(StringIO(metric.content.decode("utf-8")))
    assert metric_doc.units == InsertUnits.Millimeters
    metric_dimension = metric_doc.modelspace().query('DIMENSION[layer=="AIA_DIM"]')[0]
    assert metric_dimension.dxf.text == "10.000 m"
