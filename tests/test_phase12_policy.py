from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase12_canvas_dependencies_are_frontend_only() -> None:
    for path in (ROOT / "python").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "react-konva" not in text
        assert "konva" not in text.lower()


def test_phase12_editor_contract_preserves_plan_authority() -> None:
    contract = (ROOT / "docs/editor/phase-12-contract.md").read_text(encoding="utf-8")
    assert "PlanDocument" in contract
    assert "never writes pixel values" in contract
    assert "integer-mm commands" in contract
