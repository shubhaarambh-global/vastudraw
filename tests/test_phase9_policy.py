from pathlib import Path

from ai_vastu.plan_schema import PLAN_SCHEMA_VERSION
from ai_vastu.validation import VALIDATOR_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_phase9_governance_files_exist() -> None:
    required = [
        ROOT / "docs/architecture/phase-9-freeze.md",
        ROOT / "docs/architecture/phase-9-validation.md",
        ROOT / "docs/adr/ADR-029-fail-closed-architectural-validation.md",
        ROOT / "docs/adr/ADR-030-exact-clear-dimensions-and-circulation.md",
        ROOT / "docs/validation/phase-9-contract.md",
    ]
    assert all(path.is_file() for path in required)


def test_phase9_contract_versions_are_explicit_and_plan_schema_stays_stable() -> None:
    assert PLAN_SCHEMA_VERSION == "1.0.0"
    assert VALIDATOR_VERSION == "1.0.0"


def test_phase9_uses_existing_geometry_stack_without_export_dependencies() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert "pyclipr==0.1.8" in pyproject
    assert "shapely==2.1.2" in pyproject

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

def test_phase9_validator_does_not_import_ortools() -> None:
    validation_root = ROOT / "python/ai_vastu/validation"
    for path in validation_root.rglob("*.py"):
        assert "ortools" not in path.read_text(encoding="utf-8").lower()
