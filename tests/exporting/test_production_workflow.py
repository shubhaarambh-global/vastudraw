from __future__ import annotations

import re
from io import StringIO
from uuid import UUID

import ezdxf
import pytest
from pydantic import ValidationError

from ai_vastu.exporting import (
    ExportFormat,
    ExportScope,
    ProductionExportError,
    ProductionExportRequest,
    export_selected_document,
    sanitize_filename_component,
)

from .test_professional_renderer import professional_plan

CANDIDATE_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _request(
    export_format: ExportFormat,
    *,
    floor_index: int | None = 0,
    scope: ExportScope = ExportScope.FLOOR,
) -> ProductionExportRequest:
    document = professional_plan()
    return ProductionExportRequest(
        revision_id=document.revision_id,
        candidate_id=CANDIDATE_ID,
        format=export_format,
        scope=scope,
        floor_index=floor_index,
    )


@pytest.mark.parametrize(
    ("export_format", "media_type", "signature"),
    [
        (ExportFormat.SVG, "image/svg+xml", b"<?xml"),
        (ExportFormat.JPEG, "image/jpeg", b"\xff\xd8"),
        (ExportFormat.PDF, "application/pdf", b"%PDF"),
        (ExportFormat.DXF, "application/dxf", b"  0\nSECTION"),
    ],
)
def test_selected_candidate_exports_every_supported_format(
    export_format: ExportFormat,
    media_type: str,
    signature: bytes,
) -> None:
    document = professional_plan()
    before = document.to_canonical_json()
    result = export_selected_document(
        document,
        project_name="Sharma Residence",
        expected_plan_hash=document.content_hash or "",
        request=_request(export_format),
    )

    assert result.artifact.media_type == media_type
    assert result.artifact.content.startswith(signature)
    assert result.artifact.filename == (
        f"vastudraw-sharma-residence-ground-floor.{export_format.value.lower()}"
    )
    assert result.manifest.candidate_id == CANDIDATE_ID
    assert result.manifest.source_plan_hash == document.content_hash
    assert result.manifest.artifacts[0].byte_size == len(result.artifact.content)
    assert document.to_canonical_json() == before
    assert document.compute_content_hash() == document.content_hash


def test_svg_and_dxf_preserve_professional_canonical_semantics() -> None:
    document = professional_plan()
    svg = export_selected_document(
        document,
        project_name="Residence",
        expected_plan_hash=document.content_hash or "",
        request=_request(ExportFormat.SVG),
    ).artifact.content.decode("utf-8")
    assert 'id="walls"' in svg
    assert 'id="openings"' in svg
    assert svg.count('data-opening-id="') == len(document.floors[0].openings)
    assert 'id="stairs"' in svg
    assert str(document.floors[0].stairs[0].id) in svg
    assert "VASTUDRAW" in svg
    assert "COMMON TOILET" in svg

    dxf = export_selected_document(
        document,
        project_name="Residence",
        expected_plan_hash=document.content_hash or "",
        request=_request(ExportFormat.DXF),
    ).artifact.content.decode("utf-8")
    drawing = ezdxf.read(StringIO(dxf))
    assert "AIA_WALL_EXT" in drawing.layers
    assert "AIA_DOOR" in drawing.layers
    assert "AIA_STAIR_TREAD" in drawing.layers


@pytest.mark.parametrize("floor_count", [1, 2, 3, 4])
def test_combined_pdf_has_one_ordered_page_per_canonical_floor(floor_count: int) -> None:
    document = professional_plan(floors=floor_count)
    request = ProductionExportRequest(
        revision_id=document.revision_id,
        candidate_id=CANDIDATE_ID,
        format=ExportFormat.PDF,
        scope=ExportScope.ALL_FLOORS,
        floor_index=None,
    )
    result = export_selected_document(
        document,
        project_name="30 x 50 East Home",
        expected_plan_hash=document.content_hash or "",
        request=request,
    )

    assert len(re.findall(rb"/Type /Page(?!s)", result.artifact.content)) == floor_count
    assert result.artifact.filename == "vastudraw-30-x-50-east-home-all-floors.pdf"
    assert result.manifest.artifacts[0].combined
    assert result.manifest.artifacts[0].floor_index is None
    labels = [
        floor.name.encode("ascii")
        for floor in sorted(document.floors, key=lambda item: item.index)
    ]
    positions = [result.artifact.content.find(label) for label in labels]
    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_individual_floor_names_and_order_follow_canonical_floors() -> None:
    document = professional_plan(floors=4)
    filenames = []
    for floor in sorted(document.floors, key=lambda item: item.index):
        request = ProductionExportRequest(
            revision_id=document.revision_id,
            candidate_id=CANDIDATE_ID,
            format=ExportFormat.SVG,
            floor_index=floor.index,
        )
        result = export_selected_document(
            document,
            project_name="Patel / Home ..\\unsafe",
            expected_plan_hash=document.content_hash or "",
            request=request,
        )
        filenames.append(result.artifact.filename)
        assert result.manifest.artifacts[0].floor_index == floor.index
        assert result.manifest.artifacts[0].floor_label == floor.name

    assert filenames == [
        "vastudraw-patel-home-unsafe-ground-floor.svg",
        "vastudraw-patel-home-unsafe-floor-1.svg",
        "vastudraw-patel-home-unsafe-floor-2.svg",
        "vastudraw-patel-home-unsafe-floor-3.svg",
    ]
    assert all("/" not in name and "\\" not in name and ".." not in name for name in filenames)


@pytest.mark.parametrize("export_format", tuple(ExportFormat))
def test_each_format_can_export_an_individual_upper_floor(
    export_format: ExportFormat,
) -> None:
    document = professional_plan(floors=2)
    request = ProductionExportRequest(
        revision_id=document.revision_id,
        candidate_id=CANDIDATE_ID,
        format=export_format,
        floor_index=1,
    )
    result = export_selected_document(
        document,
        project_name="Upper Floor Home",
        expected_plan_hash=document.content_hash or "",
        request=request,
    )
    entry = result.manifest.artifacts[0]
    assert entry.floor_index == 1
    assert entry.floor_label == "Floor 1"
    assert result.artifact.filename.endswith(f"-floor-1.{export_format.value.lower()}")


def test_svg_and_combined_pdf_are_deterministic_for_identical_source() -> None:
    document = professional_plan(floors=2)
    svg_request = ProductionExportRequest(
        revision_id=document.revision_id,
        candidate_id=CANDIDATE_ID,
        format=ExportFormat.SVG,
        floor_index=0,
    )
    combined_request = ProductionExportRequest(
        revision_id=document.revision_id,
        candidate_id=CANDIDATE_ID,
        format=ExportFormat.PDF,
        scope=ExportScope.ALL_FLOORS,
        floor_index=None,
    )
    first_svg = export_selected_document(
        document,
        project_name="Residence",
        expected_plan_hash=document.content_hash or "",
        request=svg_request,
    )
    second_svg = export_selected_document(
        document,
        project_name="Residence",
        expected_plan_hash=document.content_hash or "",
        request=svg_request,
    )
    first_pdf = export_selected_document(
        document,
        project_name="Residence",
        expected_plan_hash=document.content_hash or "",
        request=combined_request,
    )
    second_pdf = export_selected_document(
        document,
        project_name="Residence",
        expected_plan_hash=document.content_hash or "",
        request=combined_request,
    )
    assert first_svg.artifact.content == second_svg.artifact.content
    assert first_svg.manifest == second_svg.manifest
    assert first_pdf.artifact.content == second_pdf.artifact.content
    assert first_pdf.manifest == second_pdf.manifest


def test_closed_format_allowlist_rejects_unsafe_values() -> None:
    document = professional_plan()
    for unsafe in ("PNG", "../../secret", "PDF.exe", "pdf/../../x"):
        with pytest.raises(ValidationError):
            ProductionExportRequest.model_validate(
                {
                    "revision_id": str(document.revision_id),
                    "candidate_id": str(CANDIDATE_ID),
                    "format": unsafe,
                    "scope": "FLOOR",
                    "floor_index": 0,
                }
            )
    assert sanitize_filename_component(" ../../My Project\\plans ") == "my-project-plans"


def test_source_hash_mismatch_and_missing_floor_fail_closed() -> None:
    document = professional_plan()
    with pytest.raises(ProductionExportError, match="EXPORT_SOURCE_HASH_MISMATCH"):
        export_selected_document(
            document,
            project_name="Residence",
            expected_plan_hash="0" * 64,
            request=_request(ExportFormat.PDF),
        )

    with pytest.raises(ProductionExportError, match="EXPORT_FLOOR_NOT_FOUND"):
        export_selected_document(
            document,
            project_name="Residence",
            expected_plan_hash=document.content_hash or "",
            request=ProductionExportRequest(
                revision_id=document.revision_id,
                candidate_id=CANDIDATE_ID,
                format=ExportFormat.PDF,
                floor_index=3,
            ),
        )
