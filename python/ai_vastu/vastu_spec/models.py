from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ai_vastu.plan_schema.base import FrozenModel
from ai_vastu.vastu import RuleLifecycle, SourceRecord, VastuRule

VASTU_SPEC_VERSION = "1.0.0"

_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SpecLifecycle(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    FROZEN = "FROZEN"
    RETIRED = "RETIRED"


class ReviewStatus(StrEnum):
    DRAFT = "DRAFT"
    SOURCE_VERIFIED = "SOURCE_VERIFIED"
    DOMAIN_REVIEWED = "DOMAIN_REVIEWED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReviewDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ReviewerRole(StrEnum):
    VASTU_EXPERT = "VASTU_EXPERT"
    ARCHITECT = "ARCHITECT"
    TECHNICAL_REVIEWER = "TECHNICAL_REVIEWER"
    SOURCE_EDITOR = "SOURCE_EDITOR"


class ReviewerAttestation(FrozenModel):
    reviewer_id: str
    role: ReviewerRole
    decision: ReviewDecision
    reviewed_at: datetime
    note: str

    @model_validator(mode="after")
    def validate_attestation(self) -> ReviewerAttestation:
        if not _ID_RE.fullmatch(self.reviewer_id):
            raise ValueError("reviewer_id must use stable uppercase identifier syntax.")
        if self.reviewed_at.tzinfo is None:
            raise ValueError("reviewed_at must be timezone-aware.")
        if not self.note.strip():
            raise ValueError("Reviewer attestation requires a non-blank note.")
        return self


class RuleReview(FrozenModel):
    status: ReviewStatus
    source_validation_passed: bool = False
    geometry_semantics_reviewed: bool = False
    attestations: tuple[ReviewerAttestation, ...] = ()

    @model_validator(mode="after")
    def validate_review(self) -> RuleReview:
        reviewer_ids = [item.reviewer_id for item in self.attestations]
        if len(reviewer_ids) != len(set(reviewer_ids)):
            raise ValueError("Reviewer attestations must use unique reviewer_id values.")

        if self.status is ReviewStatus.APPROVED:
            if not self.source_validation_passed:
                raise ValueError("APPROVED rule review requires source validation.")
            if not self.geometry_semantics_reviewed:
                raise ValueError("APPROVED rule review requires geometry-semantics review.")
            expert_approvals = [
                item
                for item in self.attestations
                if item.role is ReviewerRole.VASTU_EXPERT
                and item.decision is ReviewDecision.APPROVE
            ]
            if not expert_approvals:
                raise ValueError("APPROVED rule review requires a VASTU_EXPERT approval.")
            if any(item.decision is ReviewDecision.REJECT for item in self.attestations):
                raise ValueError("APPROVED rule review cannot contain a rejection attestation.")

        if self.status is ReviewStatus.REJECTED and not any(
            item.decision is ReviewDecision.REJECT for item in self.attestations
        ):
            raise ValueError("REJECTED rule review requires a rejection attestation.")
        return self


class RuleAuthoringRecord(FrozenModel):
    rule: VastuRule
    normalized_statement: str
    interpretation_notes: str
    review: RuleReview

    @model_validator(mode="after")
    def validate_record(self) -> RuleAuthoringRecord:
        if not self.normalized_statement.strip():
            raise ValueError("normalized_statement must not be blank.")
        if not self.interpretation_notes.strip():
            raise ValueError("interpretation_notes must not be blank.")
        if (
            self.rule.lifecycle is RuleLifecycle.FROZEN
            and self.review.status is not ReviewStatus.APPROVED
        ):
            raise ValueError("FROZEN Vastu rules require an APPROVED review record.")
        if (
            self.review.status is ReviewStatus.APPROVED
            and self.rule.lifecycle is not RuleLifecycle.FROZEN
        ):
            raise ValueError("APPROVED review records must correspond to FROZEN Vastu rules.")
        return self


RuleCount = Annotated[int, Field(ge=0)]


class VastuSpecManifest(FrozenModel):
    spec_version: Literal["1.0.0"]
    title: str
    lifecycle: SpecLifecycle
    rule_ids: tuple[str, ...] = ()
    production_rule_count: RuleCount = 0
    expected_rule_bundle_hash: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_manifest(self) -> VastuSpecManifest:
        if not self.title.strip():
            raise ValueError("Specification title must not be blank.")
        if len(self.rule_ids) != len(set(self.rule_ids)):
            raise ValueError("Manifest rule_ids must be unique.")
        if tuple(sorted(self.rule_ids)) != self.rule_ids:
            raise ValueError("Manifest rule_ids must be sorted for deterministic authoring.")
        if self.expected_rule_bundle_hash is not None and not _SHA256_RE.fullmatch(
            self.expected_rule_bundle_hash
        ):
            raise ValueError("expected_rule_bundle_hash must be lowercase SHA-256 hex.")
        if self.lifecycle is SpecLifecycle.FROZEN:
            if not self.rule_ids:
                raise ValueError("A FROZEN specification cannot contain zero rules.")
            if self.production_rule_count != len(self.rule_ids):
                raise ValueError(
                    "FROZEN specification production_rule_count must equal rule count."
                )
            if self.expected_rule_bundle_hash is None:
                raise ValueError("FROZEN specification requires expected_rule_bundle_hash.")
        elif self.expected_rule_bundle_hash is not None:
            raise ValueError("Only a FROZEN specification may declare a production bundle hash.")
        return self


class LoadedVastuSpecification(FrozenModel):
    manifest: VastuSpecManifest
    sources: tuple[SourceRecord, ...]
    rule_records: tuple[RuleAuthoringRecord, ...]
    authoring_content_hash: str

    @model_validator(mode="after")
    def validate_loaded_spec(self) -> LoadedVastuSpecification:
        if not _SHA256_RE.fullmatch(self.authoring_content_hash):
            raise ValueError("authoring_content_hash must be lowercase SHA-256 hex.")
        return self

    def canonical_content_bytes(self) -> bytes:
        payload = {
            "manifest": self.manifest.model_dump(mode="json"),
            "sources": [item.model_dump(mode="json") for item in self.sources],
            "rule_records": [item.model_dump(mode="json") for item in self.rule_records],
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")

    def compute_authoring_content_hash(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def verify_hash(self) -> bool:
        return self.authoring_content_hash == self.compute_authoring_content_hash()

    @property
    def production_ready(self) -> bool:
        return self.manifest.lifecycle is SpecLifecycle.FROZEN


class VastuSpecRelease(FrozenModel):
    spec_version: Literal["1.0.0"]
    authoring_content_hash: str
    rule_bundle_hash: str
    rule_count: Annotated[int, Field(gt=0)]
    released_at: datetime
    release_hash: str

    def canonical_content_bytes(self) -> bytes:
        payload = {
            "spec_version": self.spec_version,
            "authoring_content_hash": self.authoring_content_hash,
            "rule_bundle_hash": self.rule_bundle_hash,
            "rule_count": self.rule_count,
            "released_at": self.released_at.isoformat(),
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")

    def compute_release_hash(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def verify_hash(self) -> bool:
        return self.release_hash == self.compute_release_hash()

    @model_validator(mode="after")
    def validate_release(self) -> VastuSpecRelease:
        for field_name, value in (
            ("authoring_content_hash", self.authoring_content_hash),
            ("rule_bundle_hash", self.rule_bundle_hash),
            ("release_hash", self.release_hash),
        ):
            if not _SHA256_RE.fullmatch(value):
                raise ValueError(f"{field_name} must be lowercase SHA-256 hex.")
        if self.released_at.tzinfo is None:
            raise ValueError("released_at must be timezone-aware.")
        return self
