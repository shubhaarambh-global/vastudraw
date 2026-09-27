from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from ai_vastu.provider_runtime import ProviderFailureCategory
from ai_vastu.requirements import (
    ConfirmedRequirements,
    RequirementsService,
    RequirementsStore,
    create_provider,
)
from ai_vastu.requirements.errors import (
    RequirementsConfigurationError,
    RequirementsProviderError,
)
from ai_vastu.requirements.providers import ReferenceAsset
from ai_vastu.upload_validation import (
    UploadContentError,
    validate_image_content,
    validate_pdf_content,
)
from app.auth_dependencies import CurrentUserDependency, project_service, require_project_owner

router = APIRouter(prefix="/requirements", tags=["requirements"])

_ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}
_ALLOWED_SUFFIXES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "application/pdf": {".pdf"},
}
_MAX_FILES = 8
_MAX_FILE_BYTES = 20 * 1024 * 1024
_MAX_TOTAL_BYTES = 50 * 1024 * 1024


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


def _validate_signature(content_type: str, data: bytes) -> None:
    try:
        if content_type in {"image/jpeg", "image/png"}:
            validate_image_content(content_type, data)
        else:
            validate_pdf_content(data)
    except UploadContentError as exc:
        label = {
            "image/jpeg": "JPEG",
            "image/png": "PNG",
            "application/pdf": "PDF",
        }[content_type]
        raise HTTPException(status_code=422, detail=f"Invalid {label} bytes.") from exc


async def _read_references(files: list[UploadFile]) -> tuple[ReferenceAsset, ...]:
    if len(files) > _MAX_FILES:
        raise HTTPException(status_code=413, detail="Too many reference files.")

    total = 0
    assets: list[ReferenceAsset] = []
    for file in files:
        content_type = file.content_type or ""
        if content_type not in _ALLOWED_TYPES:
            raise HTTPException(status_code=415, detail="Unsupported reference type.")
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in _ALLOWED_SUFFIXES[content_type]:
            raise HTTPException(status_code=415, detail="Unsupported reference type.")
        data = await file.read(_MAX_FILE_BYTES + 1)
        if len(data) > _MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="Reference file too large.")
        total += len(data)
        if total > _MAX_TOTAL_BYTES:
            raise HTTPException(status_code=413, detail="Combined references too large.")
        await run_in_threadpool(_validate_signature, content_type, data)
        assets.append(
            ReferenceAsset(
                filename=file.filename or "reference",
                content_type=content_type,
                data=data,
            )
        )
    return tuple(assets)


def _service() -> RequirementsService:
    return RequirementsService(
        provider=create_provider(),
        store=RequirementsStore.from_environment(),
    )


@router.post("/interpret")
async def interpret_requirements(
    project_id: Annotated[UUID, Form()],
    prompt: Annotated[str, Form(min_length=1, max_length=20_000)],
    request: Request,
    user: CurrentUserDependency,
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> dict[str, object]:
    require_project_owner(project_service(request), project_id, user)
    references = await _read_references(files or [])
    try:
        service = _service()
        draft = await run_in_threadpool(
            service.interpret,
            user_id=user.user_id,
            project_id=project_id,
            prompt=prompt,
            references=references,
        )
    except RequirementsConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail="AI provider is not configured.",
        ) from exc
    except RequirementsProviderError as exc:
        raise _provider_http_error(exc.category) from exc
    return {
        "draft": draft.model_dump(mode="json"),
        "ready_for_confirmation": draft.ready_for_confirmation,
    }


@router.get("/drafts/{draft_id}")
def get_requirement_draft(
    draft_id: UUID,
    request: Request,
    user: CurrentUserDependency,
) -> dict[str, object]:
    try:
        draft = RequirementsStore.from_environment().get_draft(draft_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Requirement draft not found.") from exc
    if draft.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Requirement draft not found.")
    require_project_owner(project_service(request), draft.project_id, user)
    return {
        "draft": draft.model_dump(mode="json"),
        "ready_for_confirmation": draft.ready_for_confirmation,
    }


@router.post("/drafts/{draft_id}/confirm")
def confirm_requirements(
    draft_id: UUID,
    confirmed: ConfirmedRequirements,
    request: Request,
    user: CurrentUserDependency,
) -> dict[str, object]:
    if confirmed.draft_id != draft_id:
        raise HTTPException(status_code=422, detail="Draft identity mismatch.")
    try:
        draft = RequirementsStore.from_environment().get_draft(draft_id)
        if draft.user_id != user.user_id:
            raise PermissionError("Requirement draft does not belong to this user.")
        require_project_owner(project_service(request), draft.project_id, user)
        result = _service().confirm(
            authenticated_user_id=user.user_id,
            confirmed=confirmed,
        )
    except (KeyError, PermissionError) as exc:
        raise HTTPException(status_code=404, detail="Requirement draft not found.") from exc
    return {"confirmed": result.model_dump(mode="json")}


@router.get("/drafts/{draft_id}/confirmed")
def get_confirmed_requirements(
    draft_id: UUID,
    request: Request,
    user: CurrentUserDependency,
) -> dict[str, object]:
    try:
        result = RequirementsStore.from_environment().get_confirmed(draft_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Confirmed requirements not found.",
        ) from exc
    if result.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Confirmed requirements not found.")
    require_project_owner(project_service(request), result.project_id, user)
    return {"confirmed": result.model_dump(mode="json")}
