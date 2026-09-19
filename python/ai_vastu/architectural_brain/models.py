from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

BasisPoints = Annotated[int, Field(ge=0, le=10_000)]


class EvidenceStatus(StrEnum):
    EVALUATED = "EVALUATED"
    NOT_EVALUATED = "NOT_EVALUATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class LicenseClass(StrEnum):
    PRODUCTION_ALLOWED = "PRODUCTION_ALLOWED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    RESEARCH_ONLY = "RESEARCH_ONLY"


class PrecedentSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    name: str
    url: str
    license_id: str
    license_class: LicenseClass
    attribution_required: bool
    notes: str


class RoomFingerprint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    room_type: str
    area_mm2: int = Field(gt=0)
    width_mm: int | None = Field(default=None, gt=0)
    depth_mm: int | None = Field(default=None, gt=0)
    external_edge_count: int = Field(default=0, ge=0)
    door_count: int = Field(default=0, ge=0)
    window_count: int = Field(default=0, ge=0)


class TopologyEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_room_type: str
    target_room_type: str
    relation: Literal["DOOR", "ADJACENT", "NEAR", "AVOID", "ROAD_ACCESS"]
    weight: int = Field(default=50, ge=0, le=100)


class PrecedentFingerprint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    precedent_id: str
    source_id: str
    source_record_id: str
    license_id: str
    attribution: str
    width_mm: int = Field(gt=0)
    depth_mm: int = Field(gt=0)
    floor_area_mm2: int = Field(gt=0)
    bedroom_count: int = Field(ge=0)
    toilet_count: int = Field(ge=0)
    parking_count: int = Field(ge=0)
    room_types: tuple[str, ...]
    rooms: tuple[RoomFingerprint, ...]
    topology: tuple[TopologyEdge, ...]
    road_side: str | None = None
    entrance_side: str | None = None
    content_hash: str | None = None

    def canonical_bytes(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def compute_content_hash(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def with_content_hash(self) -> PrecedentFingerprint:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})


class RetrievedPrecedent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fingerprint: PrecedentFingerprint
    similarity_basis_points: BasisPoints
    reasons: tuple[str, ...]


class SpaceAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    category: Literal[
        "ROOM",
        "CIRCULATION",
        "WALL",
        "PARKING",
        "PORCH",
        "COURTYARD",
        "LIGHTWELL",
        "SHAFT",
        "SETBACK",
        "LANDSCAPE",
        "UTILITY_YARD",
        "VEHICLE_ACCESS",
        "OPEN_SPACE",
        "OTHER_PURPOSEFUL",
    ]
    label: str
    area_mm2: int = Field(ge=0)


class SiteAccounting(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    envelope_area_mm2: int = Field(gt=0)
    allocations: tuple[SpaceAllocation, ...]
    classified_area_mm2: int = Field(ge=0)
    residual_area_mm2: int = Field(ge=0)
    allocation_basis_points: BasisPoints

    @model_validator(mode="after")
    def validate_accounting(self) -> SiteAccounting:
        if sum(item.area_mm2 for item in self.allocations) != self.classified_area_mm2:
            raise ValueError("classified_area_mm2 must equal allocation sum.")
        if self.classified_area_mm2 + self.residual_area_mm2 != self.envelope_area_mm2:
            raise ValueError("Site accounting must exactly close.")
        return self


class ResidualRegion(BaseModel):
    """A geometrically measured, currently unclassified part of the site."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    area_mm2: int = Field(gt=0)
    centroid_x_mm: int
    centroid_y_mm: int
    min_x_mm: int
    min_y_mm: int
    max_x_mm: int
    max_y_mm: int


class SiteAccountingAnalysis(BaseModel):
    """Geometry-derived site accounting with auditable residual evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    accounting: SiteAccounting
    residual_regions: tuple[ResidualRegion, ...] = ()
    numerical_tolerance_mm2: int = Field(ge=0)
    unexplained_residual_area_mm2: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_residual(self) -> SiteAccountingAnalysis:
        expected = max(
            0,
            self.accounting.residual_area_mm2 - self.numerical_tolerance_mm2,
        )
        if self.unexplained_residual_area_mm2 != expected:
            raise ValueError(
                "unexplained_residual_area_mm2 must equal residual area "
                "after deterministic numerical tolerance."
            )
        return self


class ConceptRoom(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    room_type: str
    zone: Literal["PUBLIC", "SEMI_PRIVATE", "PRIVATE", "SERVICE", "SACRED", "VEHICLE"]
    target_area_mm2: int | None = Field(default=None, gt=0)
    target_width_mm: int | None = Field(default=None, gt=0)
    target_depth_mm: int | None = Field(default=None, gt=0)
    max_area_mm2: int | None = Field(default=None, gt=0)
    prefer_external_wall: bool = False
    notes: tuple[str, ...] = ()


class ArchitecturalConcept(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["26.4B.1"] = "26.4B.1"
    project_id: UUID
    concept_id: str
    title: str
    rooms: tuple[ConceptRoom, ...]
    topology: tuple[TopologyEdge, ...]
    precedent_ids: tuple[str, ...] = ()
    design_rationale: tuple[str, ...]
    authoritative_geometry: Literal[False] = False
    content_hash: str | None = None

    def canonical_bytes(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    def compute_content_hash(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def with_content_hash(self) -> ArchitecturalConcept:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})


class QualityMetric(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str
    label: str
    status: EvidenceStatus
    score_basis_points: BasisPoints | None = None
    weight: int = Field(default=1, ge=0)
    evidence: tuple[str, ...] = ()
    note: str | None = None


class ArchitecturalQualityScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    score_basis_points: BasisPoints | None
    evaluation_coverage_basis_points: BasisPoints
    evaluated_weight: int = Field(ge=0)
    unevaluated_weight: int = Field(ge=0)
    metrics: tuple[QualityMetric, ...]


class CritiqueSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    REJECT = "REJECT"


class CritiqueFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    severity: CritiqueSeverity
    message: str
    repair_hint: str | None = None


class ArchitecturalCritique(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted: bool
    findings: tuple[CritiqueFinding, ...]
    repair_round: int = Field(default=0, ge=0, le=3)


class RevisionOperation(StrEnum):
    INCREASE_DIMENSION = "INCREASE_DIMENSION"
    DECREASE_DIMENSION = "DECREASE_DIMENSION"
    SET_DIMENSION = "SET_DIMENSION"
    INCREASE_AREA = "INCREASE_AREA"
    DECREASE_AREA = "DECREASE_AREA"
    MOVE_TOWARD_SIDE = "MOVE_TOWARD_SIDE"
    PREFER_ADJACENCY = "PREFER_ADJACENCY"
    AVOID_ADJACENCY = "AVOID_ADJACENCY"
    ADD_ROOM = "ADD_ROOM"
    REMOVE_ROOM = "REMOVE_ROOM"
    PRESERVE = "PRESERVE"


class RevisionDirective(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: RevisionOperation
    room_type: str
    axis: Literal["WIDTH", "DEPTH"] | None = None
    delta_mm: int | None = None
    target_mm: int | None = None
    target_side: str | None = None
    related_room_type: str | None = None
    quantity: int | None = Field(default=None, ge=1)


class StructuredRevisionIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["26D.1"] = "26D.1"
    project_id: UUID
    base_revision_id: UUID
    original_request: str
    directives: tuple[RevisionDirective, ...]
    preserve_unmentioned_requirements: Literal[True] = True
    authoritative_geometry: Literal[False] = False
