from __future__ import annotations

import warnings
from io import BytesIO

from PIL import Image


class ImageValidationError(ValueError):
    pass


def validate_image_with_pillow(content_type: str, data: bytes) -> None:
    expected_format = {
        "image/jpeg": "JPEG",
        "image/png": "PNG",
    }.get(content_type)
    if expected_format is None:
        raise ImageValidationError("Unsupported image content type.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format != expected_format:
                    raise ImageValidationError(
                        "Image format does not match content type."
                    )
                image.verify()
    except ImageValidationError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise ImageValidationError("Image content is corrupt or unsupported.") from exc
