from __future__ import annotations

from ai_vastu.media_validation_adapter import (
    ImageValidationError,
    validate_image_with_pillow,
)


class UploadContentError(ValueError):
    pass


def validate_image_content(content_type: str, data: bytes) -> None:
    try:
        validate_image_with_pillow(content_type, data)
    except ImageValidationError as exc:
        raise UploadContentError("Image content is corrupt or unsupported.") from exc


def validate_pdf_content(data: bytes) -> None:
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-1024:]:
        raise UploadContentError("PDF content is corrupt or incomplete.")
