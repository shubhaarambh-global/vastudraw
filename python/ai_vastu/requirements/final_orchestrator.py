from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ai_vastu.architectural_intelligence import (
    ArchitecturalDesignIntent,
    ArchitecturalReasoningInput,
    apply_design_intent,
    architectural_intelligence_enabled,
    create_architectural_intelligence_service,
)
from ai_vastu.billing import BillingService
from ai_vastu.generation.models import ArchitecturalGenerationResult
from ai_vastu.projects.errors import DuplicateRevisionError
from ai_vastu.projects.models import AppendRevisionCommand, RevisionRecord
from ai_vastu.projects.service import ProjectRevisionService
from ai_vastu.vastu_reasoning import (
    PlanningBlend,
    VastuReasoningProfile,
    WeightedVastuAssessment,
    assess_plan,
    blend_plan_scores,
    create_vastu_reasoning_service,
    load_soft_vastu_catalog,
    vastu_reasoning_enabled,
)

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
    architectural_intent: ArchitecturalDesignIntent | None = None
    vastu_reasoning_profile: VastuReasoningProfile | None = None
    vastu_assessment: WeightedVastuAssessment | None = None
    planning_blend: PlanningBlend | None = None

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
            raise ValueError("Commercial MVP currently supports exactly one generated floor.")
        for room in confirmed.rooms:
            if room.floor_preference not in {None, 0}:
                raise ValueError("Commercial MVP cannot silently drop an upper-floor preference.")

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

        architectural_intent: ArchitecturalDesignIntent | None = None
        if architectural_intelligence_enabled():
            draft = self._requirements_store.get_draft(draft_id)
            architectural_intent = create_architectural_intelligence_service().reason(
                ArchitecturalReasoningInput(
                    confirmed=confirmed,
                    original_prompt=draft.prompt,
                )
            )

        vastu_reasoning_profile: VastuReasoningProfile | None = None
        if vastu_reasoning_enabled():
            vastu_draft = self._requirements_store.get_draft(draft_id)
            vastu_reasoning_profile = create_vastu_reasoning_service().reason(
                confirmed=confirmed,
                original_prompt=vastu_draft.prompt,
            )

        compiled = compile_confirmed_requirements(confirmed)
        if architectural_intent is not None:
            compiled = apply_design_intent(compiled, architectural_intent)
        generation_result = run_compiled_generation(compiled)

        if generation_result.disposition.value != "ACCEPTED":
            return FinalGenerationRun(
                confirmed=confirmed,
                architectural_intent=architectural_intent,
                vastu_reasoning_profile=vastu_reasoning_profile,
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

        vastu_assessment: WeightedVastuAssessment | None = None
        planning_blend: PlanningBlend | None = None
        if vastu_reasoning_profile is not None:
            vastu_assessment = assess_plan(
                canonical.document,
                vastu_reasoning_profile,
                load_soft_vastu_catalog(),
            )
            planning_blend = blend_plan_scores(
                canonical.document,
                vastu_reasoning_profile,
                vastu_assessment,
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
            architectural_intent=architectural_intent,
            vastu_reasoning_profile=vastu_reasoning_profile,
            compiled=compiled,
            generation_result=generation_result,
            canonical=canonical,
            revision=revision,
            vastu_assessment=vastu_assessment,
            planning_blend=planning_blend,
            billing_reason=authorization.reason,
            free_generation_consumed=(authorization.consumption == "free_generation"),
        )
