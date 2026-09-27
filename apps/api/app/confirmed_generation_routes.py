from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from ai_vastu.architectural_brain.errors import (
    ArchitecturalBrainConfigurationError,
    ArchitecturalBrainProviderError,
)
from ai_vastu.architectural_intelligence import (
    ArchitecturalIntelligenceConfigurationError,
    ArchitecturalIntelligenceProviderError,
)
from ai_vastu.billing import BillingService, create_billing_repository
from ai_vastu.billing.service import development_billing_bypass_enabled
from ai_vastu.multi_candidate import MultiCandidateGenerationError
from ai_vastu.projects.errors import ProjectNotFoundError, RevisionConflictError
from ai_vastu.provider_runtime import ProviderFailureCategory
from ai_vastu.requirements.candidate_orchestrator import (
    CandidateGenerationOrchestrator,
    CandidateSelectionError,
    GenerateAlternativesOptions,
    SelectAlternativeOptions,
)
from ai_vastu.requirements.final_orchestrator import (
    EntitlementDenied,
    FinalGenerationOrchestrator,
)
from ai_vastu.requirements.finalization import Phase24FinalizationError
from ai_vastu.requirements.generation_adapter import (
    GenerateConfirmedOptions,
    UnsupportedConfirmedRequirement,
)
from ai_vastu.requirements.store import RequirementsStore
from ai_vastu.vastu_reasoning import (
    VastuReasoningConfigurationError,
    VastuReasoningProviderError,
)
from app.auth_dependencies import CurrentUserDependency, project_service, require_project_owner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/confirmed-generation", tags=["confirmed-generation"])


def _provider_http_error(category: ProviderFailureCategory) -> HTTPException:
    if category is ProviderFailureCategory.TIMEOUT:
        return HTTPException(status_code=504, detail="AI provider timed out.")
    if category in {
        ProviderFailureCategory.AUTHENTICATION,
        ProviderFailureCategory.RATE_LIMITED,
        ProviderFailureCategory.UNAVAILABLE,
    }:
        return HTTPException(status_code=503, detail="AI provider is unavailable.")
    return HTTPException(
        status_code=502,
        detail="AI provider returned an invalid response.",
    )


@router.post("/projects/{project_id}/alternatives")
def generate_confirmed_alternatives(
    project_id: UUID,
    request: Request,
    options: GenerateAlternativesOptions,
    user: CurrentUserDependency,
) -> dict[str, object]:
    require_project_owner(project_service(request), project_id, user)
    user_id = user.user_id
    billing_repository = create_billing_repository()
    projects = project_service(request)
    try:
        orchestrator = CandidateGenerationOrchestrator(
            requirements_store=RequirementsStore.from_environment(),
            billing_service=BillingService(
                billing_repository,
                development_bypass=development_billing_bypass_enabled(),
            ),
            project_service=projects,
        )
        preview = orchestrator.preview(
            authenticated_user_id=user_id,
            project_id=project_id,
            draft_id=options.draft_id,
            max_alternatives=options.max_alternatives,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Confirmed requirements were not found.",
        ) from exc
    except EntitlementDenied as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        ArchitecturalBrainConfigurationError,
        ArchitecturalIntelligenceConfigurationError,
        VastuReasoningConfigurationError,
    ) as exc:
        raise HTTPException(
            status_code=503,
            detail="AI provider is not configured.",
        ) from exc
    except ArchitecturalBrainProviderError as exc:
        raise _provider_http_error(exc.category) from exc
    except ArchitecturalIntelligenceProviderError as exc:
        raise _provider_http_error(exc.category) from exc
    except VastuReasoningProviderError as exc:
        raise _provider_http_error(exc.category) from exc
    except MultiCandidateGenerationError as exc:
        logger.warning(
            "Confirmed candidate generation rejected:\n%s",
            exc,
        )
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except (
        UnsupportedConfirmedRequirement,
        Phase24FinalizationError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    finally:
        billing_repository.close()

    return {
        "candidate_run": preview.outcome.run.model_dump(mode="json"),
        "billing_reason": preview.billing_reason,
        "quota_consumed": False,
        "revision_persisted": False,
        "architectural_intent": (
            None
            if preview.architectural_intent is None
            else preview.architectural_intent.model_dump(mode="json")
        ),
        "vastu_reasoning_profile": (
            None
            if preview.vastu_reasoning_profile is None
            else preview.vastu_reasoning_profile.model_dump(mode="json")
        ),
    }


@router.post("/projects/{project_id}/alternatives/select")
def select_confirmed_alternative(
    project_id: UUID,
    request: Request,
    options: SelectAlternativeOptions,
    user: CurrentUserDependency,
) -> dict[str, object]:
    require_project_owner(project_service(request), project_id, user)
    user_id = user.user_id
    billing_repository = create_billing_repository()
    projects = project_service(request)
    try:
        orchestrator = CandidateGenerationOrchestrator(
            requirements_store=RequirementsStore.from_environment(),
            billing_service=BillingService(
                billing_repository,
                development_bypass=development_billing_bypass_enabled(),
            ),
            project_service=projects,
        )
        selection = orchestrator.select(
            authenticated_user_id=user_id,
            project_id=project_id,
            options=options,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Confirmed requirements were not found.",
        ) from exc
    except EntitlementDenied as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RevisionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CandidateSelectionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        billing_repository.close()

    revision = selection.revision
    return {
        "revision_persisted": True,
        "successful_generation_recorded": selection.successful_generation_recorded,
        "billing_reason": selection.billing_reason,
        "revision_id": str(revision.revision_id),
        "revision_number": revision.revision_number,
        "candidate_id": str(revision.source_candidate_id),
        "plan_document_hash": revision.plan_document_hash,
        "editor_path": f"/editor?project={project_id}",
    }


@router.post("/projects/{project_id}")
def generate_from_confirmed_requirements(
    project_id: UUID,
    request: Request,
    options: GenerateConfirmedOptions,
    user: CurrentUserDependency,
) -> dict[str, object]:
    require_project_owner(project_service(request), project_id, user)
    user_id = user.user_id
    billing_repository = create_billing_repository()
    projects = project_service(request)
    try:
        orchestrator = FinalGenerationOrchestrator(
            requirements_store=RequirementsStore.from_environment(),
            billing_service=BillingService(
                billing_repository,
                development_bypass=development_billing_bypass_enabled(),
            ),
            project_service=projects,
        )
        run = orchestrator.run(
            authenticated_user_id=user_id,
            project_id=project_id,
            draft_id=options.draft_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Confirmed requirements were not found.",
        ) from exc
    except EntitlementDenied as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (
        ArchitecturalBrainConfigurationError,
        ArchitecturalIntelligenceConfigurationError,
        VastuReasoningConfigurationError,
    ) as exc:
        raise HTTPException(
            status_code=503,
            detail="AI provider is not configured.",
        ) from exc
    except ArchitecturalBrainProviderError as exc:
        raise _provider_http_error(exc.category) from exc
    except ArchitecturalIntelligenceProviderError as exc:
        raise _provider_http_error(exc.category) from exc
    except VastuReasoningProviderError as exc:
        raise _provider_http_error(exc.category) from exc
    except (
        UnsupportedConfirmedRequirement,
        Phase24FinalizationError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        billing_repository.close()

    generation_result = run.generation_result
    if run.revision is None or run.canonical is None:
        return {
            "status": generation_result.disposition.value,
            "billing_reason": run.billing_reason,
            "architectural_intent": (
                None
                if run.architectural_intent is None
                else run.architectural_intent.model_dump(mode="json")
            ),
            "vastu_reasoning_profile": (
                None
                if run.vastu_reasoning_profile is None
                else run.vastu_reasoning_profile.model_dump(mode="json")
            ),
            "vastu_assessment": None,
            "planning_blend": None,
            "free_generation_consumed": False,
            "revision_persisted": False,
            "generation_result": generation_result.model_dump(mode="json"),
            "editor_path": None,
        }

    revision = run.revision
    canonical = run.canonical
    editor_path = f"/editor?projectId={project_id}&revisionId={revision.revision_id}"
    return {
        "status": generation_result.disposition.value,
        "billing_reason": run.billing_reason,
        "architectural_intent": (
            None
            if run.architectural_intent is None
            else run.architectural_intent.model_dump(mode="json")
        ),
        "vastu_reasoning_profile": (
            None
            if run.vastu_reasoning_profile is None
            else run.vastu_reasoning_profile.model_dump(mode="json")
        ),
        "vastu_assessment": (
            None if run.vastu_assessment is None else run.vastu_assessment.model_dump(mode="json")
        ),
        "planning_blend": (
            None if run.planning_blend is None else run.planning_blend.model_dump(mode="json")
        ),
        "free_generation_consumed": run.free_generation_consumed,
        "revision_persisted": True,
        "revision_id": str(revision.revision_id),
        "revision_number": revision.revision_number,
        "plan_document_hash": revision.plan_document_hash,
        "candidate_id": str(canonical.candidate_id),
        "vastu_bundle_hash": canonical.bundle_hash,
        "vastu_analysis": canonical.vastu.model_dump(mode="json"),
        "scoring": canonical.scoring.model_dump(mode="json"),
        "editor_path": editor_path,
    }
