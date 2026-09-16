from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_governance_files_exist() -> None:
    required = [
        ROOT / "THIRD_PARTY.md",
        ROOT / "docs/architecture/phase-0-freeze.md",
        ROOT / "docs/adr/ADR-001-canonical-units.md",
        ROOT / "docs/adr/ADR-002-coordinate-orientation.md",
        ROOT / "docs/adr/ADR-003-plan-document-ownership.md",
        ROOT / "docs/adr/ADR-004-geometry-kernels.md",
        ROOT / "docs/adr/ADR-005-cp-sat-planner.md",
        ROOT / "docs/adr/ADR-006-solver-resolution.md",
        ROOT / "docs/adr/ADR-007-vastu-rule-lifecycle.md",
        ROOT / "docs/adr/ADR-008-editor-renderer.md",
        ROOT / "docs/adr/ADR-009-drawing-scene.md",
        ROOT / "docs/adr/ADR-010-dxf-backend.md",
        ROOT / "docs/adr/ADR-011-dwg-qualification.md",
        ROOT / "docs/adr/ADR-012-reproducibility.md",
    ]
    assert all(path.is_file() for path in required)
