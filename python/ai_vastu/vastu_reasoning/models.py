from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

VASTU_REASONING_VERSION = "26B.1"
BasisPoints = Annotated[int, Field(ge=0, le=10_000)]


class VastuInfluenceMode(StrEnum):
    PRACTICAL = "practical"
    BALANCED = "balanced"
    VASTU_FORWARD = "vastu_forward"


class RuleImportance(StrEnum):
    NEGLIGIBLE = "NEGLIGIBLE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CORE = "CORE"


class RuleFlexibility(StrEnum):
    FLEXIBLE = "FLEXIBLE"
    PREFERRED = "PREFERRED"
    STRONGLY_PREFERRED = "STRONGLY_PREFERRED"
    TRADITIONALLY_FIXED = "TRADITIONALLY_FIXED"


class RuleApplicability(StrEnum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CONTEXT_DEPENDENT = "CONTEXT_DEPENDENT"


class EvaluationKind(StrEnum):
    ROOM_CENTROID_SECTOR = "ROOM_CENTROID_SECTOR"
    UNSUPPORTED = "UNSUPPORTED"


class VastuRuleSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    title: str
    publisher: str
    url: str
    source_kind: str


class SoftVastuRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    version: str
    title: str
    subject_room_types: tuple[str, ...] = ()
    evaluation_kind: EvaluationKind
    preferred_sectors: tuple[str, ...] = ()
    secondary_sectors: tuple[str, ...] = ()
    avoid_sectors: tuple[str, ...] = ()
    base_weight: Annotated[int, Field(ge=0, le=100)]
    default_importance: RuleImportance
    default_flexibility: RuleFlexibility
    allowed_importance: tuple[RuleImportance, ...]
    allowed_flexibility: tuple[RuleFlexibility, ...]
    reasoning_adjustable: bool
    source_disagreement: bool
    source_ids: tuple[str, ...]
    suggestion: str
    hard_constraint: Literal[False] = False

    @model_validator(mode="after")
    def validate_policy(self) -> SoftVastuRule:
        if self.default_importance not in self.allowed_importance:
            raise ValueError("Default importance must be allowed.")
        if self.default_flexibility not in self.allowed_flexibility:
            raise ValueError("Default flexibility must be allowed.")
        if self.reasoning_adjustable is False:
            if self.allowed_importance != (self.default_importance,):
                raise ValueError("Non-adjustable rule must fix importance.")
            if self.allowed_flexibility != (self.default_flexibility,):
                raise ValueError("Non-adjustable rule must fix flexibility.")
        return self


class SoftVastuCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["26B.1"] = "26B.1"
    status: str
    hard_constraints_allowed: Literal[False] = False
    notes: tuple[str, ...] = ()
    sources: tuple[VastuRuleSource, ...]
    rules: tuple[SoftVastuRule, ...]

    @model_validator(mode="after")
    def validate_catalog(self) -> SoftVastuCatalog:
        source_ids = {item.source_id for item in self.sources}
        rule_ids = [item.rule_id for item in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Vastu rule IDs must be unique.")
        for rule in self.rules:
            unknown = set(rule.source_ids) - source_ids
            if unknown:
                raise ValueError(f"{rule.rule_id} references unknown source IDs: {sorted(unknown)}")
        return self


class VastuRuleReasoning(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    applicability: RuleApplicability
    importance: RuleImportance
    flexibility: RuleFlexibility
    weight_multiplier_basis_points: Annotated[int, Field(ge=0, le=15_000)] = 10_000
    rationale: str = Field(min_length=1, max_length=1000)


class VastuReasoningProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["26B.1"] = "26B.1"
    project_id: UUID
    draft_id: UUID
    provider: str
    model: str | None = None
    influence_mode: VastuInfluenceMode
    architecture_weight_basis_points: BasisPoints
    vastu_weight_basis_points: BasisPoints
    rules: tuple[VastuRuleReasoning, ...]
    notes: tuple[str, ...] = ()
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_weights(self) -> VastuReasoningProfile:
        if self.architecture_weight_basis_points + self.vastu_weight_basis_points != 10_000:
            raise ValueError("Architecture + Vastu weights must total 10000 basis points.")
        ids = [item.rule_id for item in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("Vastu reasoning profile contains duplicate rule IDs.")
        if self.content_hash is not None and self.content_hash != self.compute_content_hash():
            raise ValueError("content_hash does not match Vastu reasoning profile.")
        return self

    def canonical_content_bytes(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()

    def compute_content_hash(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def with_content_hash(self) -> VastuReasoningProfile:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})


class VastuRuleAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    title: str
    applicability: RuleApplicability
    importance: RuleImportance
    flexibility: RuleFlexibility
    score_basis_points: BasisPoints | None = None
    effective_weight: int = Field(ge=0)
    status: Literal[
        "PREFERRED",
        "SECONDARY",
        "NEUTRAL",
        "AVOIDED",
        "NOT_APPLICABLE",
        "NOT_EVALUATED",
    ]
    evidence: tuple[str, ...] = ()
    suggestion: str


class WeightedVastuAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["26B.1"] = "26B.1"
    project_id: UUID
    profile_hash: str
    overall_basis_points: BasisPoints | None
    rules: tuple[VastuRuleAssessment, ...]
    suggestions: tuple[str, ...] = ()
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_hash(self) -> WeightedVastuAssessment:
        if self.content_hash is not None and self.content_hash != self.compute_content_hash():
            raise ValueError("content_hash does not match weighted Vastu assessment.")
        return self

    def canonical_content_bytes(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()

    def compute_content_hash(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def with_content_hash(self) -> WeightedVastuAssessment:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})


class PlanningBlend(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    architecture_score_basis_points: BasisPoints
    vastu_score_basis_points: BasisPoints | None
    architecture_weight_basis_points: BasisPoints
    vastu_weight_basis_points: BasisPoints
    combined_basis_points: BasisPoints
    ranking_ready: bool
    note: str
