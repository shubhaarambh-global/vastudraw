from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
from PIL import Image

from ai_vastu.generation_intake import (
    GenerationIntakeError,
    GenerationIntakeStorageConfigurationError,
    GenerationIntakeStore,
    IncomingGenerationAttachment,
    create_generation_intake_store_from_environment,
)

PROJECT_ID = UUID("11111111-aaaa-bbbb-cccc-111111111111")
INTAKE_ID = UUID("22222222-aaaa-bbbb-cccc-222222222222")


def _image_bytes(image_format: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format=image_format)
    return buffer.getvalue()


def test_generation_intake_hashes_and_persists_references(tmp_path: Path) -> None:
    store = GenerationIntakeStore(tmp_path)
    record = store.create(
        PROJECT_ID,
        " 3BHK residence with practical daylight and client references. ",
        (
            IncomingGenerationAttachment(
                "sketch.png",
                "image/png",
                _image_bytes("PNG"),
            ),
            IncomingGenerationAttachment(
                "survey.pdf",
                "application/pdf",
                b"%PDF-1.7\nreference-pdf\n%%EOF\n",
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


@pytest.mark.parametrize(
    ("filename", "media_type", "content"),
    [
        ("truncated.jpg", "image/jpeg", b"\xff\xd8\xff"),
        ("truncated.png", "image/png", b"\x89PNG\r\n\x1a\n"),
        ("truncated.pdf", "application/pdf", b"%PDF-"),
    ],
)
def test_generation_intake_rejects_truncated_magic_only_uploads(
    tmp_path: Path,
    filename: str,
    media_type: str,
    content: bytes,
) -> None:
    store = GenerationIntakeStore(tmp_path)

    with pytest.raises(GenerationIntakeError, match="signature"):
        store.create(
            PROJECT_ID,
            "Truncated reference",
            (IncomingGenerationAttachment(filename, media_type, content),),
        )


def test_generation_intake_rejects_disagreeing_image_extension_and_media_type(
    tmp_path: Path,
) -> None:
    store = GenerationIntakeStore(tmp_path)

    with pytest.raises(GenerationIntakeError, match="extension and media type disagree"):
        store.create(
            PROJECT_ID,
            "Reference image",
            (
                IncomingGenerationAttachment(
                    "spoof.png",
                    "image/jpeg",
                    b"\xff\xd8\xffreference-image",
                ),
            ),
        )


def test_generation_intake_rejects_unsupported_extension_with_valid_image(
    tmp_path: Path,
) -> None:
    store = GenerationIntakeStore(tmp_path)

    with pytest.raises(GenerationIntakeError, match="Only JPEG, PNG, PDF"):
        store.create(
            PROJECT_ID,
            "Reference image",
            (
                IncomingGenerationAttachment(
                    "payload.exe",
                    "image/png",
                    _image_bytes("PNG"),
                ),
            ),
        )


@pytest.mark.parametrize(
    ("filename", "media_type", "content"),
    [
        ("spoof.png", "image/png", b"\xff\xd8\xffreference-image"),
        ("spoof.jpg", "image/jpeg", b"\x89PNG\r\n\x1a\nreference-image"),
    ],
)
def test_generation_intake_rejects_image_signature_subtype_mismatch(
    tmp_path: Path,
    filename: str,
    media_type: str,
    content: bytes,
) -> None:
    store = GenerationIntakeStore(tmp_path)

    with pytest.raises(GenerationIntakeError, match="signature does not match"):
        store.create(
            PROJECT_ID,
            "Reference image",
            (IncomingGenerationAttachment(filename, media_type, content),),
        )


@pytest.mark.parametrize("app_env", ["production", "staging"])
def test_deployed_upload_storage_fails_closed_without_absolute_path(app_env: str) -> None:
    with pytest.raises(GenerationIntakeStorageConfigurationError):
        create_generation_intake_store_from_environment({"APP_ENV": app_env})
    with pytest.raises(GenerationIntakeStorageConfigurationError):
        create_generation_intake_store_from_environment(
            {
                "APP_ENV": app_env,
                "AI_VASTU_GENERATION_UPLOAD_ROOT": ".local/uploads",
            }
        )


def test_staging_accepts_absolute_upload_root(tmp_path: Path) -> None:
    configured = tmp_path / "uploads"
    store = create_generation_intake_store_from_environment(
        {"APP_ENV": "staging", "AI_VASTU_GENERATION_UPLOAD_ROOT": str(configured)}
    )
    assert store.root == configured.resolve()
    assert configured.is_dir()


def test_development_retains_relative_upload_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    store = create_generation_intake_store_from_environment(
        {"APP_ENV": "development", "AI_VASTU_GENERATION_UPLOAD_ROOT": "uploads"}
    )
    assert store.root == (tmp_path / "uploads").resolve()
