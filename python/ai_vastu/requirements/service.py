from __future__ import annotations

import os
from uuid import UUID, uuid4

from .models import ConfirmedRequirements, RequirementDraft
from .providers import (
    FixtureRequirementsProvider,
    InterpretationInput,
    OpenAIResponsesRequirementsProvider,
    ReferenceAsset,
    RequirementsProvider,
)
from .store import RequirementsStore


def create_provider() -> RequirementsProvider:
    provider_name = os.getenv(
        "AI_VASTU_REQUIREMENTS_PROVIDER",
        "fixture",
    ).strip().lower()

    if provider_name == "fixture":
        return FixtureRequirementsProvider()
    if provider_name == "openai":
        return OpenAIResponsesRequirementsProvider.from_environment()
    raise RuntimeError(f"Unsupported requirements provider: {provider_name}")


class RequirementsService:
    def __init__(
        self,
        provider: RequirementsProvider,
        store: RequirementsStore,
    ) -> None:
        self._provider = provider
        self._store = store

    def interpret(
        self,
        *,
        user_id: UUID,
        project_id: UUID,
        prompt: str,
        references: tuple[ReferenceAsset, ...],
    ) -> RequirementDraft:
        draft_id = uuid4()
        draft = self._provider.interpret(
            InterpretationInput(
                draft_id=draft_id,
                user_id=user_id,
                project_id=project_id,
                prompt=prompt,
                references=references,
            )
        )
        self._store.save_draft(draft)
        return draft

    def get_draft(self, draft_id: UUID) -> RequirementDraft:
        return self._store.get_draft(draft_id)

    def confirm(
        self,
        *,
        authenticated_user_id: UUID,
        confirmed: ConfirmedRequirements,
    ) -> ConfirmedRequirements:
        draft = self._store.get_draft(confirmed.draft_id)
        if draft.user_id != authenticated_user_id:
            raise PermissionError("Requirement draft does not belong to this user.")
        if confirmed.user_id != authenticated_user_id:
            raise PermissionError("Confirmed user identity mismatch.")
        if confirmed.project_id != draft.project_id:
            raise PermissionError("Confirmed project identity mismatch.")
        self._store.save_confirmed(confirmed)
        return confirmed

    def get_confirmed(self, draft_id: UUID) -> ConfirmedRequirements:
        return self._store.get_confirmed(draft_id)
