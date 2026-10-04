from __future__ import annotations

import os

from .errors import ArchitecturalIntelligenceConfigurationError
from .models import ArchitecturalDesignIntent
from .providers import (
    ApinexArchitecturalIntelligenceProvider,
    ArchitecturalIntelligenceProvider,
    ArchitecturalReasoningInput,
    FixtureArchitecturalIntelligenceProvider,
    GeminiArchitecturalIntelligenceProvider,
    NvidiaNimArchitecturalIntelligenceProvider,
    OllamaLocalArchitecturalIntelligenceProvider,
    OpenAIResponsesArchitecturalIntelligenceProvider,
    OpenRouterArchitecturalIntelligenceProvider,
)


def configured_provider_name() -> str:
    return (
        os.getenv(
            "AI_VASTU_ARCHITECT_PROVIDER",
            "disabled",
        )
        .strip()
        .lower()
    )


def architectural_intelligence_enabled() -> bool:
    return configured_provider_name() not in {"", "disabled", "off", "none"}


def create_architectural_intelligence_provider() -> ArchitecturalIntelligenceProvider:
    provider_name = configured_provider_name()
    if provider_name == "fixture":
        return FixtureArchitecturalIntelligenceProvider()
    if provider_name == "gemini":
        return GeminiArchitecturalIntelligenceProvider.from_environment()
    if provider_name == "openai":
        return OpenAIResponsesArchitecturalIntelligenceProvider.from_environment()
    if provider_name == "openrouter":
        return OpenRouterArchitecturalIntelligenceProvider.from_environment()
    if provider_name == "nvidia_nim":
        return NvidiaNimArchitecturalIntelligenceProvider.from_environment()
    if provider_name == "ollama_local":
        return OllamaLocalArchitecturalIntelligenceProvider.from_environment()
    if provider_name == "apinex":
        return ApinexArchitecturalIntelligenceProvider.from_environment()
    raise ArchitecturalIntelligenceConfigurationError(
        "Unsupported AI_VASTU_ARCHITECT_PROVIDER: "
        f"{provider_name or '<blank>'}. Use disabled, fixture, gemini, nvidia_nim, "
        "ollama_local, apinex, openai, or openrouter."
    )


class ArchitecturalIntelligenceService:
    def __init__(self, provider: ArchitecturalIntelligenceProvider) -> None:
        self._provider = provider

    def reason(
        self,
        request: ArchitecturalReasoningInput,
    ) -> ArchitecturalDesignIntent:
        intent = self._provider.reason(request)
        if intent.project_id != request.confirmed.project_id:
            raise ValueError("Architectural intent project identity mismatch.")
        if intent.draft_id != request.confirmed.draft_id:
            raise ValueError("Architectural intent draft identity mismatch.")
        return intent


def create_architectural_intelligence_service() -> ArchitecturalIntelligenceService:
    return ArchitecturalIntelligenceService(create_architectural_intelligence_provider())
