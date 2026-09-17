from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import Field, model_validator

from ai_vastu.plan_schema.base import FrozenModel

_HASH_LENGTH = 64
PromptText = Annotated[str, Field(min_length=1, max_length=12_000)]
FilenameText = Annotated[str, Field(min_length=1, max_length=255)]
NonNegativeInt = Annotated[int, Field(ge=0)]


class GenerationReferenceKind(StrEnum):
    IMAGE = "IMAGE"
    PDF = "PDF"
    DXF = "DXF"
    DWG = "DWG"


class GenerationAttachmentRecord(FrozenModel):
    attachment_id: UUID
    kind: GenerationReferenceKind
    original_filename: FilenameText
    media_type: str
    size_bytes: NonNegativeInt
    sha256: str
    storage_name: str

    @model_validator(mode="after")
    def validate_integrity(self) -> GenerationAttachmentRecord:
        if not self.original_filename.strip():
            raise ValueError("original_filename must not be blank.")
        if not self.media_type.strip():
            raise ValueError("media_type must not be blank.")
        if not self.storage_name.strip() or "/" in self.storage_name or "\\" in self.storage_name:
            raise ValueError("storage_name must be a single server-generated filename.")
        if len(self.sha256) != _HASH_LENGTH or any(
            char not in "0123456789abcdef" for char in self.sha256
        ):
            raise ValueError("sha256 must be a lowercase SHA-256 hex digest.")
        return self


class GenerationIntakeRecord(FrozenModel):
    intake_id: UUID
    project_id: UUID
    created_at: datetime
    prompt: PromptText
    attachments: tuple[GenerationAttachmentRecord, ...] = ()
    authoritative_geometry: bool = False
    content_hash: str

    @model_validator(mode="after")
    def validate_record(self) -> GenerationIntakeRecord:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware.")
        if self.authoritative_geometry:
            raise ValueError("Generation intake references cannot be authoritative geometry.")
        if len(self.attachments) > 8:
            raise ValueError("A generation intake supports at most 8 attachments.")
        if self.content_hash != self.compute_content_hash():
            raise ValueError("content_hash does not match generation intake content.")
        return self

    def compute_content_hash(self) -> str:
        payload = {
            "project_id": str(self.project_id),
            "prompt": self.prompt,
            "attachments": [
                {
                    "attachment_id": str(item.attachment_id),
                    "kind": item.kind.value,
                    "original_filename": item.original_filename,
                    "media_type": item.media_type,
                    "size_bytes": item.size_bytes,
                    "sha256": item.sha256,
                    "storage_name": item.storage_name,
                }
                for item in self.attachments
            ],
            "authoritative_geometry": False,
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
