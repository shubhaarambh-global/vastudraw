from pathlib import Path

from ai_vastu.solver import SOLVER_MODEL_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_phase7_governance_files_exist() -> None:
    required = [
        ROOT / "docs/architecture/phase-7-freeze.md",
        ROOT / "docs/architecture/phase-7-validation.md",
        ROOT / "docs/adr/ADR-025-cp-sat-rectangular-planner.md",
        ROOT / "docs/adr/ADR-026-solver-lattice-and-reproducibility.md",
        ROOT / "docs/solver/phase-7-contract.md",
    ]
    assert all(path.is_file() for path in required)


def test_phase7_solver_contract_version_is_explicit() -> None:
    assert SOLVER_MODEL_VERSION == "1.0.0"


def test_ortools_import_is_confined_to_solver_adapter() -> None:
    allowed = ROOT / "python/ai_vastu/solver/rectangular_cp_sat.py"
    for path in (ROOT / "python/ai_vastu").rglob("*.py"):
        if "ortools" in path.read_text(encoding="utf-8").lower():
            assert path == allowed, f"OR-Tools leaked outside adapter: {path.relative_to(ROOT)}"


def test_phase7_does_not_claim_vastu_optimization_without_frozen_rules() -> None:
    solver_source = (ROOT / "python/ai_vastu/solver/rectangular_cp_sat.py").read_text(
        encoding="utf-8"
    )
    assert "VastuResult" not in solver_source
    assert "vastu score" not in solver_source.lower()
