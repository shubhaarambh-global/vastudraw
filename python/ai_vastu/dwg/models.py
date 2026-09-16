from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ai_vastu.plan_schema.base import FrozenModel

DWG_QUALIFICATION_VERSION = "1.0.0"
_SHA256_LENGTH = 64
NonNegativeCount = Annotated[int, Field(ge=0)]
NonNegativeFloat = Annotated[float, Field(ge=0)]
PositiveSeconds = Annotated[int, Field(gt=0, le=600)]


class DwgTargetVersion(StrEnum):
    R2018 = "R2018"


class DwgBackendKind(StrEnum):
    ODA_DRAWINGS_SDK = "ODA_DRAWINGS_SDK"
    LIBREDWG = "LIBREDWG"
    EXTERNAL_COMMAND = "EXTERNAL_COMMAND"


class DwgBackendCandidate(FrozenModel):
    backend_id: str
    kind: DwgBackendKind
    display_name: str
    source_url: str
    source_checked_on: str
    license_summary: str
    supported_targets: tuple[DwgTargetVersion, ...] = ()
    modern_dwg_write: bool
    production_candidate: bool
    bundled: bool = False
    notes: tuple[str, ...] = ()


class DwgBackendCapabilities(FrozenModel):
    backend_id: str
    kind: DwgBackendKind
    backend_version: str
    supported_targets: tuple[DwgTargetVersion, ...]
    modern_dwg_write: bool
    roundtrip_inspection: bool
    production_eligible: bool
    test_backend: bool = False


class DwgExtents(FrozenModel):
    min_x_mm: float
    min_y_mm: float
    max_x_mm: float
    max_y_mm: float


class DwgSemanticFingerprint(FrozenModel):
    room_count: NonNegativeCount
    wall_segment_count: NonNegativeCount
    opening_count: NonNegativeCount
    dimension_count: NonNegativeCount
    stair_count: NonNegativeCount
    extents: DwgExtents


class DwgInspection(FrozenModel):
    version: Literal["1.0.0"] = "1.0.0"
    dwg_version_code: str
    units: Literal["MM", "UNKNOWN"]
    layers: tuple[str, ...]
    scene_hash: str | None = None
    fingerprint: DwgSemanticFingerprint

    @model_validator(mode="after")
    def validate_scene_hash(self) -> DwgInspection:
        if self.scene_hash is not None:
            if len(self.scene_hash) != _SHA256_LENGTH:
                raise ValueError("scene_hash must be a SHA-256 hex digest.")
            int(self.scene_hash, 16)
        return self


class DwgQualificationConfig(FrozenModel):
    target_version: DwgTargetVersion = DwgTargetVersion.R2018
    required_layers: tuple[str, ...] = (
        "AIA_PLOT",
        "AIA_BUILDABLE",
        "AIA_FLOOR",
        "AIA_ROOM",
        "AIA_WALL_EXT",
        "AIA_WALL_INT",
        "AIA_OPENING",
        "AIA_DIM",
        "AIA_ANNOT",
        "AIA_NORTH",
    )
    max_extent_delta_mm: NonNegativeFloat = 1.0
    require_scene_hash: bool = True
    require_dimensions: bool = True


class DwgQualificationReport(FrozenModel):
    version: Literal["1.0.0"] = "1.0.0"
    backend_id: str
    backend_version: str
    target_version: DwgTargetVersion
    source_scene_hash: str
    output_sha256: str | None = None
    qualified: bool
    failures: tuple[str, ...] = ()
    inspection: DwgInspection | None = None
    report_hash: str | None = None

    @model_validator(mode="after")
    def validate_hashes(self) -> DwgQualificationReport:
        if len(self.source_scene_hash) != _SHA256_LENGTH:
            raise ValueError("source_scene_hash must be a SHA-256 hex digest.")
        int(self.source_scene_hash, 16)
        if self.output_sha256 is not None:
            if len(self.output_sha256) != _SHA256_LENGTH:
                raise ValueError("output_sha256 must be a SHA-256 hex digest.")
            int(self.output_sha256, 16)
        if self.report_hash is not None and self.report_hash != self.compute_report_hash():
            raise ValueError("report_hash does not match canonical report content.")
        return self

    def canonical_content_bytes(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"report_hash"})
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return text.encode("utf-8")

    def compute_report_hash(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def with_report_hash(self) -> DwgQualificationReport:
        return self.model_copy(update={"report_hash": self.compute_report_hash()})


class ExternalCommandBackendConfig(FrozenModel):
    backend_id: str
    backend_version: str
    converter_executable: str
    converter_args: tuple[str, ...]
    inspector_executable: str
    inspector_args: tuple[str, ...]
    target_version: DwgTargetVersion = DwgTargetVersion.R2018
    timeout_seconds: PositiveSeconds = 120

    @model_validator(mode="after")
    def validate_templates(self) -> ExternalCommandBackendConfig:
        converter_tokens = " ".join(self.converter_args)
        inspector_tokens = " ".join(self.inspector_args)
        for required in ("{input_dxf}", "{output_dwg}"):
            if required not in converter_tokens:
                raise ValueError(f"converter_args must contain {required}.")
        if "{input_dwg}" not in inspector_tokens:
            raise ValueError("inspector_args must contain {input_dwg}.")
        return self
