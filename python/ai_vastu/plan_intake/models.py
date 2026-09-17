from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from ai_vastu.plan_schema.base import FrozenModel
from ai_vastu.requirements.models import Direction

PLAN_INTAKE_VERSION = "26B.5.1"
BasisPoints = Annotated[int, Field(ge=0, le=10_000)]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
PositiveMM = Annotated[int, Field(gt=0)]
PositiveMM2 = Annotated[int, Field(gt=0)]


class PlanReferenceKind(StrEnum):
    IMAGE = "IMAGE"
    PDF = "PDF"
    DXF = "DXF"
    DWG = "DWG"


class PlanObservationSource(StrEnum):
    IMAGE = "IMAGE"
    PDF = "PDF"
    DXF = "DXF"
    DWG = "DWG"
    CAD_EXTRACTION = "CAD_EXTRACTION"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    USER_CONFIRMED = "USER_CONFIRMED"


class PlanAuditStatus(StrEnum):
    SCORED = "SCORED"
    NEEDS_ORIENTATION = "NEEDS_ORIENTATION"
    NEEDS_ROOM_POSITIONS = "NEEDS_ROOM_POSITIONS"
    NO_EVALUABLE_RULES = "NO_EVALUABLE_RULES"


class PlanReferenceAsset(FrozenModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=160)
    kind: PlanReferenceKind
    data_sha256: str

    @model_validator(mode="after")
    def validate_hash(self) -> PlanReferenceAsset:
        if len(self.data_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.data_sha256
        ):
            raise ValueError("data_sha256 must be a lowercase SHA-256 digest.")
        return self


class PlanEnvelopeObservation(FrozenModel):
    geometry_type: Literal["RECTANGLE", "POLYGON", "UNKNOWN"] = "UNKNOWN"
    width_mm: PositiveMM | None = None
    depth_mm: PositiveMM | None = None
    built_up_area_mm2: PositiveMM2 | None = None
    confidence: Confidence = 0.0
    source: PlanObservationSource = PlanObservationSource.MODEL_INFERENCE
    requires_confirmation: bool = True
    evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_rectangle(self) -> PlanEnvelopeObservation:
        if self.geometry_type == "RECTANGLE" and (
            (self.width_mm is None) != (self.depth_mm is None)
        ):
            raise ValueError("Rectangle width and depth must be supplied together.")
        return self


class PlanOrientationObservation(FrozenModel):
    north_rotation_deg: Annotated[float, Field(ge=0.0, lt=360.0)] | None = None
    road_side: Direction | None = None
    entrance_facing: Direction | None = None
    confidence: Confidence = 0.0
    source: PlanObservationSource = PlanObservationSource.MODEL_INFERENCE
    requires_confirmation: bool = True
    evidence: tuple[str, ...] = ()


class PlanRoomObservation(FrozenModel):
    room_type: str = Field(min_length=1, max_length=80)
    label: str | None = Field(default=None, max_length=120)
    centroid_x_basis_points: BasisPoints | None = None
    centroid_y_basis_points: BasisPoints | None = None
    approximate_area_mm2: PositiveMM2 | None = None
    confidence: Confidence = 0.0
    source: PlanObservationSource = PlanObservationSource.MODEL_INFERENCE
    requires_confirmation: bool = True
    evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_centroid_pair(self) -> PlanRoomObservation:
        if (self.centroid_x_basis_points is None) != (self.centroid_y_basis_points is None):
            raise ValueError("Room centroid x/y must be supplied together.")
        return self


class PlanRecognitionDraft(FrozenModel):
    schema_version: Literal["26B.5.1"] = "26B.5.1"
    project_id: UUID
    intake_id: UUID
    provider: str = Field(min_length=1, max_length=80)
    model: str | None = Field(default=None, max_length=200)
    reference_names: tuple[str, ...]
    envelope: PlanEnvelopeObservation
    orientation: PlanOrientationObservation
    rooms: tuple[PlanRoomObservation, ...] = ()
    observations: tuple[str, ...] = ()
    questions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_content_hash(self) -> PlanRecognitionDraft:
        if self.content_hash is not None and self.content_hash != self.compute_content_hash():
            raise ValueError("content_hash does not match plan recognition draft.")
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

    def with_content_hash(self) -> PlanRecognitionDraft:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})


class PlanVastuRuleAudit(FrozenModel):
    rule_id: str
    title: str
    status: Literal[
        "PREFERRED",
        "SECONDARY",
        "NEUTRAL",
        "AVOIDED",
        "NOT_APPLICABLE",
        "NOT_EVALUATED",
    ]
    score_basis_points: BasisPoints | None = None
    effective_weight: int = Field(ge=0)
    evidence: tuple[str, ...] = ()
    suggestion: str


class PlanVastuAudit(FrozenModel):
    schema_version: Literal["26B.5.1"] = "26B.5.1"
    project_id: UUID
    intake_id: UUID
    status: PlanAuditStatus
    overall_basis_points: BasisPoints | None = None
    evaluation_coverage_basis_points: BasisPoints | None = None
    evaluated_weight: int = Field(default=0, ge=0)
    unevaluated_weight: int = Field(default=0, ge=0)
    provisional: Literal[True] = True
    rules: tuple[PlanVastuRuleAudit, ...] = ()
    suggestions: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_content_hash(self) -> PlanVastuAudit:
        if self.content_hash is not None and self.content_hash != self.compute_content_hash():
            raise ValueError("content_hash does not match plan Vastu audit.")
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

    def with_content_hash(self) -> PlanVastuAudit:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})


class AlternatePlanEnvelope(FrozenModel):
    geometry_type: Literal["RECTANGLE", "POLYGON", "UNKNOWN"]
    width_mm: PositiveMM | None = None
    depth_mm: PositiveMM | None = None
    exact_area_mm2: PositiveMM2 | None = None
    ready_for_exact_alternatives: bool = False
    requires_user_confirmation: bool = True
    reason: str


class PlanAnalysisResult(FrozenModel):
    schema_version: Literal["26B.5.1"] = "26B.5.1"
    project_id: UUID
    intake_id: UUID
    recognition: PlanRecognitionDraft
    vastu_audit: PlanVastuAudit
    alternate_plan_envelope: AlternatePlanEnvelope
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_identity_and_hash(self) -> PlanAnalysisResult:
        if self.recognition.project_id != self.project_id:
            raise ValueError("Recognition project identity mismatch.")
        if self.recognition.intake_id != self.intake_id:
            raise ValueError("Recognition intake identity mismatch.")
        if self.vastu_audit.project_id != self.project_id:
            raise ValueError("Vastu audit project identity mismatch.")
        if self.vastu_audit.intake_id != self.intake_id:
            raise ValueError("Vastu audit intake identity mismatch.")
        if self.content_hash is not None and self.content_hash != self.compute_content_hash():
            raise ValueError("content_hash does not match plan analysis.")
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

    def with_content_hash(self) -> PlanAnalysisResult:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})


class PlanGeometryConfirmationInput(FrozenModel):
    width_mm: PositiveMM
    depth_mm: PositiveMM
    north_rotation_deg: Annotated[float, Field(ge=0.0, lt=360.0)]
    road_side: Direction | None = None
    entrance_facing: Direction | None = None
    preserve_outer_envelope: Literal[True] = True

    @field_validator("road_side", "entrance_facing", mode="before")
    @classmethod
    def parse_direction(
        cls,
        value: object,
    ) -> object:
        if value is None or isinstance(value, Direction):
            return value
        if isinstance(value, str):
            try:
                return Direction(value.strip().upper())
            except ValueError as exc:
                raise ValueError("Direction must be one of N, NE, E, SE, S, SW, W, NW.") from exc
        return value


class PlanGeometryConfirmationRecord(FrozenModel):
    schema_version: Literal["26B.5.1"] = "26B.5.1"
    project_id: UUID
    intake_id: UUID
    width_mm: PositiveMM
    depth_mm: PositiveMM
    exact_area_mm2: PositiveMM2
    north_rotation_deg: Annotated[float, Field(ge=0.0, lt=360.0)]
    road_side: Direction | None = None
    entrance_facing: Direction | None = None
    preserve_outer_envelope: Literal[True] = True
    confirmed_by_user: Literal[True] = True
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_area_and_hash(self) -> PlanGeometryConfirmationRecord:
        if self.exact_area_mm2 != self.width_mm * self.depth_mm:
            raise ValueError("exact_area_mm2 must equal width_mm * depth_mm.")
        if self.content_hash is not None and self.content_hash != self.compute_content_hash():
            raise ValueError("content_hash does not match plan geometry confirmation.")
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

    def with_content_hash(self) -> PlanGeometryConfirmationRecord:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})
