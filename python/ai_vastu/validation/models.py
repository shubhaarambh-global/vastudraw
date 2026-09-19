from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import model_validator

from ai_vastu.architectural_geometry import ArchitecturalGeometryResult
from ai_vastu.constraints import CompiledConstraintProblem
from ai_vastu.plan_schema import IntPolygon, NonNegativeMM, PositiveMM2, ValidationReport
from ai_vastu.plan_schema.base import FrozenModel
from ai_vastu.plan_schema.models import EntityId

VALIDATOR_VERSION = "1.0.0"
_HASH_LENGTH = 64


class SwingSpace(StrEnum):
    ROOM = "ROOM"
    EXTERIOR = "EXTERIOR"


class ValidationConfig(FrozenModel):
    tiny_sliver_area_mm2: PositiveMM2
    door_clearance_margin_mm: NonNegativeMM
    require_exterior_access: bool = True


class DoorSwingContext(FrozenModel):
    opening_id: EntityId
    swing_space: SwingSpace
    room_id: EntityId | None = None

    @model_validator(mode="after")
    def validate_room_reference_shape(self) -> DoorSwingContext:
        if self.swing_space is SwingSpace.ROOM and self.room_id is None:
            raise ValueError("ROOM swing context requires room_id.")
        if self.swing_space is SwingSpace.EXTERIOR and self.room_id is not None:
            raise ValueError("EXTERIOR swing context cannot include room_id.")
        return self


class ArchitecturalValidationRequest(FrozenModel):
    plot_boundary: IntPolygon
    problem: CompiledConstraintProblem
    geometry: ArchitecturalGeometryResult
    config: ValidationConfig
    swing_contexts: tuple[DoorSwingContext, ...] = ()
    circulation_anchor_room_ids: tuple[EntityId, ...] = ()


class ValidationRunResult(FrozenModel):
    validator_version: Literal["1.0.0"] = "1.0.0"
    source_problem_hash: str
    source_geometry_hash: str
    report: ValidationReport
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_hashes(self) -> ValidationRunResult:
        for name, value in (
            ("source_problem_hash", self.source_problem_hash),
            ("source_geometry_hash", self.source_geometry_hash),
        ):
            if len(value) != _HASH_LENGTH or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"{name} must be lowercase SHA-256 hex.")
        if self.content_hash is not None:
            if len(self.content_hash) != _HASH_LENGTH or any(
                c not in "0123456789abcdef" for c in self.content_hash
            ):
                raise ValueError("content_hash must be lowercase SHA-256 hex.")
            if self.content_hash != self.compute_content_hash():
                raise ValueError("content_hash does not match validation result content.")
        return self

    def canonical_content_bytes(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def compute_content_hash(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def with_content_hash(self) -> ValidationRunResult:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})
