from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from ai_vastu.requirements import (
    ConfirmedRequirements,
    RequirementsService,
    RequirementsStore,
    create_provider,
)
from ai_vastu.requirements.providers import ReferenceAsset
from app.auth_dependencies import CurrentUserDependency, project_service, require_project_owner

router = APIRouter(prefix="/requirements", tags=["requirements"])

_ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}
_MAX_FILES = 8
_MAX_FILE_BYTES = 20 * 1024 * 1024
_MAX_TOTAL_BYTES = 50 * 1024 * 1024


def _validate_signature(content_type: str, data: bytes) -> None:
    if content_type == "image/jpeg" and not data.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=422, detail="Invalid JPEG bytes.")
    if content_type == "image/png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=422, detail="Invalid PNG bytes.")
    if content_type == "application/pdf" and not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="Invalid PDF bytes.")


async def _read_references(files: list[UploadFile]) -> tuple[ReferenceAsset, ...]:
    if len(files) > _MAX_FILES:
        raise HTTPException(status_code=413, detail="Too many reference files.")

    total = 0
    assets: list[ReferenceAsset] = []
    for file in files:
        content_type = file.content_type or ""
        if content_type not in _ALLOWED_TYPES:
            raise HTTPException(status_code=415, detail="Unsupported reference type.")
        data = await file.read(_MAX_FILE_BYTES + 1)
        if len(data) > _MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="Reference file too large.")
        total += len(data)
        if total > _MAX_TOTAL_BYTES:
            raise HTTPException(status_code=413, detail="Combined references too large.")
        _validate_signature(content_type, data)
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
    draft = _service().interpret(
        user_id=user.user_id,
        project_id=project_id,
        prompt=prompt,
        references=references,
    )
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
