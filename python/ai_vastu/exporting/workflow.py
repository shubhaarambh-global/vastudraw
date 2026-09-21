from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_vastu.plan_schema import PlanDocument
from ai_vastu.plan_schema.base import FrozenModel

from .dxf_exporter import render_dxf
from .jpeg_exporter import render_jpeg
from .models import (
    EXPORT_SCENE_VERSION,
    DxfExportConfig,
    ExportArtifact,
    ExportFormat,
    PdfExportConfig,
    RasterExportConfig,
    SvgExportConfig,
)
from .pdf_exporter import render_combined_pdf, render_pdf
from .scene import build_drawing_scene
from .svg_exporter import render_svg

_SAFE_SLUG = re.compile(r"[^a-z0-9]+")


class ExportScope(StrEnum):
    FLOOR = "FLOOR"
    ALL_FLOORS = "ALL_FLOORS"


class ProductionExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    revision_id: UUID
    candidate_id: UUID
    format: ExportFormat
    scope: ExportScope = ExportScope.FLOOR
    floor_index: int | None = Field(default=0, ge=0, le=99)

    @model_validator(mode="after")
    def validate_scope(self) -> ProductionExportRequest:
        if self.scope is ExportScope.ALL_FLOORS:
            if self.format is not ExportFormat.PDF:
                raise ValueError("ALL_FLOORS is supported only for combined PDF export.")
            if self.floor_index is not None:
                raise ValueError("Combined PDF export must not specify floor_index.")
        elif self.floor_index is None:
            raise ValueError("Single-floor export requires floor_index.")
        return self


class ExportManifestEntry(FrozenModel):
    format: ExportFormat
    floor_index: int | None = None
    floor_label: str
    filename: str
    media_type: str
    source_plan_hash: str
    candidate_id: UUID
    byte_size: int = Field(ge=1)
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    combined: bool = False


class ExportManifest(FrozenModel):
    manifest_version: Literal["2D9I.1"] = "2D9I.1"
    renderer_version: str = EXPORT_SCENE_VERSION
    project_id: UUID
    revision_id: UUID
    candidate_id: UUID
    source_plan_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifacts: tuple[ExportManifestEntry, ...]


@dataclass(frozen=True, slots=True)
class ProductionExportResult:
    artifact: ExportArtifact
    manifest: ExportManifest


class ProductionExportError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def sanitize_filename_component(value: str, *, fallback: str = "project") -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = _SAFE_SLUG.sub("-", normalized.lower()).strip("-")
    return (slug[:64].rstrip("-") or fallback).lower()


def _extension(export_format: ExportFormat) -> str:
    return {
        ExportFormat.SVG: "svg",
        ExportFormat.JPEG: "jpeg",
        ExportFormat.PDF: "pdf",
        ExportFormat.DXF: "dxf",
    }[export_format]


def _individual_filename(project_name: str, floor_name: str, export_format: ExportFormat) -> str:
    project = sanitize_filename_component(project_name)
    floor = sanitize_filename_component(floor_name, fallback="floor")
    return f"vastudraw-{project}-{floor}.{_extension(export_format)}"


def _combined_filename(project_name: str) -> str:
    return f"vastudraw-{sanitize_filename_component(project_name)}-all-floors.pdf"


def _render_single(
    document: PlanDocument,
    request: ProductionExportRequest,
    *,
    svg: SvgExportConfig,
    raster: RasterExportConfig,
    pdf: PdfExportConfig,
    dxf: DxfExportConfig,
) -> tuple[ExportArtifact, int, str]:
    assert request.floor_index is not None
    floor = next(
        (item for item in document.floors if item.index == request.floor_index),
        None,
    )
    if floor is None:
        raise ProductionExportError(
            "EXPORT_FLOOR_NOT_FOUND",
            f"Canonical floor index {request.floor_index} does not exist.",
        )
    scene = build_drawing_scene(document, floor_id=floor.id)
    if request.format is ExportFormat.SVG:
        artifact = render_svg(scene, svg)
    elif request.format is ExportFormat.JPEG:
        artifact = render_jpeg(scene, raster)
    elif request.format is ExportFormat.PDF:
        artifact = render_pdf(scene, pdf)
    else:
        artifact = render_dxf(scene, dxf)
    return artifact, floor.index, floor.name


def export_selected_document(
    document: PlanDocument,
    *,
    project_name: str,
    expected_plan_hash: str,
    request: ProductionExportRequest,
    svg: SvgExportConfig | None = None,
    raster: RasterExportConfig | None = None,
    pdf: PdfExportConfig | None = None,
    dxf: DxfExportConfig | None = None,
) -> ProductionExportResult:
    before_json = document.to_canonical_json()
    actual_hash = document.compute_content_hash()
    if document.content_hash is None or document.content_hash != actual_hash:
        raise ProductionExportError(
            "EXPORT_SOURCE_HASH_INVALID",
            "The selected canonical document does not carry a valid content hash.",
        )
    if expected_plan_hash != actual_hash:
        raise ProductionExportError(
            "EXPORT_SOURCE_HASH_MISMATCH",
            "The persisted revision hash does not match its canonical document.",
        )

    svg_config = svg or SvgExportConfig()
    raster_config = raster or RasterExportConfig()
    pdf_config = pdf or PdfExportConfig()
    dxf_config = dxf or DxfExportConfig()
    try:
        if request.scope is ExportScope.ALL_FLOORS:
            scenes = tuple(
                build_drawing_scene(document, floor_id=floor.id)
                for floor in sorted(document.floors, key=lambda item: item.index)
            )
            artifact = render_combined_pdf(scenes, pdf_config)
            floor_index = None
            floor_label = "All Floors"
            filename = _combined_filename(project_name)
            combined = True
        else:
            artifact, floor_index, floor_label = _render_single(
                document,
                request,
                svg=svg_config,
                raster=raster_config,
                pdf=pdf_config,
                dxf=dxf_config,
            )
            filename = _individual_filename(project_name, floor_label, request.format)
            combined = False
    except ProductionExportError:
        raise
    except Exception as exc:
        raise ProductionExportError(
            "EXPORT_RENDER_FAILED",
            "The selected plan could not be rendered in the requested format.",
        ) from exc

    artifact = replace(artifact, filename=filename)
    if (
        document.to_canonical_json() != before_json
        or document.compute_content_hash() != actual_hash
    ):
        raise ProductionExportError(
            "EXPORT_SOURCE_MUTATED",
            "Export rendering changed canonical plan content.",
        )

    entry = ExportManifestEntry(
        format=request.format,
        floor_index=floor_index,
        floor_label=floor_label,
        filename=artifact.filename,
        media_type=artifact.media_type,
        source_plan_hash=actual_hash,
        candidate_id=request.candidate_id,
        byte_size=len(artifact.content),
        artifact_sha256=artifact.sha256,
        combined=combined,
    )
    return ProductionExportResult(
        artifact=artifact,
        manifest=ExportManifest(
            project_id=document.project_id,
            revision_id=document.revision_id,
            candidate_id=request.candidate_id,
            source_plan_hash=actual_hash,
            artifacts=(entry,),
        ),
    )
