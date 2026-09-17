from __future__ import annotations

from pathlib import Path

from ai_vastu.plan_schema import PLAN_SCHEMA_VERSION
from ai_vastu.vastu_spec import VASTU_SPEC_VERSION, SpecLifecycle, load_vastu_spec_directory

ROOT = Path(__file__).resolve().parents[1]


def test_phase5_governance_files_exist() -> None:
    required = [
        ROOT / "docs/architecture/phase-5-freeze.md",
        ROOT / "docs/architecture/phase-5-validation.md",
        ROOT / "docs/adr/ADR-021-vastu-spec-authoring-and-approval.md",
        ROOT / "docs/adr/ADR-022-vastu-spec-release-manifest.md",
        ROOT / "docs/vastu/spec-v1.0/manifest.json",
        ROOT / "docs/vastu/spec-v1.0/sources.json",
    ]
    assert all(path.is_file() for path in required)


def test_phase5_keeps_plan_document_schema_version_stable() -> None:
    assert PLAN_SCHEMA_VERSION == "1.0.0"
    assert VASTU_SPEC_VERSION == "1.0.0"


def test_repository_spec_requires_review_before_production_freeze() -> None:
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


def test_phase5_rule_files_require_a_reviewed_release() -> None:
    spec = load_vastu_spec_directory(ROOT / "docs/vastu/spec-v1.0")
    rules = sorted((ROOT / "docs/vastu/spec-v1.0/rules").glob("*.json"))

    if spec.manifest.lifecycle is SpecLifecycle.DRAFT:
        assert rules == []
        return

    assert spec.manifest.lifecycle is SpecLifecycle.FROZEN
    assert len(rules) == spec.manifest.production_rule_count
    assert len(rules) > 0
    assert spec.production_ready is True


def test_phase5_does_not_pull_solver_or_cad_dependencies() -> None:
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
