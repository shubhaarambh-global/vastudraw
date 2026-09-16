from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ai_vastu.plan_schema.base import FrozenModel

RELEASE_READINESS_VERSION = "1.0.0"
_HASH_LENGTH = 64
NonNegativeCount = Annotated[int, Field(ge=0)]


class ReleaseDisposition(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"


class ReleaseGateStatus(StrEnum):
    PASS = "PASS"
    BLOCKER = "BLOCKER"
    INFO = "INFO"


class ReleaseGateResult(FrozenModel):
    code: str
    status: ReleaseGateStatus
    message: str
    evidence: tuple[str, ...] = ()


class ProductionReadinessReport(FrozenModel):
    version: Literal["1.0.0"] = "1.0.0"
    disposition: ReleaseDisposition
    gates: tuple[ReleaseGateResult, ...]
    blocker_codes: tuple[str, ...]
    blocker_count: NonNegativeCount
    report_hash: str | None = None

    @model_validator(mode="after")
    def validate_report(self) -> ProductionReadinessReport:
        expected_codes = tuple(
            gate.code for gate in self.gates if gate.status is ReleaseGateStatus.BLOCKER
        )
        if self.blocker_codes != expected_codes:
            raise ValueError("blocker_codes must match blocker gates in deterministic order.")
        if self.blocker_count != len(self.blocker_codes):
            raise ValueError("blocker_count must equal blocker_codes length.")
        expected_disposition = (
            ReleaseDisposition.READY
            if self.blocker_count == 0
            else ReleaseDisposition.BLOCKED
        )
        if self.disposition is not expected_disposition:
            raise ValueError("disposition does not match blocker state.")
        if self.report_hash is not None:
            if len(self.report_hash) != _HASH_LENGTH:
                raise ValueError("report_hash must be a SHA-256 hex digest.")
            int(self.report_hash, 16)
            if self.report_hash != self.compute_report_hash():
                raise ValueError("report_hash does not match canonical report content.")
        return self

    def canonical_content_bytes(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"report_hash"})
        text = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return text.encode("utf-8")

    def compute_report_hash(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def with_report_hash(self) -> ProductionReadinessReport:
        return self.model_copy(update={"report_hash": self.compute_report_hash()})
