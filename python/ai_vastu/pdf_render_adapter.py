from __future__ import annotations

import io
import time
from dataclasses import dataclass
from typing import Protocol

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

MAX_PDF_INPUT_BYTES = 32 * 1024 * 1024
MAX_PDF_PAGES = 8
MAX_PAGE_DIMENSION_PX = 4096
MAX_PAGE_PIXELS = 16_000_000
MAX_TOTAL_PIXELS = 48_000_000
MAX_PAGE_PNG_BYTES = 12 * 1024 * 1024
MAX_TOTAL_PNG_BYTES = 32 * 1024 * 1024
PDF_RENDER_DPI = 144
PDF_RENDER_TIMEOUT_SECONDS = 30.0
_PDF_POINTS_PER_INCH = 72.0


class PdfRenderError(ValueError):
    """A sanitized, fail-closed local PDF rendering failure."""


@dataclass(frozen=True, slots=True)
class RenderedPdfPage:
    page_number: int
    filename: str
    content_type: str
    data: bytes


class PdfPageRenderer(Protocol):
    def render(self, *, filename: str, data: bytes) -> tuple[RenderedPdfPage, ...]: ...


class PdfiumPageRenderer:
    """Render bounded PDF pages locally; provider boundaries receive PNG only."""

    def render(self, *, filename: str, data: bytes) -> tuple[RenderedPdfPage, ...]:
        if not data or len(data) > MAX_PDF_INPUT_BYTES:
            raise PdfRenderError("PDF is empty or exceeds the local rendering limit.")
        if not data.startswith(b"%PDF-"):
            raise PdfRenderError("PDF signature is invalid.")

        started = time.monotonic()
        document: pdfium.PdfDocument | None = None
        try:
            document = pdfium.PdfDocument(data)
            if pdfium_c.FPDF_GetSecurityHandlerRevision(document.raw) >= 0:
                raise PdfRenderError("Encrypted PDFs are not accepted.")

            page_count = len(document)
            if page_count < 1:
                raise PdfRenderError("PDF contains no pages.")
            if page_count > MAX_PDF_PAGES:
                raise PdfRenderError("PDF exceeds the local page limit.")

            rendered: list[RenderedPdfPage] = []
            total_pixels = 0
            total_encoded_bytes = 0
            scale = PDF_RENDER_DPI / _PDF_POINTS_PER_INCH
            for index in range(page_count):
                self._check_deadline(started)
                page = document[index]
                bitmap = None
                image = None
                try:
                    width_points, height_points = page.get_size()
                    width_px = max(1, round(width_points * scale))
                    height_px = max(1, round(height_points * scale))
                    pixels = width_px * height_px
                    if (
                        width_px > MAX_PAGE_DIMENSION_PX
                        or height_px > MAX_PAGE_DIMENSION_PX
                        or pixels > MAX_PAGE_PIXELS
                    ):
                        raise PdfRenderError("PDF page exceeds local image bounds.")
                    total_pixels += pixels
                    if total_pixels > MAX_TOTAL_PIXELS:
                        raise PdfRenderError("PDF exceeds the total rendered-pixel limit.")

                    bitmap = page.render(scale=scale)
                    image = bitmap.to_pil()
                    output = io.BytesIO()
                    image.save(output, format="PNG", optimize=True)
                    encoded = output.getvalue()
                    if len(encoded) > MAX_PAGE_PNG_BYTES:
                        raise PdfRenderError("Rendered PDF page exceeds the encoded-byte limit.")
                    total_encoded_bytes += len(encoded)
                    if total_encoded_bytes > MAX_TOTAL_PNG_BYTES:
                        raise PdfRenderError("PDF exceeds the total encoded-byte limit.")
                    rendered.append(
                        RenderedPdfPage(
                            page_number=index + 1,
                            filename=f"{filename}#page-{index + 1}.png",
                            content_type="image/png",
                            data=encoded,
                        )
                    )
                finally:
                    if image is not None:
                        image.close()
                    if bitmap is not None:
                        bitmap.close()
                    page.close()
                self._check_deadline(started)
            return tuple(rendered)
        except PdfRenderError:
            raise
        except Exception as exc:
            raise PdfRenderError("PDF could not be rendered locally.") from exc
        finally:
            if document is not None:
                document.close()

    @staticmethod
    def _check_deadline(started: float) -> None:
        if time.monotonic() - started > PDF_RENDER_TIMEOUT_SECONDS:
            raise PdfRenderError("PDF rendering exceeded the local time limit.")


def render_pdf_pages(*, filename: str, data: bytes) -> tuple[RenderedPdfPage, ...]:
    return PdfiumPageRenderer().render(filename=filename, data=data)
