from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field, model_validator

from ai_vastu.plan_schema import PlanDocument
from ai_vastu.plan_schema.base import FrozenModel

PROJECT_STORE_VERSION = "1.0.0"
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeInt = Annotated[int, Field(ge=0)]


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")


class OutputArtifactRef(FrozenModel):
    kind: str
    uri: str
    content_hash: str
    media_type: str | None = None

    @model_validator(mode="after")
    def validate_hash(self) -> OutputArtifactRef:
        if not _HASH_RE.fullmatch(self.content_hash):
            raise ValueError("Output artifact content_hash must be lowercase SHA-256 hex.")
        return self


class ProjectRecord(FrozenModel):
    project_id: UUID
    name: str
    created_at: datetime
    current_revision_id: UUID | None = None
    current_revision_number: NonNegativeInt = 0

    @model_validator(mode="after")
    def validate_state(self) -> ProjectRecord:
        _require_aware(self.created_at, "created_at")
        if not self.name.strip():
            raise ValueError("Project name cannot be blank.")
        if self.current_revision_number == 0 and self.current_revision_id is not None:
            raise ValueError("A project with zero revisions cannot have current_revision_id.")
        if self.current_revision_number > 0 and self.current_revision_id is None:
            raise ValueError("A project with revisions requires current_revision_id.")
        return self


class AppendRevisionCommand(FrozenModel):
    project_id: UUID
    document: PlanDocument
    expected_parent_revision_id: UUID | None = None
    source_candidate_id: UUID | None = None
    note: str | None = None
    generated_outputs: tuple[OutputArtifactRef, ...] = ()

    @model_validator(mode="after")
    def validate_project_identity(self) -> AppendRevisionCommand:
        if self.document.project_id != self.project_id:
            raise ValueError("PlanDocument project_id must match append command project_id.")
        return self


class RevisionRecord(FrozenModel):
    project_id: UUID
    revision_id: UUID
    revision_number: PositiveInt
    parent_revision_id: UUID | None = None
    created_at: datetime
    document: PlanDocument
    plan_document_hash: str
    source_candidate_id: UUID | None = None
    note: str | None = None
    generated_outputs: tuple[OutputArtifactRef, ...] = ()
    payload_hash: str

    @model_validator(mode="after")
    def validate_integrity(self) -> RevisionRecord:
        _require_aware(self.created_at, "created_at")
        for field_name, value in (
            ("plan_document_hash", self.plan_document_hash),
            ("payload_hash", self.payload_hash),
        ):
            if not _HASH_RE.fullmatch(value):
                raise ValueError(f"{field_name} must be lowercase SHA-256 hex.")
        if self.document.project_id != self.project_id:
            raise ValueError("Revision project_id does not match PlanDocument project_id.")
        if self.document.revision_id != self.revision_id:
            raise ValueError("Revision revision_id does not match PlanDocument revision_id.")
        canonical = self.document.with_content_hash()
        if canonical.content_hash != self.plan_document_hash:
            raise ValueError("plan_document_hash does not match canonical PlanDocument content.")
        if self.payload_hash != self.compute_payload_hash():
            raise ValueError("payload_hash does not match immutable revision payload.")
        return self

    def compute_payload_hash(self) -> str:
        payload = {
            "project_id": str(self.project_id),
            "revision_id": str(self.revision_id),
            "revision_number": self.revision_number,
            "parent_revision_id": (
                None if self.parent_revision_id is None else str(self.parent_revision_id)
            ),
            "plan_document_hash": self.plan_document_hash,
            "source_candidate_id": (
                None if self.source_candidate_id is None else str(self.source_candidate_id)
            ),
            "note": self.note,
            "generated_outputs": [item.model_dump(mode="json") for item in self.generated_outputs],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
