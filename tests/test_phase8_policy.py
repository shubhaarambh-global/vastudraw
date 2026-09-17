from pathlib import Path

from ai_vastu.architectural_geometry import ARCHITECTURAL_GEOMETRY_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_phase8_governance_files_exist() -> None:
    required = [
        ROOT / "docs/architecture/phase-8-freeze.md",
        ROOT / "docs/architecture/phase-8-validation.md",
        ROOT / "docs/adr/ADR-027-architectural-geometry-builder.md",
        ROOT / "docs/adr/ADR-028-wall-topology-and-deterministic-identity.md",
        ROOT / "docs/geometry/phase-8-contract.md",
    ]
    assert all(path.is_file() for path in required)


def test_phase8_geometry_contract_version_is_explicit() -> None:
    assert ARCHITECTURAL_GEOMETRY_VERSION == "1.0.0"


def test_phase8_does_not_pull_export_dependencies() -> None:
    python_root = ROOT / "python/ai_vastu"
    for path in python_root.rglob("*.py"):
        relative = path.relative_to(python_root)
        if relative.parts and relative.parts[0] == "exporting":
            continue
        source = path.read_text(encoding="utf-8").lower()
        assert "import ezdxf" not in source
        assert "from ezdxf" not in source
        assert "import reportlab" not in source
        assert "from reportlab" not in source


def test_phase8_does_not_hide_wall_defaults() -> None:
    source = (ROOT / "python/ai_vastu/architectural_geometry/models.py").read_text(encoding="utf-8")
    assert "external_wall_thickness_mm: PositiveMM" in source
    assert "internal_wall_thickness_mm: PositiveMM" in source
    assert "external_wall_thickness_mm: PositiveMM =" not in source
    assert "internal_wall_thickness_mm: PositiveMM =" not in source
