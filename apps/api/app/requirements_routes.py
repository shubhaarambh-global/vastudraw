from __future__ import annotations

import os
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from ai_vastu.requirements import (
    ConfirmedRequirements,
    RequirementsService,
    RequirementsStore,
    create_provider,
)
from ai_vastu.requirements.providers import ReferenceAsset

router = APIRouter(prefix="/requirements", tags=["requirements"])

_ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}
_MAX_FILES = 8
_MAX_FILE_BYTES = 20 * 1024 * 1024
_MAX_TOTAL_BYTES = 50 * 1024 * 1024


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
    files: Annotated[list[UploadFile] | None, File()] = None,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    user_id = _resolve_user_id(authorization)
    references = await _read_references(files or [])
    draft = _service().interpret(
        user_id=user_id,
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
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    user_id = _resolve_user_id(authorization)
    try:
        draft = _service().get_draft(draft_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Requirement draft not found.") from exc
    if draft.user_id != user_id:
        raise HTTPException(status_code=404, detail="Requirement draft not found.")
    return {
        "draft": draft.model_dump(mode="json"),
        "ready_for_confirmation": draft.ready_for_confirmation,
    }


@router.post("/drafts/{draft_id}/confirm")
def confirm_requirements(
    draft_id: UUID,
    confirmed: ConfirmedRequirements,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    user_id = _resolve_user_id(authorization)
    if confirmed.draft_id != draft_id:
        raise HTTPException(status_code=422, detail="Draft identity mismatch.")
    try:
        result = _service().confirm(
            authenticated_user_id=user_id,
            confirmed=confirmed,
        )
    except (KeyError, PermissionError) as exc:
        raise HTTPException(status_code=404, detail="Requirement draft not found.") from exc
    return {"confirmed": result.model_dump(mode="json")}


@router.get("/drafts/{draft_id}/confirmed")
def get_confirmed_requirements(
    draft_id: UUID,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    user_id = _resolve_user_id(authorization)
    try:
        result = _service().get_confirmed(draft_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Confirmed requirements not found.",
        ) from exc
    if result.user_id != user_id:
        raise HTTPException(status_code=404, detail="Confirmed requirements not found.")
    return {"confirmed": result.model_dump(mode="json")}
