from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ai_vastu.billing import BillingService
from ai_vastu.generation.models import ArchitecturalGenerationResult
from ai_vastu.requirements.generation_adapter import (
    CompiledGeneration,
    compile_confirmed_requirements,
    run_compiled_generation,
)
from ai_vastu.requirements.models import ConfirmedRequirements
from ai_vastu.requirements.store import RequirementsStore


@dataclass(frozen=True, slots=True)
class ConfirmedGenerationRun:
    confirmed: ConfirmedRequirements
    compiled: CompiledGeneration
    result: ArchitecturalGenerationResult
    billing_reason: str
    free_generation_consumed: bool


class ConfirmedGenerationOrchestrator:
    def __init__(
        self,
        *,
        requirements_store: RequirementsStore,
        billing_service: BillingService,
    ) -> None:
        self._requirements_store = requirements_store
        self._billing_service = billing_service

    def run(
        self,
        *,
        authenticated_user_id: UUID,
        project_id: UUID,
        draft_id: UUID,
    ) -> ConfirmedGenerationRun:
        confirmed = self._requirements_store.get_confirmed(draft_id)

        if confirmed.user_id != authenticated_user_id:
            raise PermissionError("Confirmed requirements do not belong to this user.")
        if confirmed.project_id != project_id:
            raise PermissionError("Confirmed requirements belong to another project.")

        user_key = str(authenticated_user_id)
        project_key = str(project_id)

        authorization = self._billing_service.authorize_generation(
            user_key,
            project_key,
        )
        if not authorization.allowed and authorization.reason == "project_not_entitled":
            self._billing_service.register_project(user_key, project_key)
            authorization = self._billing_service.authorize_generation(
                user_key,
                project_key,
            )

        if not authorization.allowed:
            raise PermissionError(authorization.reason)

        compiled = compile_confirmed_requirements(confirmed)
        result = run_compiled_generation(compiled)

        consumed = False
        if result.disposition.value == "ACCEPTED":
            self._billing_service.record_successful_generation(
                user_key,
                project_key,
            )
            consumed = authorization.consumption == "free_generation"

        return ConfirmedGenerationRun(
            confirmed=confirmed,
            compiled=compiled,
            result=result,
            billing_reason=authorization.reason,
            free_generation_consumed=consumed,
        )
