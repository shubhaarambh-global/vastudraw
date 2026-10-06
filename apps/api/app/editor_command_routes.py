"""Apply supported exact editor commands to immutable saved revisions."""

from __future__ import annotations

import os
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

from ai_vastu.architectural_geometry.circulation import validate_circulation
from ai_vastu.plan_schema import PlanDocument
from ai_vastu.projects import AppendRevisionCommand, RevisionConflictError
from ai_vastu.requirements.saved_revision import regenerate_room_dimension
from ai_vastu.requirements.store import RequirementsStore
from ai_vastu.validation.vehicle_access import validate_document_vehicle_access
from app.auth_dependencies import CurrentUserDependency, project_service, require_project_owner

router = APIRouter(tags=["editor-commands"])


class RoomLockCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["ROOM_LOCK"]
    room_id: UUID
    locked: StrictBool


class RoomDimensionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["ROOM_SET_DIMENSION"]
    room_id: UUID
    axis: Literal["WIDTH", "DEPTH"]
    target_mm: StrictInt = Field(gt=0, le=100_000)


EditorCommand = Annotated[RoomLockCommand | RoomDimensionCommand, Field(discriminator="kind")]


class EditorCommandsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    protocol_version: Literal["1.0.0"]
    project_id: UUID
    base_revision_id: UUID
    commands: list[EditorCommand] = Field(min_length=1, max_length=100)


def apply_room_locks(document: PlanDocument, commands: list[RoomLockCommand]) -> PlanDocument:
    known = {room.id for floor in document.floors for room in floor.rooms}
    if any(command.room_id not in known for command in commands):
        raise ValueError("Unknown saved room.")
    locks = {command.room_id: command.locked for command in commands}
    floors = tuple(
        floor.model_copy(
            update={
                "rooms": tuple(
                    room.model_copy(update={"locked": locks.get(room.id, room.locked)})
                    for room in floor.rooms
                )
            }
        )
        for floor in document.floors
    )
    if floors == document.floors:
        raise ValueError("No effective room lock change.")
    return document.model_copy(
        update={
            "floors": floors,
            "revision_id": uuid4(),
            "content_hash": None,
        }
    ).with_content_hash()


@router.post("/projects/{project_id}/editor-commands")
def save_editor_commands(
    project_id: UUID,
    payload: EditorCommandsRequest,
    request: Request,
    user: CurrentUserDependency,
) -> dict[str, object]:
    service = project_service(request)
    require_project_owner(service, project_id, user)
    if os.getenv("APP_ENV", "development").strip().lower() != "development":
        raise HTTPException(403, "Exact editor command application requires development mode.")
    if payload.project_id != project_id:
        raise HTTPException(422, "Editor project identity does not match.")
    if service.get_project(project_id).current_revision_id != payload.base_revision_id:
        raise HTTPException(409, "Reload the current revision before applying edits.")
    base = service.get_revision(project_id, payload.base_revision_id)
    try:
        if all(isinstance(command, RoomLockCommand) for command in payload.commands):
            document = apply_room_locks(
                base.document,
                [command for command in payload.commands if isinstance(command, RoomLockCommand)],
            )
            candidate_id = base.source_candidate_id
        elif len(payload.commands) == 1 and isinstance(payload.commands[0], RoomDimensionCommand):
            command = payload.commands[0]
            confirmed = RequirementsStore.from_environment().confirmed_for_context(
                project_id=project_id,
                user_id=user.user_id,
                context_ids={
                    item.id
                    for item in base.document.assumptions
                    if item.code == "PHASE24_CONFIRMED_CONTEXT" and item.confirmed_by_user
                },
            )
            canonical = regenerate_room_dimension(
                base=base.document,
                confirmed=confirmed,
                room_id=command.room_id,
                axis="width" if command.axis == "WIDTH" else "depth",
                target_mm=command.target_mm,
            )
            document, candidate_id = canonical.document, canonical.candidate_id
        else:
            raise ValueError("Submit room locks or one exact room dimension separately.")
        # New saved revisions must satisfy canonical access; never mutate a legacy base.
        if len(document.floors) != 1 or not validate_circulation(document.floors[0]).accepted:
            raise ValueError("New edits require independently valid single-floor circulation.")
        if validate_document_vehicle_access(document):
            raise ValueError("New edits require canonical road-aligned vehicle access.")
        revision = service.append_revision(
            AppendRevisionCommand(
                project_id=project_id,
                document=document,
                expected_parent_revision_id=payload.base_revision_id,
                source_candidate_id=candidate_id,
                note="Exact editor commands applied server-side.",
            )
        )
    except RevisionConflictError as exc:
        raise HTTPException(
            409, "The saved revision changed; reload before applying edits."
        ) from exc
    except (ValueError, KeyError, RuntimeError) as exc:
        raise HTTPException(
            422, "These exact edits cannot produce a valid saved revision."
        ) from exc
    return {"revision": revision.model_dump(mode="json")}
