from __future__ import annotations

from pathlib import Path

from ai_vastu.plan_schema import PLAN_SCHEMA_VERSION
from ai_vastu.vastu import GeometrySemantic, RuleLifecycle

ROOT = Path(__file__).resolve().parents[1]


def test_phase4_governance_files_exist() -> None:
    required = [
        ROOT / "docs/architecture/phase-4-freeze.md",
        ROOT / "docs/architecture/phase-4-validation.md",
        ROOT / "docs/adr/ADR-019-vastu-rule-representation-and-lifecycle.md",
        ROOT / "docs/adr/ADR-020-vastu-rule-bundle-and-provenance.md",
    ]
    assert all(path.is_file() for path in required)


def test_phase4_keeps_plan_document_schema_version_stable() -> None:
    assert PLAN_SCHEMA_VERSION == "1.0.0"


def test_phase4_has_required_rule_lifecycle_and_geometry_semantics() -> None:
    assert set(RuleLifecycle) == {
        RuleLifecycle.DRAFT,
        RuleLifecycle.REVIEWED,
        RuleLifecycle.FROZEN,
        RuleLifecycle.RETIRED,
    }
    assert GeometrySemantic.AREA_OVERLAP_PERCENT.value == "AREA_OVERLAP_PERCENT"
    assert GeometrySemantic.CENTROID_IN_ZONE.value == "CENTROID_IN_ZONE"


def test_phase4_contains_no_production_vastu_rule_catalog() -> None:
    vastu_root = ROOT / "python/ai_vastu/vastu"
    assert not (vastu_root / "rules").exists()
    assert not (ROOT / "docs/vastu/vastu-spec-v1.0.json").exists()


def test_phase4_does_not_pull_future_solver_or_cad_dependencies() -> None:
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