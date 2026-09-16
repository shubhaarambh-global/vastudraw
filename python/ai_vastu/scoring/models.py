from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ai_vastu.architectural_geometry.models import ArchitecturalGeometryResult
from ai_vastu.constraints.models import CompiledConstraintProblem
from ai_vastu.plan_schema import BasisPoints, PositiveMM, ScoringSummary
from ai_vastu.plan_schema.base import FrozenModel
from ai_vastu.plan_schema.models import EntityId
from ai_vastu.solver.models import PlannerResult
from ai_vastu.validation.models import ValidationRunResult

SCORING_VERSION = "1.0.0"
_HASH_LENGTH = 64
PositiveInt20 = Annotated[int, Field(gt=0, le=20)]
PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeInt = Annotated[int, Field(ge=0)]


class ScoringNoticeSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"


class ScoringConfig(FrozenModel):
    max_alternatives: PositiveInt20
    room_change_threshold_mm: PositiveMM
    minimum_changed_rooms: PositiveInt
    reject_validation_warnings: bool


class ScoringCandidate(FrozenModel):
    candidate_id: EntityId
    planner_result: PlannerResult
    geometry_result: ArchitecturalGeometryResult
    validation_result: ValidationRunResult


class ObjectiveScore(FrozenModel):
    constraint_id: EntityId
    kind: str
    score_basis_points: BasisPoints
    weight: NonNegativeInt
    evidence: tuple[str, ...] = ()


class ScoringNotice(FrozenModel):
    code: str
    severity: ScoringNoticeSeverity
    message: str
    constraint_id: EntityId | None = None
    candidate_id: EntityId | None = None


class CandidateScore(FrozenModel):
    candidate_id: EntityId
    overall_basis_points: BasisPoints
    scoring_summary: ScoringSummary
    planner_objective_penalty: NonNegativeInt
    objective_scores: tuple[ObjectiveScore, ...]
    notices: tuple[ScoringNotice, ...] = ()
    placement_signature: str
    source_planner_hash: str
    source_geometry_hash: str
    source_validation_hash: str
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_hashes(self) -> CandidateScore:
        for name, value in (
            ("placement_signature", self.placement_signature),
            ("source_planner_hash", self.source_planner_hash),
            ("source_geometry_hash", self.source_geometry_hash),
            ("source_validation_hash", self.source_validation_hash),
        ):
            if len(value) != _HASH_LENGTH or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"{name} must be lowercase SHA-256 hex.")
        if self.content_hash is not None:
            if len(self.content_hash) != _HASH_LENGTH or any(
                c not in "0123456789abcdef" for c in self.content_hash
            ):
                raise ValueError("content_hash must be lowercase SHA-256 hex.")
            if self.content_hash != self.compute_content_hash():
                raise ValueError("content_hash does not match candidate score content.")
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

    def with_content_hash(self) -> CandidateScore:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})


class RankedAlternative(FrozenModel):
    rank: PositiveInt
    candidate: CandidateScore
    minimum_changed_rooms_vs_selected: NonNegativeInt | None = None


class ExcludedAlternative(FrozenModel):
    candidate_id: EntityId
    reason_code: str
    message: str


class ScoringRequest(FrozenModel):
    problem: CompiledConstraintProblem
    config: ScoringConfig
    candidates: tuple[ScoringCandidate, ...]

    @model_validator(mode="after")
    def validate_candidate_identity(self) -> ScoringRequest:
        if not self.candidates:
            raise ValueError("At least one scoring candidate is required.")
        ids = [item.candidate_id for item in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate_id values must be unique.")
        return self


class ScoringRunResult(FrozenModel):
    scoring_version: Literal["1.0.0"] = "1.0.0"
    source_problem_hash: str
    selected: tuple[RankedAlternative, ...]
    excluded: tuple[ExcludedAlternative, ...] = ()
    notices: tuple[ScoringNotice, ...] = ()
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_hashes(self) -> ScoringRunResult:
        if len(self.source_problem_hash) != _HASH_LENGTH or any(
            c not in "0123456789abcdef" for c in self.source_problem_hash
        ):
            raise ValueError("source_problem_hash must be lowercase SHA-256 hex.")
        if self.content_hash is not None:
            if len(self.content_hash) != _HASH_LENGTH or any(
                c not in "0123456789abcdef" for c in self.content_hash
            ):
                raise ValueError("content_hash must be lowercase SHA-256 hex.")
            if self.content_hash != self.compute_content_hash():
                raise ValueError("content_hash does not match scoring result content.")
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

    def with_content_hash(self) -> ScoringRunResult:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})
