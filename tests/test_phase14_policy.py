from pathlib import Path

from ai_vastu.dwg import DWG_QUALIFICATION_VERSION, builtin_backend_candidates

ROOT = Path(__file__).resolve().parents[1]


def test_phase14_governance_files_exist() -> None:
    required = [
        ROOT / "docs/architecture/phase-14-freeze.md",
        ROOT / "docs/architecture/phase-14-validation.md",
        ROOT / "docs/adr/ADR-039-dwg-backend-qualification-boundary.md",
        ROOT / "docs/adr/ADR-040-dwg-provider-selection.md",
        ROOT / "docs/dwg/qualification-contract.md",
        ROOT / "docs/dwg/provider-assessment-2026-09-14.md",
    ]
    assert all(path.is_file() for path in required)


def test_phase14_dwg_contract_version_is_explicit() -> None:
    assert DWG_QUALIFICATION_VERSION == "1.0.0"


def test_no_dwg_binary_or_sdk_is_bundled() -> None:
    forbidden_suffixes = {".dwg", ".dll", ".so", ".dylib", ".exe"}
    repository_roots = ("python", "apps", "packages", "scripts", "docs", "third_party")
    for repository_root in repository_roots:
        for path in (ROOT / repository_root).rglob("*"):
            if path.is_file():
                assert path.suffix.lower() not in forbidden_suffixes


def test_libredwg_is_not_imported_into_production_python() -> None:
    for path in (ROOT / "python/ai_vastu").rglob("*.py"):
        source = path.read_text(encoding="utf-8").lower()
        assert "import libredwg" not in source
        assert "from libredwg" not in source


def test_provider_registry_is_evidence_backed_and_not_silent_fallback() -> None:
    candidates = builtin_backend_candidates()
    assert {item.backend_id for item in candidates} == {"oda-drawings-sdk", "gnu-libredwg"}
    assert all(item.source_url.startswith("https://") for item in candidates)
    assert all(item.bundled is False for item in candidates)
