from __future__ import annotations

from uuid import UUID

import pytest

import ai_vastu.plan_intake.provider as plan_provider_module
from ai_vastu.plan_intake import (
    PlanEnvelopeObservation,
    PlanIntakeService,
    PlanObservationSource,
    PlanOrientationObservation,
    PlanRecognitionDraft,
    PlanRecognitionInput,
    PlanReferenceBlob,
    PlanReferenceKind,
    PlanRoomObservation,
)
from ai_vastu.plan_intake.errors import (
    PlanIntakeConfigurationError,
    PlanIntakeProviderError,
)
from ai_vastu.plan_intake.provider import GeminiPlanRecognitionProvider
from ai_vastu.provider_runtime import (
    ProviderBudget,
    ProviderFailureCategory,
    ProviderRuntimeError,
)

PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")
INTAKE_ID = UUID("22222222-2222-2222-2222-222222222222")


class _MaliciousVisualProvider:
    name = "gemini"

    def recognize(self, request: PlanRecognitionInput) -> PlanRecognitionDraft:
        return PlanRecognitionDraft(
            project_id=request.project_id,
            intake_id=request.intake_id,
            provider=self.name,
            model="test-model",
            reference_names=("plan.png",),
            envelope=PlanEnvelopeObservation(
                geometry_type="RECTANGLE",
                width_mm=9000,
                depth_mm=12000,
                source=PlanObservationSource.USER_CONFIRMED,
                requires_confirmation=False,
            ),
            orientation=PlanOrientationObservation(
                north_rotation_deg=0,
                source=PlanObservationSource.USER_CONFIRMED,
                requires_confirmation=False,
            ),
            rooms=(
                PlanRoomObservation(
                    room_type="living",
                    source=PlanObservationSource.USER_CONFIRMED,
                    requires_confirmation=False,
                ),
            ),
        ).with_content_hash()


def test_visual_provider_cannot_claim_user_confirmation_and_hash_is_recomputed() -> None:
    request = PlanRecognitionInput(
        project_id=PROJECT_ID,
        intake_id=INTAKE_ID,
        prompt="Analyze plan",
        references=(
            PlanReferenceBlob(
                filename="plan.png",
                content_type="image/png",
                kind=PlanReferenceKind.IMAGE,
                data=b"\x89PNG\r\n\x1a\n",
            ),
        ),
    )

    result = PlanIntakeService(_MaliciousVisualProvider()).recognize(request)

    assert result.project_id == PROJECT_ID
    assert result.intake_id == INTAKE_ID
    assert result.content_hash == result.compute_content_hash()
    assert result.envelope.source is PlanObservationSource.IMAGE
    assert result.orientation.source is PlanObservationSource.IMAGE
    assert result.rooms[0].source is PlanObservationSource.IMAGE
    assert result.envelope.requires_confirmation is True
    assert result.orientation.requires_confirmation is True
    assert result.rooms[0].requires_confirmation is True


def test_gemini_plan_provider_rejects_invalid_shared_runtime_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-live-key")
    monkeypatch.setenv("AI_VASTU_GEMINI_ATTEMPT_TIMEOUT_SECONDS", "nan")

    with pytest.raises(PlanIntakeConfigurationError) as captured:
        GeminiPlanRecognitionProvider.from_environment()

    assert str(captured.value) == "Gemini plan-recognition runtime budget is invalid."
    assert "not-a-live-key" not in str(captured.value)


def test_gemini_plan_provider_passes_shared_budget_to_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget = ProviderBudget(
        attempt_timeout_seconds=1.0,
        total_timeout_seconds=2.0,
        retry_delay_seconds=0.0,
        max_retry_after_seconds=0.0,
    )
    seen: dict[str, object] = {}

    def fail_with_timeout(*_args: object, **kwargs: object) -> object:
        seen["budget"] = kwargs["budget"]
        raise ProviderRuntimeError(ProviderFailureCategory.TIMEOUT, "gemini")

    monkeypatch.setattr(plan_provider_module, "post_json_with_retry", fail_with_timeout)
    provider = GeminiPlanRecognitionProvider(
        "not-a-live-key",
        "gemini-test-model",
        budget=budget,
    )

    with pytest.raises(PlanIntakeProviderError) as captured:
        provider.recognize(
            PlanRecognitionInput(
                project_id=PROJECT_ID,
                intake_id=INTAKE_ID,
                prompt="Analyze plan",
                references=(),
            )
        )

    assert seen["budget"] is budget
    assert captured.value.category is ProviderFailureCategory.TIMEOUT
