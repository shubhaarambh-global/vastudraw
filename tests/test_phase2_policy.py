from pathlib import Path
from uuid import UUID

from ai_vastu.plan_schema import PLAN_SCHEMA_VERSION, LengthUnit
from ai_vastu.plot import create_rectangular_plot, derive_edge_ids

ROOT = Path(__file__).resolve().parents[1]


def test_phase2_governance_files_exist() -> None:
    required = [
        ROOT / "docs/architecture/phase-2-freeze.md",
        ROOT / "docs/architecture/phase-2-validation.md",
        ROOT / "docs/adr/ADR-015-plot-construction-and-edge-identity.md",
        ROOT / "docs/adr/ADR-016-direction-and-facing-semantics.md",
    ]
    assert all(path.is_file() for path in required)


def test_phase2_does_not_change_plan_document_schema_version() -> None:
    assert PLAN_SCHEMA_VERSION == "1.0.0"


def test_plot_edge_ids_are_reproducible_not_random() -> None:
    plot_id = UUID("50000000-0000-0000-0000-000000000001")
    first = create_rectangular_plot(
        plot_id=plot_id,
        width_value=30,
        width_unit=LengthUnit.FT,
        depth_value=50,
        depth_unit=LengthUnit.FT,
    )
    second = create_rectangular_plot(
        plot_id=plot_id,
        width_value=30,
        width_unit=LengthUnit.FT,
        depth_value=50,
        depth_unit=LengthUnit.FT,
    )

    assert first.edge_ids == second.edge_ids == derive_edge_ids(plot_id, 4)


def test_phase3_has_not_pulled_future_solver_or_cad_dependencies() -> None:
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
