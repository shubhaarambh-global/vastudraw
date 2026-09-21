from pathlib import Path

from ai_vastu.plan_schema import PLAN_SCHEMA_VERSION, PlanDocument

ROOT = Path(__file__).resolve().parents[1]


def test_phase1_governance_files_exist() -> None:
    required = [
        ROOT / "docs/architecture/phase-1-freeze.md",
        ROOT / "docs/adr/ADR-013-fixed-angle-unit.md",
        ROOT / "docs/adr/ADR-014-canonical-json-hash.md",
        ROOT / "packages/contracts/schema/plan-document.schema.json",
    ]
    assert all(path.is_file() for path in required)


def test_phase1_schema_contract() -> None:
    # The canonical contract intentionally evolved to 1.1.0 with an explicit
    # migration; the original Phase 1 root-ownership invariants still hold.
    assert PLAN_SCHEMA_VERSION == "1.1.0"
    assert "rooms" not in PlanDocument.model_fields
    assert "walls" not in PlanDocument.model_fields
