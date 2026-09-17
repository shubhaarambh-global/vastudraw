from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from ai_vastu.auth import (
    AccessTokenVerifier,
    AuthenticatedUser,
    AuthenticationError,
    create_access_token_verifier_from_environment,
)
from ai_vastu.generation import (
    ArchitecturalGenerationRequest,
    ArchitecturalGenerationResult,
    GenerationInputError,
    generate_architectural_plan,
)
from ai_vastu.generation_intake import (
    MAX_FILE_BYTES,
    MAX_TOTAL_BYTES,
    GenerationIntakeError,
    GenerationIntakeNotFoundError,
    GenerationIntakeRecord,
    GenerationIntakeStore,
    IncomingGenerationAttachment,
    create_generation_intake_store_from_environment,
)
from ai_vastu.plan_intake import (
    PlanAnalysisNotFoundError,
    PlanAnalysisResult,
    PlanAnalysisStore,
    PlanGeometryConfirmationInput,
    PlanGeometryConfirmationRecord,
    PlanIntakeConfigurationError,
    PlanIntakeProviderError,
    PlanRecognitionInput,
    PlanReferenceBlob,
    PlanReferenceKind,
    create_plan_intake_service,
)
from ai_vastu.plan_schema import PLAN_SCHEMA_VERSION, PlanDocument
from ai_vastu.production.middleware import ProductionHardeningMiddleware
from ai_vastu.projects import (
    AppendRevisionCommand,
    DuplicateProjectError,
    DuplicateRevisionError,
    OutputArtifactRef,
    ProjectNotFoundError,
    ProjectRecord,
    ProjectRepository,
    ProjectRevisionService,
    RevisionConflictError,
    RevisionNotFoundError,
    RevisionRecord,
    create_project_repository_from_environment,
)
from ai_vastu.release import (
    ProductionReadinessReport,
    evaluate_production_mvp_readiness,
)
from app.billing_routes import router as billing_router
from app.confirmed_generation_routes import router as confirmed_generation_router
from app.requirements_routes import router as requirements_router

_bearer = HTTPBearer(auto_error=False)


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=200)
    project_id: UUID | None = None


class AppendRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document: dict[str, Any]
    expected_parent_revision_id: UUID | None = None
    source_candidate_id: UUID | None = None
    note: str | None = Field(default=None, max_length=2_000)
    generated_outputs: tuple[OutputArtifactRef, ...] = ()


def _service(request: Request) -> ProjectRevisionService:
    return cast(ProjectRevisionService, request.app.state.project_service)


def _generation_intake_store(request: Request) -> GenerationIntakeStore:
    return cast(GenerationIntakeStore, request.app.state.generation_intake_store)


def _current_user(
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


ProjectServiceDependency = Annotated[ProjectRevisionService, Depends(_service)]
GenerationIntakeStoreDependency = Annotated[
    GenerationIntakeStore, Depends(_generation_intake_store)
]
CurrentUserDependency = Annotated[AuthenticatedUser, Depends(_current_user)]


def _require_project_owner(
    service: ProjectRevisionService,
    project_id: UUID,
    user: AuthenticatedUser,
) -> None:
    if not service.is_project_owner(project_id, user.user_id):
        # Do not reveal whether another user's project exists.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} does not exist.",
        )


def create_app(
    repository: ProjectRepository | None = None,
    access_token_verifier: AccessTokenVerifier | None = None,
    generation_intake_store: GenerationIntakeStore | None = None,
) -> FastAPI:
    project_repository = (
        repository if repository is not None else create_project_repository_from_environment()
    )
    verifier = (
        access_token_verifier
        if access_token_verifier is not None
        else create_access_token_verifier_from_environment()
    )

    intake_store = (
        generation_intake_store
        if generation_intake_store is not None
        else create_generation_intake_store_from_environment()
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            project_repository.close()

    app = FastAPI(
        title="AI Vastu Architect API",
        version="0.19.0",
        lifespan=lifespan,
    )
    app.state.project_service = ProjectRevisionService(project_repository)
    app.state.generation_intake_store = intake_store
    app.state.access_token_verifier = verifier
    allowed_origins = tuple(
        origin.strip()
        for origin in os.environ.get(
            "AI_VASTU_WEB_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "phase": "19",
            "plan_schema_version": PLAN_SCHEMA_VERSION,
        }

    @app.get(
        "/system/release-readiness",
        response_model=ProductionReadinessReport,
        tags=["system"],
    )
    def release_readiness() -> ProductionReadinessReport:
        repository_root = Path(__file__).resolve().parents[3]
        return evaluate_production_mvp_readiness(repository_root)

    @app.post(
        "/projects/{project_id}/generation-intakes",
        response_model=GenerationIntakeRecord,
        status_code=status.HTTP_201_CREATED,
        tags=["generation"],
    )
    async def create_generation_intake(
        project_id: UUID,
        service: ProjectServiceDependency,
        intake_store: GenerationIntakeStoreDependency,
        user: CurrentUserDependency,
        prompt: Annotated[str, Form(min_length=1, max_length=12_000)],
        files: Annotated[list[UploadFile] | None, File()] = None,
    ) -> GenerationIntakeRecord:
        _require_project_owner(service, project_id, user)
        uploads: list[IncomingGenerationAttachment] = []
        total_bytes = 0
        for upload in files or []:
            content = await upload.read(MAX_FILE_BYTES + 1)
            if len(content) > MAX_FILE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Each generation reference must be 20 MiB or smaller.",
                )
            total_bytes += len(content)
            if total_bytes > MAX_TOTAL_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Combined generation references must be 50 MiB or smaller.",
                )
            uploads.append(
                IncomingGenerationAttachment(
                    original_filename=(upload.filename or "reference")[:255],
                    media_type=upload.content_type or "application/octet-stream",
                    content=content,
                )
            )
        try:
            return intake_store.create(project_id, prompt, tuple(uploads))
        except GenerationIntakeError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    @app.get(
        "/projects/{project_id}/generation-intakes",
        response_model=tuple[GenerationIntakeRecord, ...],
        tags=["generation"],
    )
    def list_generation_intakes(
        project_id: UUID,
        service: ProjectServiceDependency,
        intake_store: GenerationIntakeStoreDependency,
        user: CurrentUserDependency,
    ) -> tuple[GenerationIntakeRecord, ...]:
        _require_project_owner(service, project_id, user)
        return intake_store.list_for_project(project_id)

    @app.get(
        "/projects/{project_id}/generation-intakes/{intake_id}",
        response_model=GenerationIntakeRecord,
        tags=["generation"],
    )
    def get_generation_intake(
        project_id: UUID,
        intake_id: UUID,
        service: ProjectServiceDependency,
        intake_store: GenerationIntakeStoreDependency,
        user: CurrentUserDependency,
    ) -> GenerationIntakeRecord:
        _require_project_owner(service, project_id, user)
        try:
            return intake_store.get(project_id, intake_id)
        except GenerationIntakeNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    @app.post(
        "/projects/{project_id}/generation-intakes/{intake_id}/plan-analysis",
        response_model=PlanAnalysisResult,
        tags=["generation"],
    )
    def analyze_generation_intake_plan(
        project_id: UUID,
        intake_id: UUID,
        service: ProjectServiceDependency,
        intake_store: GenerationIntakeStoreDependency,
        user: CurrentUserDependency,
    ) -> PlanAnalysisResult:
        _require_project_owner(service, project_id, user)
        try:
            intake = intake_store.get(project_id, intake_id)
            references: list[PlanReferenceBlob] = []
            for item in intake.attachments:
                stored, data = intake_store.read_attachment(
                    project_id,
                    intake_id,
                    item.attachment_id,
                )
                references.append(
                    PlanReferenceBlob(
                        filename=stored.original_filename,
                        content_type=stored.media_type,
                        kind=PlanReferenceKind(stored.kind.value),
                        data=data,
                    )
                )
            if not references:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Upload a plan reference before requesting plan analysis.",
                )

            result = create_plan_intake_service().analyze(
                PlanRecognitionInput(
                    project_id=project_id,
                    intake_id=intake_id,
                    prompt=intake.prompt,
                    references=tuple(references),
                )
            )
            return PlanAnalysisStore(intake_store.root).save_analysis(result)
        except GenerationIntakeNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except PlanIntakeConfigurationError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except PlanIntakeProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    @app.get(
        "/projects/{project_id}/generation-intakes/{intake_id}/plan-analysis",
        response_model=PlanAnalysisResult,
        tags=["generation"],
    )
    def get_generation_intake_plan_analysis(
        project_id: UUID,
        intake_id: UUID,
        service: ProjectServiceDependency,
        intake_store: GenerationIntakeStoreDependency,
        user: CurrentUserDependency,
    ) -> PlanAnalysisResult:
        _require_project_owner(service, project_id, user)
        try:
            intake_store.get(project_id, intake_id)
            return PlanAnalysisStore(intake_store.root).get_analysis(
                project_id,
                intake_id,
            )
        except GenerationIntakeNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except PlanAnalysisNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    @app.post(
        "/projects/{project_id}/generation-intakes/{intake_id}/plan-confirmation",
        response_model=PlanGeometryConfirmationRecord,
        tags=["generation"],
    )
    def confirm_generation_intake_plan_geometry(
        project_id: UUID,
        intake_id: UUID,
        payload: PlanGeometryConfirmationInput,
        service: ProjectServiceDependency,
        intake_store: GenerationIntakeStoreDependency,
        user: CurrentUserDependency,
    ) -> PlanGeometryConfirmationRecord:
        _require_project_owner(service, project_id, user)
        try:
            intake_store.get(project_id, intake_id)
            return PlanAnalysisStore(intake_store.root).save_confirmation(
                project_id,
                intake_id,
                payload,
            )
        except GenerationIntakeNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    @app.get(
        "/projects/{project_id}/generation-intakes/{intake_id}/plan-confirmation",
        response_model=PlanGeometryConfirmationRecord,
        tags=["generation"],
    )
    def get_generation_intake_plan_confirmation(
        project_id: UUID,
        intake_id: UUID,
        service: ProjectServiceDependency,
        intake_store: GenerationIntakeStoreDependency,
        user: CurrentUserDependency,
    ) -> PlanGeometryConfirmationRecord:
        _require_project_owner(service, project_id, user)
        try:
            intake_store.get(project_id, intake_id)
            return PlanAnalysisStore(intake_store.root).get_confirmation(
                project_id,
                intake_id,
            )
        except (GenerationIntakeNotFoundError, PlanAnalysisNotFoundError) as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    @app.post(
        "/generation/architectural",
        response_model=ArchitecturalGenerationResult,
        tags=["generation"],
    )
    async def generate_architectural(
        request: Request,
        _user: CurrentUserDependency,
    ) -> ArchitecturalGenerationResult:
        try:
            payload = ArchitecturalGenerationRequest.model_validate_json(await request.body())
            return generate_architectural_plan(payload)
        except (GenerationInputError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    @app.get("/projects", response_model=tuple[ProjectRecord, ...], tags=["projects"])
    def list_projects(
        service: ProjectServiceDependency,
        user: CurrentUserDependency,
    ) -> tuple[ProjectRecord, ...]:
        return service.list_projects_for_owner(user.user_id)

    @app.post(
        "/projects",
        response_model=ProjectRecord,
        status_code=status.HTTP_201_CREATED,
        tags=["projects"],
    )
    def create_project(
        payload: CreateProjectRequest,
        service: ProjectServiceDependency,
        user: CurrentUserDependency,
    ) -> ProjectRecord:
        try:
            return service.create_project(payload.name, payload.project_id, user.user_id)
        except DuplicateProjectError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

    @app.get("/projects/{project_id}", response_model=ProjectRecord, tags=["projects"])
    def get_project(
        project_id: UUID,
        service: ProjectServiceDependency,
        user: CurrentUserDependency,
    ) -> ProjectRecord:
        _require_project_owner(service, project_id, user)
        try:
            return service.get_project(project_id)
        except ProjectNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    @app.post(
        "/projects/{project_id}/revisions",
        response_model=RevisionRecord,
        status_code=status.HTTP_201_CREATED,
        tags=["projects"],
    )
    def append_revision(
        project_id: UUID,
        payload: AppendRevisionRequest,
        service: ProjectServiceDependency,
        user: CurrentUserDependency,
    ) -> RevisionRecord:
        _require_project_owner(service, project_id, user)
        try:
            document = PlanDocument.model_validate_json(
                json.dumps(payload.document, sort_keys=True, separators=(",", ":"))
            )
            command = AppendRevisionCommand(
                project_id=project_id,
                document=document,
                expected_parent_revision_id=payload.expected_parent_revision_id,
                source_candidate_id=payload.source_candidate_id,
                note=payload.note,
                generated_outputs=payload.generated_outputs,
            )
            return service.append_revision(command)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except ProjectNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except (DuplicateRevisionError, RevisionConflictError) as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

    @app.get(
        "/projects/{project_id}/revisions",
        response_model=tuple[RevisionRecord, ...],
        tags=["projects"],
    )
    def list_revisions(
        project_id: UUID,
        service: ProjectServiceDependency,
        user: CurrentUserDependency,
    ) -> tuple[RevisionRecord, ...]:
        _require_project_owner(service, project_id, user)
        try:
            return service.list_revisions(project_id)
        except ProjectNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    @app.get(
        "/projects/{project_id}/revisions/{revision_id}",
        response_model=RevisionRecord,
        tags=["projects"],
    )
    def get_revision(
        project_id: UUID,
        revision_id: UUID,
        service: ProjectServiceDependency,
        user: CurrentUserDependency,
    ) -> RevisionRecord:
        _require_project_owner(service, project_id, user)
        try:
            return service.get_revision(project_id, revision_id)
        except RevisionNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    return app


app = create_app()

app.include_router(billing_router)

app.include_router(requirements_router)

app.include_router(confirmed_generation_router)

# Phase 25 production defense-in-depth middleware.
app.add_middleware(ProductionHardeningMiddleware)
