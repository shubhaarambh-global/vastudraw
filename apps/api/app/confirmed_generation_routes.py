from __future__ import annotations

import os
from uuid import UUID

import jwt
from fastapi import APIRouter, Header, HTTPException

from ai_vastu.billing import BillingService, create_billing_repository
from ai_vastu.projects.factory import create_project_repository_from_environment
from ai_vastu.projects.service import ProjectRevisionService
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

router = APIRouter(prefix="/confirmed-generation", tags=["confirmed-generation"])


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer authentication required.")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Bearer authentication required.")
    return token


def _resolve_user_id(authorization: str | None) -> UUID:
    token = _bearer_token(authorization)
    mode = os.getenv("AI_VASTU_AUTH_MODE", "production").strip().lower()

    if mode == "development":
        expected = os.getenv("AI_VASTU_DEV_BEARER_TOKEN", "")
        user_id = os.getenv("AI_VASTU_DEV_USER_ID", "")
        if not expected or not user_id or token != expected:
            raise HTTPException(status_code=401, detail="Invalid development token.")
        return UUID(user_id)

    supabase_url = os.getenv("AI_VASTU_SUPABASE_URL", "").rstrip("/")
    if not supabase_url:
        raise HTTPException(
            status_code=503,
            detail="Supabase authentication is not configured.",
        )

    try:
        header = jwt.get_unverified_header(token)
        algorithm = str(header.get("alg", ""))
        if algorithm not in {"RS256", "ES256"}:
            raise ValueError("Unsupported JWT algorithm.")
        jwks = jwt.PyJWKClient(f"{supabase_url}/auth/v1/.well-known/jwks.json")
        signing_key = jwks.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            audience=os.getenv(
                "AI_VASTU_SUPABASE_JWT_AUDIENCE",
                "authenticated",
            ),
            issuer=f"{supabase_url}/auth/v1",
        )
        return UUID(str(claims["sub"]))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid access token.") from exc


@router.post("/projects/{project_id}")
def generate_from_confirmed_requirements(
    project_id: UUID,
    options: GenerateConfirmedOptions,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    user_id = _resolve_user_id(authorization)
    billing_repository = create_billing_repository()
    project_repository = create_project_repository_from_environment()
    try:
        orchestrator = FinalGenerationOrchestrator(
            requirements_store=RequirementsStore.from_environment(),
            billing_service=BillingService(billing_repository),
            project_service=ProjectRevisionService(project_repository),
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
        UnsupportedConfirmedRequirement,
        Phase24FinalizationError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        billing_repository.close()
        project_repository.close()

    generation_result = run.generation_result
    if run.revision is None or run.canonical is None:
        return {
            "status": generation_result.disposition.value,
            "billing_reason": run.billing_reason,
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
