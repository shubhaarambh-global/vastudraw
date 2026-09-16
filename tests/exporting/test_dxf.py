from __future__ import annotations

from io import StringIO

import ezdxf
from ezdxf.enums import InsertUnits

from ai_vastu.exporting import DxfExportConfig, build_drawing_scene, render_dxf

from .helpers import export_plan


def test_dxf_export_round_trips_mm_geometry_and_native_dimension() -> None:
    scene = build_drawing_scene(export_plan())
    artifact = render_dxf(scene, DxfExportConfig())
    text = artifact.content.decode("utf-8")
    doc = ezdxf.read(StringIO(text))
    assert doc.units == InsertUnits.Millimeters
    assert "AIA_WALL_EXT" in doc.layers
    assert "AIA_WALL_INT" in doc.layers
    assert "AIA_DIM" in doc.layers
    modelspace = doc.modelspace()
    assert len(modelspace.query('LWPOLYLINE[layer=="AIA_WALL_INT"]')) == 2
    assert len(modelspace.query('DIMENSION[layer=="AIA_DIM"]')) == 1
    assert artifact.scene_hash == scene.scene_hash


def test_dxf_export_is_deterministic_with_fixed_metadata() -> None:
    scene = build_drawing_scene(export_plan())
    first = render_dxf(scene, DxfExportConfig())
    second = render_dxf(scene, DxfExportConfig())
    assert first.content == second.content
