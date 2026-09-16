from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ai_vastu.plan_schema.base import FrozenModel
from ai_vastu.plan_schema.models import VastuStatus

_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_RULE_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,127}$")
_SOURCE_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

RuleWeight = Annotated[int, Field(ge=0, le=10_000)]
Precedence = Annotated[int, Field(ge=0, le=1_000_000)]
BasisPoints = Annotated[int, Field(ge=0, le=10_000)]


class RuleLifecycle(StrEnum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    FROZEN = "FROZEN"
    RETIRED = "RETIRED"


class RuleClassification(StrEnum):
    HARD = "HARD"
    SOFT = "SOFT"


class RuleSeverity(StrEnum):
    INFO = "INFO"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"


class GeometrySemantic(StrEnum):
    CENTROID_IN_ZONE = "CENTROID_IN_ZONE"
    AREA_OVERLAP_PERCENT = "AREA_OVERLAP_PERCENT"
    POINT_IN_ZONE = "POINT_IN_ZONE"
    BOUNDARY_INTERSECTION = "BOUNDARY_INTERSECTION"
    DIRECTION_VECTOR = "DIRECTION_VECTOR"
    ENTRANCE_POINT_DIRECTION = "ENTRANCE_POINT_DIRECTION"
    FIXTURE_POINT_ZONE = "FIXTURE_POINT_ZONE"
    ROOM_ORIENTATION = "ROOM_ORIENTATION"
    DISTANCE_TO_BRAHMASTHAN = "DISTANCE_TO_BRAHMASTHAN"


class PredicateKind(StrEnum):
    NUMERIC_RANGE = "NUMERIC_RANGE"
    ENUM_SET = "ENUM_SET"
    BOOLEAN = "BOOLEAN"


class SourceReference(FrozenModel):
    source_id: str
    locator: str
    interpretation_note: str | None = None

    @model_validator(mode="after")
    def validate_source_id(self) -> SourceReference:
        if not _SOURCE_ID_RE.fullmatch(self.source_id):
            raise ValueError("source_id must use stable uppercase identifier syntax.")
        if not self.locator.strip():
            raise ValueError("Source locator must not be blank.")
        return self


class SourceRecord(FrozenModel):
    source_id: str
    title: str
    author_or_institution: str | None = None
    edition: str | None = None
    publication_date: str | None = None
    uri: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> SourceRecord:
        if not _SOURCE_ID_RE.fullmatch(self.source_id):
            raise ValueError("source_id must use stable uppercase identifier syntax.")
        if not self.title.strip():
            raise ValueError("Source title must not be blank.")
        return self


class SubjectAttribute(FrozenModel):
    key: str
    value: str

    @model_validator(mode="after")
    def reject_blank(self) -> SubjectAttribute:
        if not self.key.strip() or not self.value.strip():
            raise ValueError("Subject attributes require non-blank key and value.")
        return self


class SubjectSelector(FrozenModel):
    entity_type: str
    attributes: tuple[SubjectAttribute, ...] = ()

    @model_validator(mode="after")
    def validate_subject(self) -> SubjectSelector:
        if not self.entity_type.strip():
            raise ValueError("entity_type must not be blank.")
        keys = [item.key for item in self.attributes]
        if len(keys) != len(set(keys)):
            raise ValueError("Subject attribute keys must be unique.")
        return self

    def canonical_key(self) -> tuple[str, tuple[tuple[str, str], ...]]:
        return (
            self.entity_type,
            tuple(sorted((item.key, item.value) for item in self.attributes)),
        )


class NumericRangePredicate(FrozenModel):
    kind: Literal[PredicateKind.NUMERIC_RANGE] = PredicateKind.NUMERIC_RANGE
    metric_key: str
    minimum_inclusive: int | None = None
    maximum_inclusive: int | None = None

    @model_validator(mode="after")
    def validate_range(self) -> NumericRangePredicate:
        if not self.metric_key.strip():
            raise ValueError("metric_key must not be blank.")
        if self.minimum_inclusive is None and self.maximum_inclusive is None:
            raise ValueError("Numeric range requires at least one bound.")
        if (
            self.minimum_inclusive is not None
            and self.maximum_inclusive is not None
            and self.minimum_inclusive > self.maximum_inclusive
        ):
            raise ValueError("Numeric predicate minimum cannot exceed maximum.")
        return self


class EnumSetPredicate(FrozenModel):
    kind: Literal[PredicateKind.ENUM_SET] = PredicateKind.ENUM_SET
    metric_key: str
    allowed_values: tuple[str, ...]

    @model_validator(mode="after")
    def validate_values(self) -> EnumSetPredicate:
        if not self.metric_key.strip():
            raise ValueError("metric_key must not be blank.")
        cleaned = tuple(value.strip() for value in self.allowed_values)
        if not cleaned or any(not value for value in cleaned):
            raise ValueError("Enum predicate requires non-blank allowed values.")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Enum predicate values must be unique.")
        return self


class BooleanPredicate(FrozenModel):
    kind: Literal[PredicateKind.BOOLEAN] = PredicateKind.BOOLEAN
    metric_key: str
    expected: bool

    @model_validator(mode="after")
    def validate_metric_key(self) -> BooleanPredicate:
        if not self.metric_key.strip():
            raise ValueError("metric_key must not be blank.")
        return self


RulePredicate = Annotated[
    NumericRangePredicate | EnumSetPredicate | BooleanPredicate,
    Field(discriminator="kind"),
]


class VastuRule(FrozenModel):
    rule_id: str
    rule_version: str
    spec_version: str
    lifecycle: RuleLifecycle
    category: str
    subject: SubjectSelector
    geometry_semantic: GeometrySemantic
    predicate: RulePredicate
    classification: RuleClassification
    severity: RuleSeverity
    weight: RuleWeight
    precedence: Precedence = 0
    source_refs: tuple[SourceReference, ...] = ()
    exception_rule_ids: tuple[str, ...] = ()
    explanation_template: str

    @model_validator(mode="after")
    def validate_rule(self) -> VastuRule:
        if not _RULE_ID_RE.fullmatch(self.rule_id):
            raise ValueError("rule_id must use stable uppercase identifier syntax.")
        for version_name, value in (
            ("rule_version", self.rule_version),
            ("spec_version", self.spec_version),
        ):
            if not _SEMVER_RE.fullmatch(value):
                raise ValueError(f"{version_name} must be MAJOR.MINOR.PATCH.")
        if not self.category.strip():
            raise ValueError("Rule category must not be blank.")
        needs_provenance = self.lifecycle in {RuleLifecycle.REVIEWED, RuleLifecycle.FROZEN}
        if needs_provenance and not self.source_refs:
            raise ValueError("REVIEWED/FROZEN rules require at least one source reference.")
        if self.lifecycle is RuleLifecycle.FROZEN and not self.explanation_template.strip():
            raise ValueError("FROZEN rules require an explanation template.")
        if len(self.exception_rule_ids) != len(set(self.exception_rule_ids)):
            raise ValueError("exception_rule_ids must be unique.")
        if self.rule_id in self.exception_rule_ids:
            raise ValueError("A rule cannot list itself as an exception.")
        return self

    @property
    def metric_key(self) -> str:
        return self.predicate.metric_key

    def conflict_key(self) -> tuple[object, ...]:
        return (
            self.subject.canonical_key(),
            self.geometry_semantic.value,
            self.metric_key,
            self.precedence,
        )


class VastuFact(FrozenModel):
    entity_id: str
    entity_type: str
    attributes: tuple[SubjectAttribute, ...] = ()
    geometry_semantic: GeometrySemantic
    metric_key: str
    value: int | str | bool
    evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_fact(self) -> VastuFact:
        identity_values = (self.entity_id, self.entity_type, self.metric_key)
        if any(not value.strip() for value in identity_values):
            raise ValueError("Fact identity fields must not be blank.")
        keys = [item.key for item in self.attributes]
        if len(keys) != len(set(keys)):
            raise ValueError("Fact attribute keys must be unique.")
        return self

    def matches_subject(self, subject: SubjectSelector) -> bool:
        if self.entity_type != subject.entity_type:
            return False
        attributes = {item.key: item.value for item in self.attributes}
        return all(attributes.get(item.key) == item.value for item in subject.attributes)


class RuleEvaluation(FrozenModel):
    rule_id: str
    rule_version: str
    entity_id: str | None
    status: VastuStatus
    actual_value: int | str | bool | None
    raw_weight: RuleWeight
    earned_weight: RuleWeight
    evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_weight(self) -> RuleEvaluation:
        if self.earned_weight > self.raw_weight:
            raise ValueError("earned_weight cannot exceed raw_weight.")
        if self.status is VastuStatus.NOT_APPLICABLE and self.entity_id is not None:
            raise ValueError("NOT_APPLICABLE evaluation must not claim an entity.")
        return self


class RuleBundle(FrozenModel):
    spec_version: str
    production: bool
    rules: tuple[VastuRule, ...]
    sources: tuple[SourceRecord, ...]
    content_hash: str

    @model_validator(mode="after")
    def validate_bundle(self) -> RuleBundle:
        if not _SEMVER_RE.fullmatch(self.spec_version):
            raise ValueError("spec_version must be MAJOR.MINOR.PATCH.")
        if not _SHA256_RE.fullmatch(self.content_hash):
            raise ValueError("content_hash must be lowercase SHA-256 hex.")
        return self

    def canonical_content_bytes(self) -> bytes:
        payload = {
            "spec_version": self.spec_version,
            "production": self.production,
            "rules": [rule.model_dump(mode="json") for rule in self.rules],
            "sources": [source.model_dump(mode="json") for source in self.sources],
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")

    def compute_content_hash(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def verify_hash(self) -> bool:
        return self.content_hash == self.compute_content_hash()
