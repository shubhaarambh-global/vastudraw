from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .base import FrozenModel
from .geometry import AxisSegment, IntPoint, IntPolygon
from .units import (
    MM,
    BasisPoints,
    LengthUnit,
    MicroDegrees,
    NonNegativeMM,
    PositiveMM,
    PositiveMM2,
    Priority100,
)

PLAN_SCHEMA_VERSION = "1.0.0"
CanonicalUnits = Literal["mm"]
EntityId = UUID
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class PlotGeometryType(StrEnum):
    RECTANGLE = "RECTANGLE"
    POLYGON = "POLYGON"


class PlotInputSource(StrEnum):
    MANUAL = "MANUAL"
    INTERACTIVE = "INTERACTIVE"
    SURVEY = "SURVEY"
    DOCUMENT_EXTRACTION = "DOCUMENT_EXTRACTION"
    IMPORT = "IMPORT"


class VerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    USER_VERIFIED = "USER_VERIFIED"
    SURVEY_VERIFIED = "SURVEY_VERIFIED"


class OrientationSource(StrEnum):
    USER = "USER"
    SURVEY = "SURVEY"
    DOCUMENT_EXTRACTION = "DOCUMENT_EXTRACTION"
    IMPORT = "IMPORT"


class WallCategory(StrEnum):
    EXTERNAL = "EXTERNAL"
    INTERNAL = "INTERNAL"
    SHAFT = "SHAFT"
    PARAPET = "PARAPET"


class OpeningKind(StrEnum):
    DOOR = "DOOR"
    WINDOW = "WINDOW"
    OPENING = "OPENING"


class DoorHinge(StrEnum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class DoorSwing(StrEnum):
    IN = "IN"
    OUT = "OUT"
    SLIDING = "SLIDING"
    NONE = "NONE"


class StairType(StrEnum):
    STRAIGHT = "STRAIGHT"
    L_SHAPED = "L_SHAPED"
    U_SHAPED = "U_SHAPED"
    DOG_LEGGED = "DOG_LEGGED"
    SPIRAL = "SPIRAL"
    OTHER = "OTHER"


class RoomType(StrEnum):
    LIVING = "living"
    DRAWING = "drawing"
    DINING = "dining"
    KITCHEN = "kitchen"
    UTILITY = "utility"
    PANTRY = "pantry"
    STORE = "store"
    PUJA = "puja"
    MASTER_BEDROOM = "master_bedroom"
    BEDROOM = "bedroom"
    PARENTS_BEDROOM = "parents_bedroom"
    GUEST_BEDROOM = "guest_bedroom"
    CHILDREN_BEDROOM = "children_bedroom"
    ATTACHED_TOILET = "attached_toilet"
    COMMON_TOILET = "common_toilet"
    POWDER_ROOM = "powder_room"
    BATH = "bath"
    DRESSING = "dressing"
    WARDROBE = "wardrobe"
    STAIRCASE = "staircase"
    LIFT = "lift"
    LOBBY = "lobby"
    CORRIDOR = "corridor"
    FOYER = "foyer"
    VERANDAH = "verandah"
    BALCONY = "balcony"
    TERRACE = "terrace"
    COURTYARD = "courtyard"
    PARKING = "parking"
    GARAGE = "garage"
    HOME_OFFICE = "home_office"
    SERVANT_ROOM = "servant_room"
    SERVANT_TOILET = "servant_toilet"
    LAUNDRY = "laundry"
    STUDY = "study"
    FAMILY_LOUNGE = "family_lounge"


class VastuStatus(StrEnum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    COMPROMISE = "COMPROMISE"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ValidationSeverity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class AssumptionSource(StrEnum):
    USER = "USER"
    DOCUMENTED_DEFAULT = "DOCUMENTED_DEFAULT"
    AI_SUGGESTED = "AI_SUGGESTED"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"


class DeclaredMeasurement(FrozenModel):
    label: str
    input_value: str
    input_unit: LengthUnit
    exact_mm_decimal: str
    quantized_mm: NonNegativeMM
    rounding_delta_mm_decimal: str


class ClosureReport(FrozenModel):
    closure_error_mm: NonNegativeMM
    tolerance_mm: NonNegativeMM
    accepted: bool


class Plot(FrozenModel):
    id: EntityId
    geometry_type: PlotGeometryType
    boundary: IntPolygon
    edge_ids: tuple[EntityId, ...]
    input_source: PlotInputSource
    verification_status: VerificationStatus
    declared_measurements: tuple[DeclaredMeasurement, ...] = ()
    closure_report: ClosureReport | None = None

    @model_validator(mode="after")
    def validate_edge_ids(self) -> Plot:
        if len(self.edge_ids) != len(self.boundary.outer):
            raise ValueError("Plot edge_ids must contain exactly one ID per outer boundary edge.")
        if len(set(self.edge_ids)) != len(self.edge_ids):
            raise ValueError("Plot edge_ids must be unique.")
        return self


class Orientation(FrozenModel):
    north_rotation_udeg: MicroDegrees
    source: OrientationSource
    verified: bool


class Road(FrozenModel):
    id: EntityId
    name: str | None = None
    plot_edge_ids: tuple[EntityId, ...]
    width_mm: PositiveMM | None = None
    primary_access: bool = False


class Setback(FrozenModel):
    id: EntityId
    boundary_edge_id: EntityId
    distance_mm: NonNegativeMM
    source_ref: str | None = None
    regulation_rule_id: str | None = None


class BuildableArea(FrozenModel):
    polygon: IntPolygon
    setbacks: tuple[Setback, ...] = ()


class AspectRatioRange(FrozenModel):
    min_ratio_milli: PositiveInt
    max_ratio_milli: PositiveInt

    @model_validator(mode="after")
    def validate_order(self) -> AspectRatioRange:
        if self.min_ratio_milli > self.max_ratio_milli:
            raise ValueError("min_ratio_milli cannot exceed max_ratio_milli.")
        return self


class AdjacencyPreference(FrozenModel):
    target_room_type: RoomType
    weight: Priority100
    max_gap_mm: NonNegativeMM | None = None
    min_shared_length_mm: NonNegativeMM | None = None


class AdjacencyProhibition(FrozenModel):
    target_room_type: RoomType
    hard: bool = True


class RoomRequirement(FrozenModel):
    id: EntityId
    room_type: RoomType
    quantity: PositiveInt = 1
    floor_preference: tuple[NonNegativeInt, ...] = ()
    min_width_mm: PositiveMM
    preferred_width_mm: PositiveMM | None = None
    max_width_mm: PositiveMM | None = None
    min_depth_mm: PositiveMM
    preferred_depth_mm: PositiveMM | None = None
    max_depth_mm: PositiveMM | None = None
    min_area_mm2: PositiveMM2
    preferred_area_mm2: PositiveMM2 | None = None
    max_area_mm2: PositiveMM2 | None = None
    aspect_ratio: AspectRatioRange | None = None
    adjacency_preferences: tuple[AdjacencyPreference, ...] = ()
    adjacency_prohibitions: tuple[AdjacencyProhibition, ...] = ()
    privacy_priority: Priority100 = 50
    daylight_priority: Priority100 = 50
    ventilation_priority: Priority100 = 50
    user_priority: Priority100 = 50
    vastu_profile_refs: tuple[str, ...] = ()
    locked: bool = False

    @model_validator(mode="after")
    def validate_ranges(self) -> RoomRequirement:
        _check_optional_range(
            "width", self.min_width_mm, self.preferred_width_mm, self.max_width_mm
        )
        _check_optional_range(
            "depth", self.min_depth_mm, self.preferred_depth_mm, self.max_depth_mm
        )
        _check_optional_range("area", self.min_area_mm2, self.preferred_area_mm2, self.max_area_mm2)
        return self


def _check_optional_range(
    name: str, minimum: int, preferred: int | None, maximum: int | None
) -> None:
    if preferred is not None and preferred < minimum:
        raise ValueError(f"preferred {name} cannot be below minimum {name}.")
    if maximum is not None and maximum < minimum:
        raise ValueError(f"maximum {name} cannot be below minimum {name}.")
    if preferred is not None and maximum is not None and preferred > maximum:
        raise ValueError(f"preferred {name} cannot exceed maximum {name}.")


class RoomGeometry(FrozenModel):
    id: EntityId
    requirement_id: EntityId | None = None
    room_type: RoomType
    name: str | None = None
    polygon: IntPolygon
    locked: bool = False


class Wall(FrozenModel):
    id: EntityId
    axis: AxisSegment
    thickness_mm: PositiveMM
    height_mm: PositiveMM
    category: WallCategory
    construction_type: str | None = None


class Opening(FrozenModel):
    id: EntityId
    wall_id: EntityId
    kind: OpeningKind
    offset_from_wall_start_mm: NonNegativeMM
    width_mm: PositiveMM
    height_mm: PositiveMM
    sill_height_mm: NonNegativeMM | None = None
    hinge: DoorHinge | None = None
    swing: DoorSwing | None = None


class Stair(FrozenModel):
    id: EntityId
    stair_type: StairType
    footprint: IntPolygon
    width_mm: PositiveMM
    riser_mm: PositiveMM
    tread_mm: PositiveMM
    number_of_risers: PositiveInt
    floor_height_mm: PositiveMM
    landing_depth_mm: NonNegativeMM
    direction_udeg: MicroDegrees
    headroom_mm: PositiveMM | None = None


class Fixture(FrozenModel):
    id: EntityId
    fixture_type: str
    anchor: IntPoint | None = None
    footprint: IntPolygon | None = None
    rotation_udeg: MicroDegrees = 0

    @model_validator(mode="after")
    def require_location(self) -> Fixture:
        if self.anchor is None and self.footprint is None:
            raise ValueError("Fixture requires an anchor or footprint.")
        return self


class Furniture(FrozenModel):
    id: EntityId
    furniture_type: str
    footprint: IntPolygon
    rotation_udeg: MicroDegrees = 0


class Dimension(FrozenModel):
    id: EntityId
    start: IntPoint
    end: IntPoint
    offset_mm: NonNegativeMM = 0
    label_override: str | None = None


class Annotation(FrozenModel):
    id: EntityId
    anchor: IntPoint
    text: str
    category: str


class Floor(FrozenModel):
    id: EntityId
    index: NonNegativeInt
    name: str
    elevation_mm: MM
    floor_to_floor_mm: PositiveMM
    boundary: IntPolygon | None = None
    rooms: tuple[RoomGeometry, ...] = ()
    walls: tuple[Wall, ...] = ()
    openings: tuple[Opening, ...] = ()
    stairs: tuple[Stair, ...] = ()
    fixtures: tuple[Fixture, ...] = ()
    furniture: tuple[Furniture, ...] = ()
    dimensions: tuple[Dimension, ...] = ()
    annotations: tuple[Annotation, ...] = ()


class EvidenceItem(FrozenModel):
    key: str
    value: str


class VastuResult(FrozenModel):
    rule_id: str
    rule_version: str
    entity_refs: tuple[EntityId, ...] = ()
    status: VastuStatus
    measured_evidence: tuple[EvidenceItem, ...] = ()
    geometry_evidence: tuple[EvidenceItem, ...] = ()
    raw_weight: NonNegativeInt = 0
    earned_weight: NonNegativeInt = 0

    @model_validator(mode="after")
    def validate_weight(self) -> VastuResult:
        if self.earned_weight > self.raw_weight:
            raise ValueError("earned_weight cannot exceed raw_weight.")
        return self


class VastuAnalysis(FrozenModel):
    spec_version: str
    results: tuple[VastuResult, ...] = ()
    overall_basis_points: BasisPoints | None = None
    major_violations: NonNegativeInt = 0
    minor_compromises: NonNegativeInt = 0


class ValidationResult(FrozenModel):
    check_id: str
    severity: ValidationSeverity
    entity_refs: tuple[EntityId, ...] = ()
    message_code: str
    evidence: tuple[EvidenceItem, ...] = ()
    validator_version: str


class ValidationReport(FrozenModel):
    valid: bool
    errors: tuple[ValidationResult, ...] = ()
    warnings: tuple[ValidationResult, ...] = ()
    informational: tuple[ValidationResult, ...] = ()

    @model_validator(mode="after")
    def validate_error_consistency(self) -> ValidationReport:
        if self.valid and self.errors:
            raise ValueError("A valid report cannot contain errors.")
        if not self.valid and not self.errors:
            raise ValueError("An invalid report must contain at least one error.")
        return self


class ScoreComponent(FrozenModel):
    key: str
    score_basis_points: BasisPoints
    weight_basis_points: BasisPoints


class ScoringSummary(FrozenModel):
    mode: str
    overall_basis_points: BasisPoints
    components: tuple[ScoreComponent, ...] = ()


class Assumption(FrozenModel):
    id: EntityId
    code: str
    description: str
    source: AssumptionSource
    confirmed_by_user: bool
    affected_entity_ids: tuple[EntityId, ...] = ()


class MetadataItem(FrozenModel):
    key: str
    value: str


class GenerationMetadata(FrozenModel):
    solver_name: str | None = None
    solver_version: str | None = None
    solver_parameters: tuple[MetadataItem, ...] = ()
    solver_step_mm: PositiveMM | None = None
    seed: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    rule_bundle_hash: str | None = None
    input_hash: str | None = None

    @model_validator(mode="after")
    def validate_timestamps(self) -> GenerationMetadata:
        for value in (self.started_at, self.completed_at):
            if value is not None and value.tzinfo is None:
                raise ValueError("Generation timestamps must be timezone-aware.")
        if self.started_at and self.completed_at and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at.")
        return self


class PlanDocument(FrozenModel):
    schema_version: Literal["1.0.0"]
    project_id: EntityId
    revision_id: EntityId
    canonical_units: CanonicalUnits
    plot: Plot
    orientation: Orientation
    roads: tuple[Road, ...] = ()
    buildable_area: BuildableArea
    room_requirements: tuple[RoomRequirement, ...] = ()
    floors: tuple[Floor, ...]
    vastu_spec_version: str
    regulation_spec_version: str | None = None
    vastu_analysis: VastuAnalysis
    validation: ValidationReport
    scoring: ScoringSummary
    assumptions: tuple[Assumption, ...] = ()
    generation_metadata: GenerationMetadata
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_document_integrity(self) -> PlanDocument:
        floor_ids = [floor.id for floor in self.floors]
        if len(set(floor_ids)) != len(floor_ids):
            raise ValueError("Floor IDs must be unique.")
        floor_indices = [floor.index for floor in self.floors]
        if len(set(floor_indices)) != len(floor_indices):
            raise ValueError("Floor indexes must be unique.")

        plot_edge_ids = set(self.plot.edge_ids)
        for road in self.roads:
            if not set(road.plot_edge_ids).issubset(plot_edge_ids):
                raise ValueError("Road references an unknown plot edge ID.")
        for setback in self.buildable_area.setbacks:
            if setback.boundary_edge_id not in plot_edge_ids:
                raise ValueError("Setback references an unknown plot edge ID.")

        requirement_ids = {requirement.id for requirement in self.room_requirements}
        if len(requirement_ids) != len(self.room_requirements):
            raise ValueError("RoomRequirement IDs must be unique.")
        for floor in self.floors:
            wall_ids = {wall.id for wall in floor.walls}
            if len(wall_ids) != len(floor.walls):
                raise ValueError("Wall IDs must be unique within a floor.")
            for opening in floor.openings:
                if opening.wall_id not in wall_ids:
                    raise ValueError("Opening references an unknown wall ID on its floor.")
            for room in floor.rooms:
                if room.requirement_id is not None and room.requirement_id not in requirement_ids:
                    raise ValueError("RoomGeometry references an unknown RoomRequirement ID.")

        if self.content_hash is not None:
            if not _HASH_RE.fullmatch(self.content_hash):
                raise ValueError("content_hash must be a lowercase SHA-256 hex digest.")
            if self.content_hash != self.compute_content_hash():
                raise ValueError("content_hash does not match canonical document content.")
        return self

    def canonical_content_bytes(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return text.encode("utf-8")

    def compute_content_hash(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def with_content_hash(self) -> PlanDocument:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})

    def to_canonical_json(self, *, include_hash: bool = True) -> str:
        document = self.with_content_hash() if include_hash else self
        payload = document.model_dump(
            mode="json",
            exclude=None if include_hash else {"content_hash"},
        )
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class SolverObjective(FrozenModel):
    key: str
    value: str


class PlanCandidate(FrozenModel):
    candidate_id: EntityId
    document: PlanDocument
    solver_objectives: tuple[SolverObjective, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    diversity_signature: tuple[str, ...] = ()
