from pathlib import Path

from ai_vastu.constraints import CONSTRAINT_PROBLEM_VERSION
from ai_vastu.plan_schema import PLAN_SCHEMA_VERSION
from ai_vastu.vastu_spec import SpecLifecycle, load_vastu_spec_directory

ROOT = Path(__file__).resolve().parents[1]


def test_phase6_governance_files_exist() -> None:
    required = [
        ROOT / "docs/architecture/phase-6-freeze.md",
        ROOT / "docs/architecture/phase-6-validation.md",
        ROOT / "docs/adr/ADR-023-solver-agnostic-constraint-problem.md",
        ROOT / "docs/adr/ADR-024-no-silent-architectural-defaults.md",
        ROOT / "docs/constraints/compiler-contract.md",
    ]
    assert all(path.is_file() for path in required)


def test_phase7_keeps_phase6_and_plan_contract_versions_stable() -> None:
    assert PLAN_SCHEMA_VERSION == "1.0.0"
    assert CONSTRAINT_PROBLEM_VERSION == "1.0.0"


def test_phase7_does_not_prevent_later_reviewed_vastu_release() -> None:
    spec = load_vastu_spec_directory(ROOT / "docs/vastu/spec-v1.0")

    if spec.manifest.lifecycle is SpecLifecycle.DRAFT:
        assert spec.manifest.production_rule_count == 0
        assert spec.rule_records == ()
        assert spec.production_ready is False
        return

    assert spec.manifest.lifecycle is SpecLifecycle.FROZEN
    assert spec.manifest.production_rule_count == len(spec.rule_records)
    assert spec.manifest.production_rule_count > 0
    assert spec.production_ready is True

def test_phase7_adds_solver_but_not_cad_export_dependencies() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert "ortools==9.15.6755" in pyproject

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