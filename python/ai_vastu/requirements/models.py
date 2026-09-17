from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceSource(StrEnum):
    PROMPT = "prompt"
    IMAGE = "image"
    PDF = "pdf"
    MODEL_INFERENCE = "model_inference"
    USER_CONFIRMED = "user_confirmed"


class Direction(StrEnum):
    N = "N"
    NE = "NE"
    E = "E"
    SE = "SE"
    S = "S"
    SW = "SW"
    W = "W"
    NW = "NW"


class VastuMode(StrEnum):
    STRICT = "strict"
    BALANCED = "balanced"
    SPACE_EFFICIENT = "space_efficient"
    CUSTOM = "custom"


class ProposedInt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int
    source: EvidenceSource
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    requires_confirmation: bool = True


class ProposedFloat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float
    source: EvidenceSource
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    requires_confirmation: bool = True


class ProposedDirection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Direction
    source: EvidenceSource
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    requires_confirmation: bool = True


class RoomRequirementDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_type: str = Field(min_length=1, max_length=80)
    quantity: int = Field(default=1, ge=1, le=20)
    floor_preference: int | None = Field(default=None, ge=0, le=10)
    notes: str | None = Field(default=None, max_length=500)
    source: EvidenceSource = EvidenceSource.MODEL_INFERENCE
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.7


class RequirementDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["24A.1"] = "24A.1"
    draft_id: UUID
    user_id: UUID
    project_id: UUID
    prompt: str = Field(min_length=1, max_length=20_000)

    plot_width_mm: ProposedInt | None = None
    plot_depth_mm: ProposedInt | None = None
    north_rotation_deg: ProposedFloat | None = None
    road_side: ProposedDirection | None = None
    entrance_facing: ProposedDirection | None = None
    floor_count: ProposedInt | None = None
    bedroom_count: ProposedInt | None = None
    parking_count: ProposedInt | None = None

    vastu_mode: VastuMode = VastuMode.BALANCED
    rooms: list[RoomRequirementDraft] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reference_names: list[str] = Field(default_factory=list)
    provider: str
    model: str | None = None

    @property
    def ready_for_confirmation(self) -> bool:
        required = (
            self.plot_width_mm,
            self.plot_depth_mm,
            self.north_rotation_deg,
            self.road_side,
            self.floor_count,
        )
        return all(item is not None for item in required)


class ConfirmedRoomRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_type: str = Field(min_length=1, max_length=80)
    quantity: int = Field(default=1, ge=1, le=20)
    floor_preference: int | None = Field(default=None, ge=0, le=10)
    notes: str | None = Field(default=None, max_length=500)


class ConfirmedRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["24A.1"] = "24A.1"
    draft_id: UUID
    user_id: UUID
    project_id: UUID
    user_confirmed: Literal[True]

    plot_width_mm: int = Field(gt=0, le=1_000_000)
    plot_depth_mm: int = Field(gt=0, le=1_000_000)
    north_rotation_deg: float = Field(ge=0.0, lt=360.0)
    road_side: Direction
    entrance_facing: Direction | None = None
    floor_count: int = Field(ge=1, le=10)
    bedroom_count: int = Field(ge=0, le=20)
    parking_count: int = Field(default=0, ge=0, le=20)
    vastu_mode: VastuMode = VastuMode.BALANCED
    rooms: list[ConfirmedRoomRequirement] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_room_counts(self) -> ConfirmedRequirements:
        room_bedrooms = sum(
            item.quantity
            for item in self.rooms
            if item.room_type.strip().lower() in {"bedroom", "master_bedroom"}
        )
        if room_bedrooms > self.bedroom_count:
            raise ValueError("Explicit bedroom room requirements exceed bedroom_count.")
        return self
