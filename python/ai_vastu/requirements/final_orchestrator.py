from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ai_vastu.billing import BillingService
from ai_vastu.generation.models import ArchitecturalGenerationResult
from ai_vastu.projects.errors import DuplicateRevisionError
from ai_vastu.projects.models import AppendRevisionCommand, RevisionRecord
from ai_vastu.projects.service import ProjectRevisionService

from .finalization import CanonicalGeneration, build_canonical_plan_document
from .generation_adapter import (
    CompiledGeneration,
    compile_confirmed_requirements,
    run_compiled_generation,
)
from .models import ConfirmedRequirements
from .store import RequirementsStore


class EntitlementDenied(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class FinalGenerationRun:
    confirmed: ConfirmedRequirements
    compiled: CompiledGeneration
    generation_result: ArchitecturalGenerationResult
    canonical: CanonicalGeneration | None
    revision: RevisionRecord | None
    billing_reason: str
    free_generation_consumed: bool

    @property
    def revision_persisted(self) -> bool:
        return self.revision is not None


class FinalGenerationOrchestrator:
    def __init__(
        self,
        *,
        requirements_store: RequirementsStore,
        billing_service: BillingService,
        project_service: ProjectRevisionService,
    ) -> None:
        self._requirements_store = requirements_store
        self._billing_service = billing_service
        self._project_service = project_service

    def run(
        self,
        *,
        authenticated_user_id: UUID,
        project_id: UUID,
        draft_id: UUID,
    ) -> FinalGenerationRun:
        if not self._project_service.is_project_owner(
            project_id,
            authenticated_user_id,
        ):
            raise PermissionError("Project is not owned by the authenticated user.")

        confirmed = self._requirements_store.get_confirmed(draft_id)
        if confirmed.user_id != authenticated_user_id:
            raise PermissionError("Confirmed requirements do not belong to this user.")
        if confirmed.project_id != project_id:
            raise PermissionError("Confirmed requirements belong to another project.")
        if confirmed.floor_count != 1:
            raise ValueError(
                "Commercial MVP currently supports exactly one generated floor."
            )
        for room in confirmed.rooms:
            if room.floor_preference not in {None, 0}:
                raise ValueError(
                    "Commercial MVP cannot silently drop an upper-floor preference."
                )

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
            raise EntitlementDenied(authorization.reason)

        compiled = compile_confirmed_requirements(confirmed)
        generation_result = run_compiled_generation(compiled)

        if generation_result.disposition.value != "ACCEPTED":
            return FinalGenerationRun(
                confirmed=confirmed,
                compiled=compiled,
                generation_result=generation_result,
                canonical=None,
                revision=None,
                billing_reason=authorization.reason,
                free_generation_consumed=False,
            )

        canonical = build_canonical_plan_document(
            confirmed=confirmed,
            compiled=compiled,
            result=generation_result,
        )

        project = self._project_service.get_project(project_id)
        command = AppendRevisionCommand(
            project_id=project_id,
            document=canonical.document,
            expected_parent_revision_id=project.current_revision_id,
            source_candidate_id=canonical.candidate_id,
            note=f"Phase 24 confirmed generation from draft {draft_id}",
        )

        try:
            revision = self._project_service.append_revision(command)
        except DuplicateRevisionError:
            revision = self._project_service.get_revision(
                project_id,
                canonical.document.revision_id,
            )

        # Billing success intentionally occurs only after the durable revision exists.
        self._billing_service.record_successful_generation(
            user_key,
            project_key,
        )

        return FinalGenerationRun(
            confirmed=confirmed,
            compiled=compiled,
            generation_result=generation_result,
            canonical=canonical,
            revision=revision,
            billing_reason=authorization.reason,
            free_generation_consumed=(
                authorization.consumption == "free_generation"
            ),
        )
