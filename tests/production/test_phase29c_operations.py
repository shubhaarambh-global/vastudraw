from __future__ import annotations

import base64
import importlib.util
import json
import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
from PIL import Image

from ai_vastu.nvidia_nim_http import (
    PRIMARY_TEXT_MODEL,
    VISION_MODEL,
    NvidiaNimFailureStage,
    NvidiaNimModelPolicy,
    NvidiaNimRequestError,
)
from ai_vastu.plan_intake import PlanIntakeService
from ai_vastu.plan_intake.nvidia_nim_provider import NvidiaNimPlanRecognitionProvider
from ai_vastu.provider_runtime import ProviderFailureCategory

ROOT = Path(__file__).resolve().parents[2]


def _load_live_checker() -> ModuleType:
    path = ROOT / "scripts" / "check-phase29c-live.py"
    spec = importlib.util.spec_from_file_location("phase29c_live_under_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load Phase 29C live checker.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase29c_commands_and_checkers_are_wired() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package["scripts"]

    assert scripts["phase29c:check"] == (
        "node scripts/run-project-python.mjs scripts/check-phase29c-hybrid.py"
    )
    assert scripts["phase29c:live"] == (
        "node scripts/run-project-python.mjs scripts/check-phase29c-live.py"
    )
    assert scripts["python:test"] == (
        "node scripts/run-project-python.mjs -m pytest -p pytest_workspace_tmp"
    )
    assert scripts["python:lint"].startswith(
        "node scripts/run-project-python.mjs -m ruff"
    )
    assert scripts["python:typecheck"] == (
        "node scripts/run-project-python.mjs -m mypy"
    )
    assert not any(
        command.startswith(("python ", "pytest", "ruff ", "mypy"))
        for command in scripts.values()
    )
    assert "pnpm phase29c:check" in scripts["validate"]
    assert (ROOT / "scripts/check-phase29c-hybrid.py").is_file()
    assert (ROOT / "scripts/check-phase29c-live.py").is_file()


def test_phase29c_environment_examples_define_nvidia_only_active_profile() -> None:
    for relative in (".env.production.example", "phase29-nvidia-nim.env.example"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "AI_VASTU_NVIDIA_ATTEMPT_TIMEOUT_SECONDS=120" in text
        assert "AI_VASTU_NVIDIA_TOTAL_TIMEOUT_SECONDS=240" in text
        assert "AI_VASTU_REQUIREMENTS_PROVIDER=nvidia_nim" in text
        assert "AI_VASTU_PLAN_RECOGNITION_PROVIDER=nvidia_nim" in text
        assert "NVIDIA_API_KEY=" in text
        assert "MAX_ATTEMPTS" not in text
        assert "OPENROUTER_API_KEY" not in text
        assert "GEMINI_API_KEY" not in text


def test_phase29c_live_gate_reports_blocked_credentials_without_network() -> None:
    environment = dict(os.environ)
    environment.pop("NVIDIA_API_KEY", None)

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
    assert "NVIDIA TEXT PRIMARY BLOCKED_CREDENTIALS" in result.stdout
    assert "NVIDIA MODEL INVENTORY BLOCKED_CREDENTIALS" in result.stdout
    assert "NVIDIA TEXT FALLBACK" not in result.stdout
    assert "NVIDIA VISION PNG BLOCKED_CREDENTIALS" in result.stdout
    assert "NVIDIA VISION JPEG BLOCKED_CREDENTIALS" in result.stdout
    assert "NVIDIA VISION PDF-PATH BLOCKED_CREDENTIALS" in result.stdout
    assert "NVIDIA VISION PDF LOCAL RENDER PASS_LOCAL" in result.stdout
    assert "OPENROUTER" not in result.stdout
    assert "GEMINI" not in result.stdout
    assert result.stderr == ""


def test_phase29c_live_gate_inventories_models_before_completion_probes() -> None:
    source = (ROOT / "scripts" / "check-phase29c-live.py").read_text(encoding="utf-8")

    inventory = source.index("verify_pinned_models_available()")
    primary_probe = source.index('("NVIDIA TEXT PRIMARY", PRIMARY_TEXT_MODEL', inventory)
    assert inventory < primary_probe
    assert "create_provider().interpret" in source
    assert "create_plan_intake_service().recognize" in source
    assert "success_status=success_status" in source


def test_phase29c_live_inventory_failure_prevents_all_probes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_live_checker()
    monkeypatch.setenv("NVIDIA_API_KEY", "sentinel-present-only")
    monkeypatch.setattr(module, "_policy", lambda: object())

    class FailingInventoryClient:
        def verify_pinned_models_available(self) -> None:
            raise NvidiaNimRequestError(ProviderFailureCategory.UNAVAILABLE)

    monkeypatch.setattr(
        module.NvidiaNimClient,
        "from_environment",
        classmethod(lambda _cls: FailingInventoryClient()),
    )
    labels: list[str] = []

    def run(label: str, *_args: object, **_kwargs: object) -> str:
        labels.append(label)
        if label == "NVIDIA VISION PDF LOCAL RENDER":
            return "PASS_LOCAL"
        pytest.fail("completion probe ran after inventory failure")

    monkeypatch.setattr(module, "_run", run)

    with pytest.raises(SystemExit) as captured:
        module.main()

    assert captured.value.code == 1
    output = capsys.readouterr().out
    assert "NVIDIA MODEL INVENTORY FAIL role=model_inventory" in output
    assert "category=unavailable" in output
    assert "stage=provider_transport_http" in output
    assert labels == ["NVIDIA VISION PDF LOCAL RENDER"]


def test_primary_qualification_refuses_a_multi_model_policy_before_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_checker()

    class UnsafePolicy:
        text_chain = (PRIMARY_TEXT_MODEL, "nvidia/unqualified-fallback")

    monkeypatch.setattr(
        module,
        "create_provider",
        lambda: pytest.fail("provider called for a multi-model primary probe"),
    )

    with pytest.raises(RuntimeError, match="primary-only"):
        module._primary(UnsafePolicy())


@pytest.mark.parametrize(
    "failed_label",
    (
        "NVIDIA VISION PDF LOCAL RENDER",
        "NVIDIA TEXT PRIMARY",
        "NVIDIA VISION PNG",
        "NVIDIA VISION JPEG",
        "NVIDIA VISION PDF-PATH",
    ),
)
def test_phase29c_live_runs_independent_probes_then_fails_aggregate(
    monkeypatch: pytest.MonkeyPatch,
    failed_label: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_live_checker()
    monkeypatch.setenv("NVIDIA_API_KEY", "sentinel-present-only")
    monkeypatch.setattr(module, "_policy", lambda: object())

    class PassingInventoryClient:
        def verify_pinned_models_available(self) -> tuple[str, str]:
            return (PRIMARY_TEXT_MODEL, VISION_MODEL)

    monkeypatch.setattr(
        module.NvidiaNimClient,
        "from_environment",
        classmethod(lambda _cls: PassingInventoryClient()),
    )
    labels: list[str] = []

    def run(label: str, _model: str, _probe: object, **kwargs: object) -> str:
        labels.append(label)
        if label == failed_label:
            return "FAIL"
        return str(kwargs.get("success_status", "PASS_LIVE"))

    monkeypatch.setattr(module, "_run", run)

    with pytest.raises(SystemExit) as captured:
        module.main()

    assert captured.value.code == 1
    assert labels == [
        "NVIDIA VISION PDF LOCAL RENDER",
        "NVIDIA TEXT PRIMARY",
        "NVIDIA VISION PNG",
        "NVIDIA VISION JPEG",
        "NVIDIA VISION PDF-PATH",
    ]
    assert "PHASE29C NVIDIA_NIM FAIL required_stages=incomplete" in (
        capsys.readouterr().out
    )


def test_jpeg_live_probe_starts_with_real_jpeg_and_uses_production_intake_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_checker()
    source_jpegs: list[bytes] = []

    class RecordingClient:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def complete_validated_json(self, **kwargs: Any) -> object:
            self.calls.append(kwargs)
            parsed = {
                "envelope": {
                    "geometry_type": "UNKNOWN",
                    "confidence": 0.5,
                    "requires_confirmation": True,
                },
                "orientation": {
                    "confidence": 0.5,
                    "requires_confirmation": True,
                },
                "rooms": [],
                "observations": [],
                "questions": [],
                "warnings": [],
            }
            return kwargs["validator"](parsed, kwargs["models"][0])

    client = RecordingClient()
    service = PlanIntakeService(
        NvidiaNimPlanRecognitionProvider(
            client=cast(Any, client),
            policy=NvidiaNimModelPolicy(),
        )
    )
    real_image = module._image

    def record_image(format_name: str) -> bytes:
        data = cast(bytes, real_image(format_name))
        source_jpegs.append(data)
        return data

    monkeypatch.setattr(module, "_image", record_image)
    monkeypatch.setattr(module, "create_plan_intake_service", lambda: service)

    module._vision("JPEG", NvidiaNimModelPolicy())

    assert source_jpegs[0].startswith(b"\xff\xd8\xff")
    with Image.open(BytesIO(source_jpegs[0])) as image:
        assert image.format == "JPEG"
    content = client.calls[0]["messages"][1]["content"]
    image_part = next(part for part in content if part["type"] == "image_url")
    url = image_part["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")
    assert base64.b64decode(url.partition(",")[2]).startswith(b"\x89PNG\r\n\x1a\n")
    assert client.calls[0]["disable_thinking"] is True


def test_project_python_runner_uses_venv_without_shell_and_preserves_arguments() -> None:
    runner = ROOT / "scripts" / "run-project-python.mjs"
    code = (
        "import json,os,sys; "
        "print(json.dumps({'executable':sys.executable,'cwd':os.getcwd(),"
        "'args':sys.argv[1:],'temp':os.environ.get('TEMP'),"
        "'tmp':os.environ.get('TMP'),"
        "'pytest_tmp':os.environ.get('AI_VASTU_PYTEST_TMP_ROOT')}))"
    )
    result = subprocess.run(
        ["node", str(runner), "-c", code, "argument with spaces", ";|&$()"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    expected_python = ROOT / ".venv" / (
        "Scripts/python.exe" if os.name == "nt" else "bin/python"
    )
    assert Path(payload["executable"]).resolve() == expected_python.resolve()
    assert Path(payload["cwd"]).resolve() == ROOT.resolve()
    assert payload["args"] == ["argument with spaces", ";|&$()"]
    if os.name == "nt":
        pytest_tmp = Path(payload["pytest_tmp"])
        process_temp = pytest_tmp.parent
        assert process_temp.parent == ROOT / ".local" / "python-process-temp"
        assert process_temp.name.startswith("run-")
        assert not process_temp.exists()
    assert result.stderr == ""


def test_phase29c_docs_disclose_visual_requirements_compatibility_boundary() -> None:
    runbook = (ROOT / "docs/runbooks/production-launch.md").read_text(encoding="utf-8")

    assert "/requirements/interpret" in runbook
    assert "filenames as context only" in runbook
    assert "persisted Analyze Plan" in runbook
    assert "OpenRouter vision" not in runbook


def test_live_diagnostics_are_staged_typed_and_sanitized(
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_live_checker()

    def fail() -> None:
        raise NvidiaNimRequestError(
            ProviderFailureCategory.TIMEOUT,
            http_status=504,
            stage=NvidiaNimFailureStage.PROVIDER_TRANSPORT_HTTP,
            model_id=PRIMARY_TEXT_MODEL,
            attempts=2,
        )

    assert module._run("NVIDIA TEXT PRIMARY", PRIMARY_TEXT_MODEL, fail) == "FAIL"
    output = capsys.readouterr().out
    assert f"model={PRIMARY_TEXT_MODEL}" in output
    assert "category=timeout" in output
    assert "stage=provider_transport_http" in output
    assert "attempts=2" in output
    assert "http_status=504" in output
    assert "Authorization" not in output
    assert "prompt" not in output
    assert "response" not in output
