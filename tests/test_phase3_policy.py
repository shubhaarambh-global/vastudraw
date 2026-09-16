from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_geometry_vendor_imports_are_confined_to_adapters() -> None:
    allowed = {
        ROOT / "python/ai_vastu/geometry/clipper_kernel.py",
        ROOT / "python/ai_vastu/geometry/shapely_validator.py",
    }
    for path in (ROOT / "python/ai_vastu").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "import pyclipr" in text or "from shapely" in text:
            assert path in allowed, (
                f"Geometry vendor dependency leaked into {path.relative_to(ROOT)}"
            )


def test_solver_vendor_does_not_leak_into_geometry_layer() -> None:
    for path in (ROOT / "python/ai_vastu/geometry").rglob("*.py"):
        assert "ortools" not in path.read_text(encoding="utf-8").lower()


def test_repository_still_has_no_unsourced_vastu_rule_catalog() -> None:
    assert not (ROOT / "python/ai_vastu/vastu/rules.json").exists()
