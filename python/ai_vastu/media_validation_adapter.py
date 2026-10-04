from __future__ import annotations

import warnings
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps

MAX_PLAN_RASTER_INPUT_BYTES = 20 * 1024 * 1024
MAX_PLAN_RASTER_DIMENSION_PX = 4096
MAX_PLAN_RASTER_PIXELS = 16_000_000
MAX_PLAN_RASTER_PNG_BYTES = 12 * 1024 * 1024

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"


class ImageValidationError(ValueError):
    pass


class PlanRasterNormalizationError(ValueError):
    """A sanitized, fail-closed provider-facing raster preparation failure."""


@dataclass(frozen=True, slots=True)
class NormalizedPlanRaster:
    content_type: str
    data: bytes


@dataclass(frozen=True, slots=True)
class ValidatedPlanRaster:
    content_type: str
    data: bytes


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


def _check_plan_raster_bounds(width: int, height: int) -> None:
    if width < 1 or height < 1:
        raise PlanRasterNormalizationError("Plan image dimensions are invalid.")
    if (
        width > MAX_PLAN_RASTER_DIMENSION_PX
        or height > MAX_PLAN_RASTER_DIMENSION_PX
        or width * height > MAX_PLAN_RASTER_PIXELS
    ):
        raise PlanRasterNormalizationError("Plan image exceeds safe raster bounds.")


def normalize_nvidia_plan_raster(
    content_type: str,
    data: bytes,
) -> NormalizedPlanRaster:
    expected = {
        "image/png": ("PNG", _PNG_SIGNATURE),
        "image/jpeg": ("JPEG", _JPEG_SIGNATURE),
    }.get(content_type)
    if expected is None:
        raise PlanRasterNormalizationError("Plan image content type is unsupported.")
    if not data or len(data) > MAX_PLAN_RASTER_INPUT_BYTES:
        raise PlanRasterNormalizationError("Plan image exceeds the input-byte limit.")

    expected_format, signature = expected
    if not data.startswith(signature):
        raise PlanRasterNormalizationError("Plan image signature is invalid.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format != expected_format:
                    raise PlanRasterNormalizationError(
                        "Plan image format does not match its content type."
                    )
                if getattr(image, "n_frames", 1) != 1:
                    raise PlanRasterNormalizationError(
                        "Plan image must contain exactly one frame."
                    )
                _check_plan_raster_bounds(*image.size)
                image.load()

                if expected_format == "PNG":
                    return NormalizedPlanRaster(content_type="image/png", data=data)

                oriented = ImageOps.exif_transpose(image)
                try:
                    _check_plan_raster_bounds(*oriented.size)
                    rgb = oriented.convert("RGB")
                    try:
                        output = BytesIO()
                        rgb.save(
                            output,
                            format="PNG",
                            optimize=False,
                            compress_level=9,
                        )
                        encoded = output.getvalue()
                    finally:
                        rgb.close()
                finally:
                    if oriented is not image:
                        oriented.close()
    except PlanRasterNormalizationError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise PlanRasterNormalizationError(
            "Plan image could not be safely decoded."
        ) from exc

    if not encoded.startswith(_PNG_SIGNATURE) or len(encoded) > MAX_PLAN_RASTER_PNG_BYTES:
        raise PlanRasterNormalizationError("Normalized plan PNG exceeds safe bounds.")
    return NormalizedPlanRaster(content_type="image/png", data=encoded)


def validate_plan_raster(
    content_type: str,
    data: bytes,
) -> ValidatedPlanRaster:
    """Validate a bounded raster while preserving its original PNG/JPEG bytes."""

    expected = {
        "image/png": ("PNG", _PNG_SIGNATURE),
        "image/jpeg": ("JPEG", _JPEG_SIGNATURE),
    }.get(content_type)
    if expected is None:
        raise PlanRasterNormalizationError("Plan image content type is unsupported.")
    if not data or len(data) > MAX_PLAN_RASTER_INPUT_BYTES:
        raise PlanRasterNormalizationError("Plan image exceeds the input-byte limit.")

    expected_format, signature = expected
    if not data.startswith(signature):
        raise PlanRasterNormalizationError("Plan image signature is invalid.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format != expected_format:
                    raise PlanRasterNormalizationError(
                        "Plan image format does not match its content type."
                    )
                if getattr(image, "n_frames", 1) != 1:
                    raise PlanRasterNormalizationError(
                        "Plan image must contain exactly one frame."
                    )
                _check_plan_raster_bounds(*image.size)
                image.load()
    except PlanRasterNormalizationError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise PlanRasterNormalizationError(
            "Plan image could not be safely decoded."
        ) from exc

    return ValidatedPlanRaster(content_type=content_type, data=data)


def validate_ollama_plan_raster(
    content_type: str,
    data: bytes,
) -> ValidatedPlanRaster:
    """Backward-compatible name for the provider-neutral raster validator."""

    return validate_plan_raster(content_type, data)
