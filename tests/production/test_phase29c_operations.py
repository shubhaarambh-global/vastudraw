from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase29c_commands_and_checkers_are_wired() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package["scripts"]

    assert scripts["phase29c:check"] == "python scripts/check-phase29c-hybrid.py"
    assert scripts["phase29c:live"] == "python scripts/check-phase29c-live.py"
    assert "pnpm phase29c:check" in scripts["validate"]
    assert (ROOT / "scripts/check-phase29c-hybrid.py").is_file()
    assert (ROOT / "scripts/check-phase29c-live.py").is_file()


def test_phase29c_environment_examples_have_budgets_but_no_attempt_counts() -> None:
    for relative in (".env.example", "phase28-hybrid.env.example"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "AI_VASTU_OPENROUTER_ATTEMPT_TIMEOUT_SECONDS=120" in text
        assert "AI_VASTU_OPENROUTER_TOTAL_TIMEOUT_SECONDS=240" in text
        assert "AI_VASTU_GEMINI_ATTEMPT_TIMEOUT_SECONDS=90" in text
        assert "AI_VASTU_GEMINI_TOTAL_TIMEOUT_SECONDS=181" in text
        assert "MAX_ATTEMPTS" not in text
        assert "OPENROUTER_API_KEY=\n" in text
        assert "GEMINI_API_KEY=\n" in text


def test_phase29c_live_gate_reports_blocked_credentials_without_network() -> None:
    environment = dict(os.environ)
    environment.pop("OPENROUTER_API_KEY", None)
    environment.pop("GEMINI_API_KEY", None)

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check-phase29c-live.py")],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 2
    assert "OPENROUTER BLOCKED_CREDENTIALS" in result.stdout
    assert "GEMINI BLOCKED_CREDENTIALS" in result.stdout
    assert result.stderr == ""


def test_phase29c_docs_disclose_visual_requirements_compatibility_decision() -> None:
    phase28 = (ROOT / "PHASE28_HYBRID_AI.md").read_text(encoding="utf-8")
    runbook = (ROOT / "docs/runbooks/production-launch.md").read_text(encoding="utf-8")

    for text in (phase28, runbook):
        assert "/requirements/interpret" in text
        assert "OpenRouter vision" in text
        assert "persisted Analyze Plan" in text
    assert "not resolved" in phase28
