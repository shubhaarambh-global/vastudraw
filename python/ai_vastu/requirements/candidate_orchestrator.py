from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ai_vastu.architectural_brain import run_architectural_brain_candidates
from ai_vastu.architectural_intelligence import (
    ArchitecturalDesignIntent,
    ArchitecturalReasoningInput,
    apply_design_intent,
    architectural_intelligence_enabled,
    create_architectural_intelligence_service,
)
from ai_vastu.billing import BillingService, GenerationAuthorization
from ai_vastu.multi_candidate import (
    MultiCandidateGenerationOutcome,
)
from ai_vastu.plan_schema import PlanDocument
from ai_vastu.projects.errors import DuplicateRevisionError, RevisionNotFoundError
from ai_vastu.projects.models import AppendRevisionCommand, RevisionRecord
from ai_vastu.projects.service import ProjectRevisionService
from ai_vastu.vastu_reasoning import (
    VastuReasoningProfile,
    create_vastu_reasoning_service,
    vastu_reasoning_enabled,
)

from .final_orchestrator import EntitlementDenied
from .finalization import EXPECTED_VASTU_V1_BUNDLE_HASH
from .generation_adapter import CompiledGeneration, compile_confirmed_requirements
from .models import ConfirmedRequirements
from .precedent_adapter import (
    precedent_reasoning_context,
    retrieve_resplan_precedents,
)
from .store import RequirementsStore


class GenerateAlternativesOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    draft_id: UUID
    accept_profile_defaults: Literal[True]
    max_alternatives: int = Field(default=4, ge=1, le=4)


class SelectAlternativeOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    draft_id: UUID
    candidate_run_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_id: UUID
    plan_document: PlanDocument


class CandidateSelectionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CandidatePreviewRun:
    confirmed: ConfirmedRequirements
    compiled: CompiledGeneration
    outcome: MultiCandidateGenerationOutcome
    billing_reason: str
    architectural_intent: ArchitecturalDesignIntent | None = None
    vastu_reasoning_profile: VastuReasoningProfile | None = None


@dataclass(frozen=True, slots=True)
class CandidateSelectionRun:
    revision: RevisionRecord
    billing_reason: str
    successful_generation_recorded: bool


class CandidateGenerationOrchestrator:
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

    def _confirmed(
        self,
        *,
        authenticated_user_id: UUID,
        project_id: UUID,
        draft_id: UUID,
    ) -> ConfirmedRequirements:
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
        for room in confirmed.rooms:
            if (
                room.floor_preference is not None
                and not 0 <= room.floor_preference < confirmed.floor_count
            ):
                raise ValueError(
                    "PROGRAM_DISTRIBUTION_FAILURE: room floor preference is outside the building."
                )
        return confirmed

    def _authorize(
        self,
        *,
        authenticated_user_id: UUID,
        project_id: UUID,
    ) -> GenerationAuthorization:
        user_key = str(authenticated_user_id)
        project_key = str(project_id)
        authorization = self._billing_service.authorize_generation(
            user_key,
            project_key,
        )
        if not authorization.allowed and authorization.reason == "project_not_entitled":
            try:
                self._billing_service.register_project(user_key, project_key)
            except PermissionError as exc:
                raise EntitlementDenied("project_not_entitled") from exc
            authorization = self._billing_service.authorize_generation(
                user_key,
                project_key,
            )
        if not authorization.allowed:
            raise EntitlementDenied(authorization.reason)
        return authorization

    def preview(
        self,
        *,
        authenticated_user_id: UUID,
        project_id: UUID,
        draft_id: UUID,
        max_alternatives: int = 4,
    ) -> CandidatePreviewRun:
        confirmed = self._confirmed(
            authenticated_user_id=authenticated_user_id,
            project_id=project_id,
            draft_id=draft_id,
        )
        authorization = self._authorize(
            authenticated_user_id=authenticated_user_id,
            project_id=project_id,
        )
        draft = self._requirements_store.get_draft(draft_id)

        precedent_matches = retrieve_resplan_precedents(
            confirmed,
            limit=6,
        )
        precedent_context = precedent_reasoning_context(precedent_matches)

        architectural_intent: ArchitecturalDesignIntent | None = None
        if architectural_intelligence_enabled():
            architectural_intent = create_architectural_intelligence_service().reason(
                ArchitecturalReasoningInput(
                    confirmed=confirmed,
                    original_prompt=draft.prompt,
                    precedent_context=precedent_context,
                )
            )

        vastu_reasoning_profile: VastuReasoningProfile | None = None
        if vastu_reasoning_enabled():
            vastu_reasoning_profile = create_vastu_reasoning_service().reason(
                confirmed=confirmed,
                original_prompt=draft.prompt,
            )

        # Keep the shared compiled baseline precedent-neutral.
        # Individual ResPlan graphs are bound later per candidate concept,
        # before that candidate reaches CP-SAT.
        compiled = compile_confirmed_requirements(confirmed)

        if architectural_intent is not None:
            compiled = apply_design_intent(compiled, architectural_intent)

        outcome = run_architectural_brain_candidates(
            confirmed=confirmed,
            compiled=compiled,
            original_prompt=draft.prompt,
            vastu_profile=vastu_reasoning_profile,
            precedent_matches=precedent_matches,
            max_alternatives=max_alternatives,
        )

        return CandidatePreviewRun(
            confirmed=confirmed,
            compiled=compiled,
            outcome=outcome,
            billing_reason=authorization.reason,
            architectural_intent=architectural_intent,
            vastu_reasoning_profile=vastu_reasoning_profile,
        )

    def select(
        self,
        *,
        authenticated_user_id: UUID,
        project_id: UUID,
        options: SelectAlternativeOptions,
    ) -> CandidateSelectionRun:
        self._confirmed(
            authenticated_user_id=authenticated_user_id,
            project_id=project_id,
            draft_id=options.draft_id,
        )

        document = options.plan_document
        if document.project_id != project_id:
            raise CandidateSelectionError("Selected PlanDocument belongs to another project.")
        if not document.validation.valid:
            raise CandidateSelectionError(
                "Only a hard-valid candidate PlanDocument may be selected."
            )
        if document.content_hash is None:
            raise CandidateSelectionError(
                "Selected candidate must carry its canonical PlanDocument hash."
            )
        if document.compute_content_hash() != document.content_hash:
            raise CandidateSelectionError("Selected PlanDocument hash does not match its content.")
        if document.generation_metadata.rule_bundle_hash != EXPECTED_VASTU_V1_BUNDLE_HASH:
            raise CandidateSelectionError(
                "Selected candidate does not reference the approved Vastu v1 bundle."
            )
        if not any(
            assumption.code == "PHASE24_CONFIRMED_CONTEXT" and assumption.confirmed_by_user
            for assumption in document.assumptions
        ):
            raise CandidateSelectionError(
                "Selected candidate is missing human-confirmed planning context."
            )

        # Selection is idempotent for an already-persisted candidate revision.
        try:
            existing = self._project_service.get_revision(
                project_id,
                document.revision_id,
            )
        except RevisionNotFoundError:
            existing = None

        if existing is not None:
            if (
                existing.source_candidate_id != options.candidate_id
                or existing.plan_document_hash != document.content_hash
            ):
                raise CandidateSelectionError(
                    "Selected candidate identity does not match the persisted revision."
                )
            return CandidateSelectionRun(
                revision=existing,
                billing_reason="already_persisted",
                successful_generation_recorded=False,
            )

        authorization = self._authorize(
            authenticated_user_id=authenticated_user_id,
            project_id=project_id,
        )
        project = self._project_service.get_project(project_id)
        command = AppendRevisionCommand(
            project_id=project_id,
            document=document,
            expected_parent_revision_id=project.current_revision_id,
            source_candidate_id=options.candidate_id,
            note=(
                "Phase 26C selected alternative "
                f"{options.candidate_id} from candidate run "
                f"{options.candidate_run_hash}."
            ),
        )

        try:
            revision = self._project_service.append_revision(command)
        except DuplicateRevisionError:
            revision = self._project_service.get_revision(
                project_id,
                document.revision_id,
            )
            return CandidateSelectionRun(
                revision=revision,
                billing_reason="already_persisted",
                successful_generation_recorded=False,
            )

        # Billing is deliberately after durable append-only revision persistence.
        self._billing_service.record_successful_generation(
            str(authenticated_user_id),
            str(project_id),
        )

        return CandidateSelectionRun(
            revision=revision,
            billing_reason=authorization.reason,
            successful_generation_recorded=True,
        )
