from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vendor_dependencies_are_confined_to_explicit_adapters() -> None:
    allowed_by_import = {
        "import ezdxf": {
            ROOT / "python/ai_vastu/exporting/dxf_exporter.py",
            ROOT / "python/ai_vastu/exporting/dxf_importer.py",
        },
        "from ezdxf": {
            ROOT / "python/ai_vastu/exporting/dxf_exporter.py",
            ROOT / "python/ai_vastu/exporting/dxf_importer.py",
        },
        "from PIL": {
            ROOT / "python/ai_vastu/exporting/jpeg_exporter.py",
            ROOT / "python/ai_vastu/media_validation_adapter.py",
        },
        "from reportlab": {
            ROOT / "python/ai_vastu/exporting/pdf_exporter.py",
        },
    }
    for path in (ROOT / "python/ai_vastu").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for import_marker, allowed in allowed_by_import.items():
            if import_marker in text:
                assert path in allowed, (
                    f"Vendor dependency leaked into {path.relative_to(ROOT)}"
                )


def test_phase13_has_no_dwg_backend_claim() -> None:
    export_root = ROOT / "python/ai_vastu/exporting"
    names = {path.name.lower() for path in export_root.glob("*.py")}
    assert not any("dwg" in name for name in names)


def test_all_exporters_are_driven_by_drawing_scene() -> None:
    for filename in ("jpeg_exporter.py", "pdf_exporter.py", "dxf_exporter.py"):
        text = (ROOT / "python/ai_vastu/exporting" / filename).read_text(encoding="utf-8")
        assert "DrawingScene" in text
        assert "PlanDocument" not in text
