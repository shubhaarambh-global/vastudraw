from __future__ import annotations

import os
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from ai_vastu.architectural_brain.errors import ArchitecturalBrainProviderError
from ai_vastu.architectural_brain.models import RevisionOperation
from ai_vastu.architectural_brain.ollama_local_revision import interpret_revision_with_ollama_local
from ai_vastu.projects import AppendRevisionCommand, RevisionConflictError, RevisionNotFoundError
from ai_vastu.requirements.generation_adapter import compile_confirmed_requirements
from ai_vastu.requirements.saved_revision import regenerate_room_dimension
from ai_vastu.requirements.store import RequirementsStore
from app.auth_dependencies import CurrentUserDependency, project_service, require_project_owner
from app.confirmed_generation_routes import _provider_http_error

router = APIRouter(tags=["revision-chat"])


class RevisionChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    base_revision_id: UUID
    request: str = Field(min_length=1, max_length=2000)


@router.post("/projects/{project_id}/revision-chat")
def revise_saved_plan(
    project_id: UUID,
    payload: RevisionChatRequest,
    request: Request,
    user: CurrentUserDependency,
) -> dict[str, object]:
    service = project_service(request)
    require_project_owner(service, project_id, user)
    if (
        os.getenv("APP_ENV", "development").strip().lower() != "development"
        or os.getenv("AI_VASTU_REVISION_PROVIDER", "").strip().lower() != "ollama_local"
    ):
        raise HTTPException(403, "Revision chat requires the local development Ollama profile.")
    if service.get_project(project_id).current_revision_id != payload.base_revision_id:
        raise HTTPException(409, "Reload the current saved revision before requesting changes.")
    try:
        base = service.get_revision(project_id, payload.base_revision_id)
    except RevisionNotFoundError as exc:
        raise HTTPException(404, "Saved revision was not found.") from exc
    if not payload.request.strip():
        raise HTTPException(422, "Enter a room dimension change.")
    if any(room.locked for floor in base.document.floors for room in floor.rooms):
        raise HTTPException(422, "Revision regeneration cannot preserve locked room geometry.")
    try:
        confirmed = RequirementsStore.from_environment().confirmed_for_context(
            project_id=project_id,
            user_id=user.user_id,
            context_ids={
                item.id
                for item in base.document.assumptions
                if item.code == "PHASE24_CONFIRMED_CONTEXT" and item.confirmed_by_user
            },
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            422, "The saved plan's confirmed requirements are unavailable."
        ) from exc
    try:
        intent = interpret_revision_with_ollama_local(
            project_id=project_id,
            base_revision_id=payload.base_revision_id,
            request=payload.request,
            supported_room_types=tuple(
                sorted(
                    {room.room_type.value for floor in base.document.floors for room in floor.rooms}
                )
            ),
        )
    except RuntimeError as exc:
        raise _provider_http_error(
            ArchitecturalBrainProviderError.from_exception(exc).category
        ) from exc
    # Initial support is deliberately bounded: no ignored directives or silent no-ops.
    if len(intent.directives) != 1:
        raise HTTPException(422, "Request one room width or depth increase at a time.")
    directive = intent.directives[0]
    if directive.operation is not RevisionOperation.INCREASE_DIMENSION:
        raise HTTPException(422, "The interpreted operation is not a supported dimension increase.")
    if directive.axis not in {"WIDTH", "DEPTH"}:
        raise HTTPException(422, "The interpreted dimension needs an explicit width or depth axis.")
    if directive.delta_mm is None or not 0 < directive.delta_mm <= 3000:
        raise HTTPException(422, "The interpreted increase needs a positive delta up to 3000 mm.")
    if (
        directive.operation is not RevisionOperation.INCREASE_DIMENSION
        or directive.axis not in {"WIDTH", "DEPTH"}
        or directive.delta_mm is None
        or not 0 < directive.delta_mm <= 3000
        or any(
            value is not None
            for value in (
                directive.target_mm,
                directive.target_side,
                directive.related_room_type,
                directive.quantity,
            )
        )
    ):
        raise HTTPException(
            422, "Supported changes increase one room width or depth by up to 3 metres."
        )
    rooms = [
        room
        for floor in base.document.floors
        for room in floor.rooms
        if room.room_type.value == directive.room_type
    ]
    if len(rooms) != 1:
        raise HTTPException(422, "The requested room must identify one saved room unambiguously.")
    room = rooms[0]
    axis: Literal["width", "depth"] = "width" if directive.axis == "WIDTH" else "depth"
    values = [point.x_mm if axis == "width" else point.y_mm for point in room.polygon.outer]
    previous_mm = max(values) - min(values)
    requested_mm = previous_mm + directive.delta_mm
    try:
        step_mm = compile_confirmed_requirements(confirmed).request.planner_config.solver_step_mm
        applied_mm = ((requested_mm + step_mm - 1) // step_mm) * step_mm
        canonical = regenerate_room_dimension(
            base=base.document,
            confirmed=confirmed,
            room_id=room.id,
            axis=axis,
            target_mm=applied_mm,
            exact=True,
        )
        document = canonical.document
        revision = service.append_revision(
            AppendRevisionCommand(
                project_id=project_id,
                document=document,
                expected_parent_revision_id=payload.base_revision_id,
                source_candidate_id=canonical.candidate_id,
                note="Local revision chat: deterministic regeneration from saved requirements.",
            )
        )
    except RevisionConflictError as exc:
        raise HTTPException(
            409, "The saved revision changed; reload before requesting changes."
        ) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            422, "A valid plan satisfying this change could not be generated."
        ) from exc
    return {
        "revision": revision.model_dump(mode="json"),
        "editor_path": f"/editor?project={project_id}",
        "dimension_change": {
            "room_type": room.room_type.value,
            "axis": directive.axis,
            "previous_mm": previous_mm,
            "requested_mm": requested_mm,
            "applied_mm": applied_mm,
            "rounding_mm": applied_mm - requested_mm,
            "solver_step_mm": step_mm,
        },
    }
