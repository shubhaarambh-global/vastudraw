from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_checker() -> ModuleType:
    path = ROOT / "scripts" / "check-apinex-live.py"
    spec = importlib.util.spec_from_file_location("apinex_checker_under_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load APINEX checker.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checker_uses_real_services_and_lists_every_required_stage() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["apinex:live"] == (
        "node scripts/run-project-python.mjs scripts/check-apinex-live.py"
    )
    source = (ROOT / "scripts" / "check-apinex-live.py").read_text(
        encoding="utf-8"
    )
    for label in (
        "APINEX ENDPOINT",
        "APINEX MODEL INVENTORY",
        "APINEX TEXT",
        "APINEX STRUCTURED TEXT",
        "REQUIREMENTS TEXT",
        "PLAN PNG",
        "PLAN JPEG",
        "PLAN PDF-PATH",
        "STRICT JSON",
        "PROVENANCE",
        "CONTENT HASH",
    ):
        assert label in source
    assert "create_provider()" in source
    assert "create_plan_intake_service()" in source
    assert "PdfiumPageRenderer" not in source
    assert 'os.environ.get("APINEX_API_KEY", "")' in source
    assert "print(os.environ" not in source


def test_setup_failures_report_independent_stages_and_sanitize_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_checker()
    sentinel = "private-key-or-content-sentinel"
    monkeypatch.setenv("APINEX_API_KEY", "synthetic")

    def fail(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError(sentinel)

    monkeypatch.setattr(module.ApinexClient, "from_environment", classmethod(fail))
    monkeypatch.setattr(module, "create_provider", fail)
    monkeypatch.setattr(module, "create_plan_intake_service", fail)

    with pytest.raises(SystemExit, match="QUALIFICATION FAIL"):
        module.main()

    output = capsys.readouterr().out
    for label in (
        "APINEX ENDPOINT",
        "APINEX MODEL INVENTORY",
        "APINEX TEXT",
        "APINEX STRUCTURED TEXT",
        "REQUIREMENTS TEXT",
        "PLAN PNG",
        "PLAN JPEG",
        "PLAN PDF-PATH",
        "STRICT JSON",
    ):
        assert f"{label} FAIL" in output
    assert "PROVENANCE BLOCKED_DEPENDENCY" in output
    assert "CONTENT HASH BLOCKED_DEPENDENCY" in output
    assert sentinel not in output
