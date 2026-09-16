from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_export_vendor_dependencies_are_confined_to_export_adapters() -> None:
    allowed = {
        ROOT / "python/ai_vastu/exporting/dxf_exporter.py",
        ROOT / "python/ai_vastu/exporting/jpeg_exporter.py",
        ROOT / "python/ai_vastu/exporting/pdf_exporter.py",
    }
    for path in (ROOT / "python/ai_vastu").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        has_vendor_import = (
            "import ezdxf" in text
            or "from ezdxf" in text
            or "from PIL" in text
            or "from reportlab" in text
        )
        if has_vendor_import:
            assert path in allowed, (
                f"Export vendor dependency leaked into {path.relative_to(ROOT)}"
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
