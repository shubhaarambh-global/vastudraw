from pathlib import Path
from uuid import UUID

from ai_vastu.generation_intake import (
    GenerationIntakeStore,
    GenerationReferenceKind,
    IncomingGenerationAttachment,
)


def test_generation_intake_accepts_dxf_and_dwg_plan_sources(
    tmp_path: Path,
) -> None:
    store = GenerationIntakeStore(tmp_path)
    project_id = UUID("30000000-0000-0000-0000-000000000265")

    record = store.create(
        project_id,
        "Audit the uploaded plan.",
        (
            IncomingGenerationAttachment(
                original_filename="plan.dxf",
                media_type="application/octet-stream",
                content=b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n",
            ),
            IncomingGenerationAttachment(
                original_filename="plan.dwg",
                media_type="application/octet-stream",
                content=b"AC1027" + b"\x00" * 64,
            ),
        ),
    )

    assert tuple(item.kind for item in record.attachments) == (
        GenerationReferenceKind.DXF,
        GenerationReferenceKind.DWG,
    )

    stored, data = store.read_attachment(
        project_id,
        record.intake_id,
        record.attachments[0].attachment_id,
    )
    assert stored.kind is GenerationReferenceKind.DXF
    assert data.startswith(b"0\nSECTION")
