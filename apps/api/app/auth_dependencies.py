from __future__ import annotations

from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ai_vastu.auth import AccessTokenVerifier, AuthenticatedUser, AuthenticationError
from ai_vastu.projects.service import ProjectRevisionService

_bearer = HTTPBearer(auto_error=False)


def current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    verifier = cast(AccessTokenVerifier, request.app.state.access_token_verifier)
    try:
        return verifier.verify(credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


CurrentUserDependency = Annotated[AuthenticatedUser, Depends(current_user)]


def project_service(request: Request) -> ProjectRevisionService:
    return cast(ProjectRevisionService, request.app.state.project_service)


def require_project_owner(
    service: ProjectRevisionService,
    project_id: UUID,
    user: AuthenticatedUser,
) -> None:
    if not service.is_project_owner(project_id, user.user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} does not exist.",
        )
