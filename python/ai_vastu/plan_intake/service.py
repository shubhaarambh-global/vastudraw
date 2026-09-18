from __future__ import annotations

import os

from .audit import build_plan_analysis
from .errors import PlanIntakeConfigurationError, PlanIntakeProviderError
from .models import PlanAnalysisResult, PlanRecognitionDraft
from .openrouter_provider import OpenRouterPlanRecognitionProvider
from .provider import (
    FixturePlanRecognitionProvider,
    GeminiPlanRecognitionProvider,
    PlanRecognitionInput,
    PlanRecognitionProvider,
)


def configured_plan_recognition_provider_name() -> str:
    explicit = os.getenv("AI_VASTU_PLAN_RECOGNITION_PROVIDER", "").strip().lower()
    if explicit:
        return explicit
    architect = os.getenv("AI_VASTU_ARCHITECT_PROVIDER", "disabled").strip().lower()
    return architect


def _normalize_recognition_questions(
    draft: PlanRecognitionDraft,
) -> PlanRecognitionDraft:
    questions = list(draft.questions)

    def inferred_from_access(question: str) -> bool:
        lowered = question.lower()
        mentions_direction = "road" in lowered or "entrance" in lowered
        mentions_access = any(
            token in lowered
            for token in (
                "parking",
                "driveway",
                "gate",
                "access arrangement",
            )
        )
        implies_inference = any(
            token in lowered
            for token in (
                "infer",
                "assum",
                "apparently",
                "likely",
            )
        )
        return mentions_direction and mentions_access and implies_inference

    questions = [question for question in questions if not inferred_from_access(question)]

    if draft.orientation.road_side is None:
        questions.append(
            "Road side is not explicitly established by the recognized plan; "
            "confirm the adjoining road direction."
        )

    if draft.orientation.entrance_facing is None:
        questions.append(
            "Entrance facing is not explicitly established by the recognized "
            "plan; confirm it if required."
        )

    unique_questions = tuple(dict.fromkeys(questions))

    return draft.model_copy(
        update={
            "questions": unique_questions,
            "content_hash": None,
        }
    ).with_content_hash()


def create_plan_recognition_provider() -> PlanRecognitionProvider:
    name = configured_plan_recognition_provider_name()
    if name == "fixture":
        return FixturePlanRecognitionProvider()
    if name == "gemini":
        return GeminiPlanRecognitionProvider.from_environment()
    if name == "openrouter":
        return OpenRouterPlanRecognitionProvider.from_environment()
    raise PlanIntakeConfigurationError(
        "Unsupported AI_VASTU_PLAN_RECOGNITION_PROVIDER: "
        f"{name or '<blank>'}. Use fixture, gemini, or openrouter."
    )


class PlanIntakeService:
    def __init__(self, provider: PlanRecognitionProvider) -> None:
        self._provider = provider

    def recognize(self, request: PlanRecognitionInput) -> PlanRecognitionDraft:
        try:
            draft = self._provider.recognize(request)
        except (PlanIntakeConfigurationError, PlanIntakeProviderError):
            raise
        except Exception as exc:
            raise PlanIntakeProviderError(str(exc)) from exc

        if draft.project_id != request.project_id:
            raise PlanIntakeProviderError("Plan recognition project identity mismatch.")
        if draft.intake_id != request.intake_id:
            raise PlanIntakeProviderError("Plan recognition intake identity mismatch.")
        return _normalize_recognition_questions(draft)

    def analyze(self, request: PlanRecognitionInput) -> PlanAnalysisResult:
        return build_plan_analysis(self.recognize(request))


def create_plan_intake_service() -> PlanIntakeService:
    return PlanIntakeService(create_plan_recognition_provider())
