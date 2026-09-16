from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_scoring_domain_has_no_geometry_or_solver_vendor_imports() -> None:
    for path in (ROOT / "python/ai_vastu/scoring").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "from shapely" not in text
        assert "import pyclipr" not in text
        assert "from ortools" not in text


def test_scoring_does_not_claim_vastu_mode_before_frozen_rules_exist() -> None:
    text = (ROOT / "python/ai_vastu/scoring/evaluator.py").read_text(encoding="utf-8")
    assert 'mode="ARCHITECTURAL_SOFT_CONSTRAINTS_V1"' in text
    assert "VASTU_SCORE" not in text
