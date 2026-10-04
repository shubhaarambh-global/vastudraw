from __future__ import annotations

import io

import pypdfium2 as pdfium
import pytest

import ai_vastu.pdf_render_adapter as adapter
from ai_vastu.pdf_render_adapter import PdfiumPageRenderer, PdfRenderError


def _blank_pdf(page_count: int = 1, *, width: int = 300, height: int = 400) -> bytes:
    document = pdfium.PdfDocument.new()
    try:
        for _ in range(page_count):
            document.new_page(width, height)
        output = io.BytesIO()
        document.save(output)
        return output.getvalue()
    finally:
        document.close()


@pytest.mark.parametrize("data", [b"", b"not-a-pdf", b"%PDF-broken"])
def test_pdf_renderer_rejects_empty_or_malformed_input(data: bytes) -> None:
    with pytest.raises(PdfRenderError):
        PdfiumPageRenderer().render(filename="plan.pdf", data=data)


def test_pdf_renderer_rejects_encrypted_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adapter.pdfium_c, "FPDF_GetSecurityHandlerRevision", lambda _raw: 4)

    with pytest.raises(PdfRenderError, match="Encrypted PDFs"):
        PdfiumPageRenderer().render(filename="plan.pdf", data=_blank_pdf())


def test_pdf_renderer_rejects_page_count_before_rendering() -> None:
    oversized = _blank_pdf(adapter.MAX_PDF_PAGES + 1)

    with pytest.raises(PdfRenderError, match="page limit"):
        PdfiumPageRenderer().render(filename="plan.pdf", data=oversized)


def test_pdf_renderer_rejects_page_pixel_bounds_before_bitmap_allocation() -> None:
    oversized = _blank_pdf(width=3000, height=3000)

    with pytest.raises(PdfRenderError, match="image bounds"):
        PdfiumPageRenderer().render(filename="plan.pdf", data=oversized)
