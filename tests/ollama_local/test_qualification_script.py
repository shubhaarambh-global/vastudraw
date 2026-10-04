from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from ai_vastu.ollama_local_http import (
    OLLAMA_LOCAL_MODEL,
    OllamaLocalFailureStage,
    OllamaLocalRequestError,
    OllamaLocalValidationIssue,
)
from ai_vastu.plan_intake import PlanIntakeProviderError
from ai_vastu.plan_intake.models import (
    PlanEnvelopeObservation,
    PlanObservationSource,
    PlanOrientationObservation,
    PlanRecognitionDraft,
    PlanRoomObservation,
)
from ai_vastu.provider_runtime import ProviderFailureCategory
from ai_vastu.requirements.providers.fixture import FixtureRequirementsProvider

ROOT = Path(__file__).resolve().parents[2]


def _load_checker() -> ModuleType:
    path = ROOT / "scripts" / "check-ollama-local.py"
    spec = importlib.util.spec_from_file_location("ollama_local_checker_under_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load Ollama local checker.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checker_is_wired_through_project_python_runner() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["ollama:local"] == (
        "node scripts/run-project-python.mjs scripts/check-ollama-local.py"
    )
    source = (ROOT / "scripts" / "check-ollama-local.py").read_text(encoding="utf-8")
    for label in (
        "OLLAMA ENDPOINT",
        "OLLAMA MODEL",
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


def test_failed_media_stage_does_not_hide_later_independent_results(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_checker()

    class FakeClient:
        def verify_endpoint(self) -> str:
            return "0.35.0"

        def verify_pinned_model_available(self) -> str:
            return OLLAMA_LOCAL_MODEL

        def complete_validated_json(self, **kwargs: Any) -> object:
            return kwargs["validator"]({"status": "PASS_LOCAL"}, OLLAMA_LOCAL_MODEL)

    monkeypatch.setattr(
        module.OllamaLocalClient,
        "from_environment",
        classmethod(lambda _cls: FakeClient()),
    )

    class RequirementsProvider:
        name = "ollama_local"

        def interpret(self, request: Any) -> object:
            draft = FixtureRequirementsProvider().interpret(request)
            return draft.model_copy(
                update={"provider": "ollama_local", "model": OLLAMA_LOCAL_MODEL}
            )

    monkeypatch.setattr(module, "create_provider", lambda: RequirementsProvider())
    monkeypatch.setattr(module, "_assert_requirements", lambda draft: draft)

    class PlanService:
        def recognize(self, request: Any) -> PlanRecognitionDraft:
            reference = request.references[0]
            if reference.content_type == "image/jpeg":
                raise RuntimeError("independent JPEG failure")
            return PlanRecognitionDraft(
                project_id=request.project_id,
                intake_id=request.intake_id,
                provider="ollama_local",
                model=OLLAMA_LOCAL_MODEL,
                reference_names=(reference.filename,),
                envelope=PlanEnvelopeObservation(
                    confidence=0.5,
                    source=PlanObservationSource.MODEL_INFERENCE,
                    requires_confirmation=True,
                ),
                orientation=PlanOrientationObservation(
                    north_rotation_deg=0,
                    confidence=0.9,
                    source=PlanObservationSource.MODEL_INFERENCE,
                    requires_confirmation=True,
                    evidence=("NORTH",),
                ),
                rooms=tuple(
                    PlanRoomObservation(
                        room_type=room_type,
                        label=label,
                        confidence=0.9,
                        source=PlanObservationSource.MODEL_INFERENCE,
                        requires_confirmation=True,
                    )
                    for room_type, label in (
                        ("living", "LIVING"),
                        ("kitchen", "KITCHEN"),
                        ("bedroom", "BEDROOM"),
                        ("common_toilet", "TOILET"),
                    )
                ),
            ).with_content_hash()

    monkeypatch.setattr(module, "create_plan_intake_service", lambda: PlanService())
    monkeypatch.setattr(module, "_plan_image", lambda _format: b"bounded-image")
    monkeypatch.setattr(module, "_plan_pdf", lambda: b"%PDF-bounded")

    with pytest.raises(SystemExit, match="QUALIFICATION FAIL"):
        module.main()

    output = capsys.readouterr().out
    assert "PLAN JPEG FAIL" in output
    assert output.index("PLAN JPEG FAIL") < output.index("PLAN PDF-PATH PASS_LOCAL")
    assert output.index("PLAN PDF-PATH PASS_LOCAL") < output.index("STRICT JSON PASS_LOCAL")
    assert "PROVENANCE BLOCKED_DEPENDENCY missing=PLAN JPEG" in output
    assert "CONTENT HASH BLOCKED_DEPENDENCY missing=PLAN JPEG" in output


def test_wrapped_png_application_validation_is_safe_and_blocks_dependents(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_checker()
    sentinel = "private-model-content-sentinel"

    class FakeClient:
        def verify_endpoint(self) -> str:
            return "0.35.0"

        def verify_pinned_model_available(self) -> str:
            return OLLAMA_LOCAL_MODEL

        def complete_validated_json(self, **kwargs: Any) -> object:
            return kwargs["validator"]({"status": "PASS_LOCAL"}, OLLAMA_LOCAL_MODEL)

    monkeypatch.setattr(
        module.OllamaLocalClient,
        "from_environment",
        classmethod(lambda _cls: FakeClient()),
    )

    class RequirementsProvider:
        name = "ollama_local"

        def interpret(self, request: Any) -> object:
            draft = FixtureRequirementsProvider().interpret(request)
            return draft.model_copy(
                update={"provider": "ollama_local", "model": OLLAMA_LOCAL_MODEL}
            )

    monkeypatch.setattr(module, "create_provider", lambda: RequirementsProvider())
    monkeypatch.setattr(module, "_assert_requirements", lambda draft: draft)

    class PlanService:
        def recognize(self, request: Any) -> PlanRecognitionDraft:
            reference = request.references[0]
            if reference.content_type == "image/png" and reference.kind.value == "IMAGE":
                provider_error = OllamaLocalRequestError(
                    ProviderFailureCategory.INVALID_RESPONSE,
                    stage=OllamaLocalFailureStage.APPLICATION_VALIDATION,
                    validation_issues=(
                        OllamaLocalValidationIssue(
                            location=f"rooms.{sentinel}.centroid_y_basis_points",
                            error_type=sentinel,
                        ),
                    ),
                )
                raise PlanIntakeProviderError(provider_error.category) from provider_error
            return PlanRecognitionDraft(
                project_id=request.project_id,
                intake_id=request.intake_id,
                provider="ollama_local",
                model=OLLAMA_LOCAL_MODEL,
                reference_names=(reference.filename,),
                envelope=PlanEnvelopeObservation(),
                orientation=PlanOrientationObservation(
                    north_rotation_deg=0,
                    evidence=("NORTH",),
                ),
                rooms=tuple(
                    PlanRoomObservation(room_type=room_type, label=label)
                    for room_type, label in (
                        ("living", "LIVING"),
                        ("kitchen", "KITCHEN"),
                        ("bedroom", "BEDROOM"),
                        ("common_toilet", "TOILET"),
                    )
                ),
            ).with_content_hash()

    monkeypatch.setattr(module, "create_plan_intake_service", lambda: PlanService())
    monkeypatch.setattr(module, "_plan_image", lambda _format: b"bounded-image")
    monkeypatch.setattr(module, "_plan_pdf", lambda: b"%PDF-bounded")

    with pytest.raises(SystemExit, match="QUALIFICATION FAIL"):
        module.main()

    output = capsys.readouterr().out
    assert (
        "PLAN PNG FAIL category=invalid_response stage=application_validation "
        "attempts=1 "
        "validation=rooms.<field>.centroid_y_basis_points:validation_error"
    ) in output
    assert "PLAN JPEG PASS_LOCAL" in output
    assert "PLAN PDF-PATH PASS_LOCAL" in output
    assert "STRICT JSON PASS_LOCAL" in output
    assert "PROVENANCE BLOCKED_DEPENDENCY missing=PLAN PNG" in output
    assert "CONTENT HASH BLOCKED_DEPENDENCY missing=PLAN PNG" in output
    assert sentinel not in output


def test_setup_failures_still_report_every_required_stage(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_checker()

    def fail_setup(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("private setup sentinel")

    monkeypatch.setattr(
        module.OllamaLocalClient,
        "from_environment",
        classmethod(fail_setup),
    )
    monkeypatch.setattr(module, "create_provider", fail_setup)
    monkeypatch.setattr(module, "create_plan_intake_service", fail_setup)

    with pytest.raises(SystemExit, match="QUALIFICATION FAIL"):
        module.main()

    output = capsys.readouterr().out
    for label in (
        "OLLAMA ENDPOINT",
        "OLLAMA MODEL",
        "REQUIREMENTS TEXT",
        "PLAN PNG",
        "PLAN JPEG",
        "PLAN PDF-PATH",
        "STRICT JSON",
    ):
        assert f"{label} FAIL" in output
    assert "PROVENANCE BLOCKED_DEPENDENCY" in output
    assert "CONTENT HASH BLOCKED_DEPENDENCY" in output
    assert "private setup sentinel" not in output
