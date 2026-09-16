from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from ai_vastu.generation_intake import (
    GenerationIntakeError,
    GenerationIntakeStorageConfigurationError,
    GenerationIntakeStore,
    IncomingGenerationAttachment,
    create_generation_intake_store_from_environment,
)

PROJECT_ID = UUID("11111111-aaaa-bbbb-cccc-111111111111")
INTAKE_ID = UUID("22222222-aaaa-bbbb-cccc-222222222222")


def test_generation_intake_hashes_and_persists_references(tmp_path: Path) -> None:
    store = GenerationIntakeStore(tmp_path)
    record = store.create(
        PROJECT_ID,
        " 3BHK residence with practical daylight and client references. ",
        (
            IncomingGenerationAttachment(
                "sketch.png",
                "image/png",
                b"\x89PNG\r\n\x1a\nreference-image",
            ),
            IncomingGenerationAttachment(
                "survey.pdf",
                "application/pdf",
                b"%PDF-1.7\nreference-pdf",
            ),
        ),
        created_at=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
        intake_id=INTAKE_ID,
    )

    assert record.prompt.startswith("3BHK")
    assert record.authoritative_geometry is False
    assert len(record.attachments) == 2
    assert record.content_hash == record.compute_content_hash()
    assert store.get(PROJECT_ID, INTAKE_ID) == record
    assert store.list_for_project(PROJECT_ID) == (record,)


def test_generation_intake_rejects_spoofed_media(tmp_path: Path) -> None:
    store = GenerationIntakeStore(tmp_path)
    with pytest.raises(GenerationIntakeError, match="PDF attachment signature"):
        store.create(
            PROJECT_ID,
            "Reference PDF",
            (IncomingGenerationAttachment("fake.pdf", "application/pdf", b"not-a-pdf"),),
        )


def test_production_upload_storage_fails_closed_without_absolute_path() -> None:
    with pytest.raises(GenerationIntakeStorageConfigurationError):
        create_generation_intake_store_from_environment({"APP_ENV": "production"})
    with pytest.raises(GenerationIntakeStorageConfigurationError):
        create_generation_intake_store_from_environment(
            {
                "APP_ENV": "production",
                "AI_VASTU_GENERATION_UPLOAD_ROOT": ".local/uploads",
            }
        )
