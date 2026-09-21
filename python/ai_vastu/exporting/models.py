from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from ai_vastu.plan_schema import (
    Annotation,
    AxisSegment,
    Dimension,
    Fixture,
    Furniture,
    IntPolygon,
    Opening,
    PurposefulSiteSpace,
    RoomGeometry,
    Stair,
    Wall,
)
from ai_vastu.plan_schema.base import FrozenModel
from ai_vastu.plan_schema.units import MicroDegrees, PositiveMM

EXPORT_SCENE_VERSION = "1.1.0"
_HASH_RE_LENGTH = 64
PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeInt = Annotated[int, Field(ge=0)]
JpegQuality = Annotated[int, Field(ge=1, le=100)]


class ExportFormat(StrEnum):
    SVG = "SVG"
    JPEG = "JPEG"
    PDF = "PDF"
    DXF = "DXF"


class DimensionDisplayUnit(StrEnum):
    FEET_INCHES = "ft-in"
    METRES = "m"


class SceneRoad(FrozenModel):
    id: UUID
    name: str | None = None
    axes: tuple[AxisSegment, ...]
    width_mm: PositiveMM | None = None
    primary_access: bool = False


class DrawingScene(FrozenModel):
    version: Literal["1.1.0"] = "1.1.0"
    project_id: UUID
    revision_id: UUID
    floor_id: UUID
    floor_index: NonNegativeInt
    floor_name: str
    source_plan_hash: str
    north_rotation_udeg: MicroDegrees
    plot_boundary: IntPolygon
    buildable_boundary: IntPolygon
    floor_boundary: IntPolygon
    roads: tuple[SceneRoad, ...] = ()
    rooms: tuple[RoomGeometry, ...] = ()
    site_spaces: tuple[PurposefulSiteSpace, ...] = ()
    walls: tuple[Wall, ...] = ()
    openings: tuple[Opening, ...] = ()
    stairs: tuple[Stair, ...] = ()
    fixtures: tuple[Fixture, ...] = ()
    furniture: tuple[Furniture, ...] = ()
    dimensions: tuple[Dimension, ...] = ()
    annotations: tuple[Annotation, ...] = ()
    scene_hash: str | None = None

    @model_validator(mode="after")
    def validate_hashes(self) -> DrawingScene:
        if len(self.source_plan_hash) != _HASH_RE_LENGTH:
            raise ValueError("source_plan_hash must be a SHA-256 hex digest.")
        int(self.source_plan_hash, 16)
        if self.scene_hash is not None:
            if len(self.scene_hash) != _HASH_RE_LENGTH:
                raise ValueError("scene_hash must be a SHA-256 hex digest.")
            int(self.scene_hash, 16)
            if self.scene_hash != self.compute_scene_hash():
                raise ValueError("scene_hash does not match canonical DrawingScene content.")
        return self

    def canonical_content_bytes(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"scene_hash"})
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return text.encode("utf-8")

    def compute_scene_hash(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def with_scene_hash(self) -> DrawingScene:
        return self.model_copy(update={"scene_hash": self.compute_scene_hash()})


class RasterExportConfig(FrozenModel):
    width_px: Annotated[int, Field(ge=512, le=16_384)] = 2_400
    height_px: Annotated[int, Field(ge=512, le=16_384)] = 1_800
    margin_px: Annotated[int, Field(ge=0, le=2_048)] = 80
    jpeg_quality: JpegQuality = 92
    show_room_labels: bool = True
    show_dimensions: bool = True
    show_annotations: bool = True
    show_north_arrow: bool = True
    dimension_unit: DimensionDisplayUnit = DimensionDisplayUnit.FEET_INCHES


class SvgExportConfig(FrozenModel):
    width_px: Annotated[int, Field(ge=512, le=16_384)] = 1_600
    height_px: Annotated[int, Field(ge=512, le=16_384)] = 1_200
    margin_px: Annotated[int, Field(ge=0, le=2_048)] = 70
    show_room_labels: bool = True
    show_dimensions: bool = True
    show_annotations: bool = True
    show_north_arrow: bool = True
    dimension_unit: DimensionDisplayUnit = DimensionDisplayUnit.FEET_INCHES


class PdfExportConfig(FrozenModel):
    page_size: Literal["A4_LANDSCAPE", "A3_LANDSCAPE"] = "A3_LANDSCAPE"
    margin_mm: Annotated[int, Field(ge=5, le=50)] = 15
    title_block_height_mm: Annotated[int, Field(ge=0, le=50)] = 18
    show_room_labels: bool = True
    show_dimensions: bool = True
    show_annotations: bool = True
    show_north_arrow: bool = True
    dimension_unit: DimensionDisplayUnit = DimensionDisplayUnit.FEET_INCHES


class DxfExportConfig(FrozenModel):
    dxf_version: Literal["R2018"] = "R2018"
    room_label_height_mm: PositiveMM = 250
    annotation_height_mm: PositiveMM = 180
    dimension_text_height_mm: PositiveMM = 180
    dimension_arrow_size_mm: PositiveMM = 120
    north_arrow_length_mm: PositiveMM = 1_200
    show_room_labels: bool = True
    show_dimensions: bool = True
    show_annotations: bool = True
    show_north_arrow: bool = True
    dimension_unit: DimensionDisplayUnit = DimensionDisplayUnit.FEET_INCHES


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    format: str
    filename: str
    media_type: str
    content: bytes
    sha256: str
    scene_hash: str

    @classmethod
    def create(
        cls,
        *,
        format: str,
        filename: str,
        media_type: str,
        content: bytes,
        scene_hash: str,
    ) -> ExportArtifact:
        return cls(
            format=format,
            filename=filename,
            media_type=media_type,
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
            scene_hash=scene_hash,
        )


@dataclass(frozen=True, slots=True)
class ExportBundle:
    scene: DrawingScene
    svg: ExportArtifact
    jpeg: ExportArtifact
    pdf: ExportArtifact
    dxf: ExportArtifact
