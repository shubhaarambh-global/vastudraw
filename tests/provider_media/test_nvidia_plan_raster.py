from __future__ import annotations

import io

import pytest
from PIL import Image

import ai_vastu.media_validation_adapter as adapter
from ai_vastu.media_validation_adapter import (
    PlanRasterNormalizationError,
    normalize_nvidia_plan_raster,
)


def _image_bytes(
    format_name: str,
    *,
    size: tuple[int, int] = (8, 6),
    mode: str = "RGB",
    exif_orientation: int | None = None,
) -> bytes:
    image = Image.new(mode, size, 128)
    output = io.BytesIO()
    kwargs: dict[str, object] = {}
    if exif_orientation is not None:
        exif = Image.Exif()
        exif[274] = exif_orientation
        kwargs["exif"] = exif
    image.save(output, format=format_name, **kwargs)
    image.close()
    return output.getvalue()


def _open(data: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(data))
    image.load()
    return image


def test_valid_png_is_fully_validated_and_passed_through_unchanged() -> None:
    source = _image_bytes("PNG")

    normalized = normalize_nvidia_plan_raster("image/png", source)

    assert normalized.content_type == "image/png"
    assert normalized.data == source
    with _open(normalized.data) as image:
        assert image.format == "PNG"
        assert image.size == (8, 6)


@pytest.mark.parametrize("mode", ("RGB", "L", "CMYK"))
def test_valid_jpeg_is_deterministically_normalized_to_metadata_free_rgb_png(
    mode: str,
) -> None:
    source = _image_bytes("JPEG", mode=mode)

    first = normalize_nvidia_plan_raster("image/jpeg", source)
    second = normalize_nvidia_plan_raster("image/jpeg", source)

    assert first == second
    assert first.content_type == "image/png"
    assert first.data.startswith(b"\x89PNG\r\n\x1a\n")
    assert not first.data.startswith(b"\xff\xd8\xff")
    with _open(first.data) as image:
        assert image.format == "PNG"
        assert image.mode == "RGB"
        assert image.info == {}


@pytest.mark.parametrize("orientation", (6, 8))
def test_jpeg_exif_orientation_is_applied_and_removed(orientation: int) -> None:
    source = _image_bytes(
        "JPEG",
        size=(2, 3),
        exif_orientation=orientation,
    )

    normalized = normalize_nvidia_plan_raster("image/jpeg", source)

    with _open(normalized.data) as image:
        assert image.size == (3, 2)
        assert image.getexif().get(274) is None


@pytest.mark.parametrize(
    ("content_type", "data"),
    (
        ("image/jpeg", b"\xff\xd8\xffmalformed-private-image"),
        ("image/png", b"\x89PNG\r\n\x1a\nmalformed-private-image"),
        ("image/jpeg", _image_bytes("PNG")),
        ("image/png", _image_bytes("JPEG")),
    ),
)
def test_malformed_or_mime_magic_mismatched_images_fail_closed_and_sanitized(
    content_type: str,
    data: bytes,
) -> None:
    with pytest.raises(PlanRasterNormalizationError) as captured:
        normalize_nvidia_plan_raster(content_type, data)

    message = str(captured.value)
    assert "private-image" not in message
    assert repr(data) not in message


def test_input_byte_limit_is_enforced_before_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adapter, "MAX_PLAN_RASTER_INPUT_BYTES", 3)

    with pytest.raises(PlanRasterNormalizationError, match="input-byte"):
        normalize_nvidia_plan_raster("image/jpeg", b"\xff\xd8\xffx")


def test_dimension_and_pixel_limits_are_independently_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _image_bytes("PNG", size=(3, 2))
    monkeypatch.setattr(adapter, "MAX_PLAN_RASTER_DIMENSION_PX", 2)
    with pytest.raises(PlanRasterNormalizationError, match="raster bounds"):
        normalize_nvidia_plan_raster("image/png", source)

    monkeypatch.setattr(adapter, "MAX_PLAN_RASTER_DIMENSION_PX", 4096)
    monkeypatch.setattr(adapter, "MAX_PLAN_RASTER_PIXELS", 5)
    with pytest.raises(PlanRasterNormalizationError, match="raster bounds"):
        normalize_nvidia_plan_raster("image/png", source)


def test_decompression_bomb_detection_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _image_bytes("PNG", size=(2, 2))
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)

    with pytest.raises(PlanRasterNormalizationError, match="safely decoded"):
        normalize_nvidia_plan_raster("image/png", source)


def test_normalized_png_encoded_byte_limit_is_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _image_bytes("JPEG")
    monkeypatch.setattr(adapter, "MAX_PLAN_RASTER_PNG_BYTES", 8)

    with pytest.raises(PlanRasterNormalizationError, match="PNG exceeds"):
        normalize_nvidia_plan_raster("image/jpeg", source)
