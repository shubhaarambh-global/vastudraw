from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

PHASE26C_VERSION = "26C.1"
BasisPoints = Annotated[int, Field(ge=0, le=10_000)]


class CandidatePlanningMode(StrEnum):
    PRACTICAL = "practical"
    BALANCED = "balanced"
    VASTU_FORWARD = "vastu_forward"


class CandidateStrategyKind(StrEnum):
    COMPACT = "compact"
    PRIVACY = "privacy"
    DAYLIGHT = "daylight"
    CIRCULATION = "circulation"
    VASTU_AWARE = "vastu_aware"
    ALTERNATE_TOPOLOGY = "alternate_topology"


class CandidateStrategy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_id: str = Field(min_length=1, max_length=80)
    kind: CandidateStrategyKind
    label: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    deterministic_ordinal: int = Field(ge=0, le=50)


class CandidateExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strengths: tuple[str, ...] = ()
    compromises: tuple[str, ...] = ()
    selection_reason: str = Field(min_length=1, max_length=1_000)


class CandidateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    rank: int = Field(ge=1)
    strategy: CandidateStrategy
    valid_architecture: bool
    architecture_score_basis_points: BasisPoints
    vastu_score_basis_points: BasisPoints | None = None
    vastu_evaluation_coverage_basis_points: BasisPoints | None = None
    combined_score_basis_points: BasisPoints
    architecture_weight_basis_points: BasisPoints
    vastu_weight_basis_points: BasisPoints
    plan_document_hash: str | None = None
    explanation: CandidateExplanation

    @model_validator(mode="after")
    def validate_weights(self) -> CandidateResult:
        if self.architecture_weight_basis_points + self.vastu_weight_basis_points != 10_000:
            raise ValueError("Architecture and Vastu weights must sum to 10,000 basis points.")
        if not self.valid_architecture:
            raise ValueError("Invalid architectural candidates cannot enter the ranked result set.")
        return self


class CandidateRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["26C.1"] = "26C.1"
    project_id: UUID
    planning_mode: CandidatePlanningMode
    candidates: tuple[CandidateResult, ...]
    rejected_candidate_count: int = Field(default=0, ge=0)
    structural_design_included: Literal[False] = False
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_result(self) -> CandidateRunResult:
        if not self.candidates:
            raise ValueError("Phase 26C candidate runs require at least one valid candidate.")
        ranks = [item.rank for item in self.candidates]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("Candidate ranks must be contiguous starting at 1.")
        if self.content_hash is not None and self.content_hash != self.compute_content_hash():
            raise ValueError("content_hash does not match candidate run content.")
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

    def with_content_hash(self) -> CandidateRunResult:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})
