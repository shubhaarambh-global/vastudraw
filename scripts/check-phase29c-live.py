from __future__ import annotations

import io
import os
from collections.abc import Callable
from uuid import UUID

from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

from ai_vastu.nvidia_nim_http import (
    PRIMARY_TEXT_MODEL,
    VISION_MODEL,
    NvidiaNimClient,
    NvidiaNimFailureStage,
    NvidiaNimModelPolicy,
    NvidiaNimRequestError,
)
from ai_vastu.pdf_render_adapter import PdfiumPageRenderer
from ai_vastu.plan_intake import (
    PlanRecognitionInput,
    PlanReferenceBlob,
    PlanReferenceKind,
    create_plan_intake_service,
)
from ai_vastu.provider_runtime import ProviderFailureCategory
from ai_vastu.requirements.providers import InterpretationInput
from ai_vastu.requirements.service import create_provider

PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = UUID("33333333-3333-3333-3333-333333333333")
INTAKE_ID = UUID("44444444-4444-4444-4444-444444444444")


def _policy() -> NvidiaNimModelPolicy:
    for name in (
        "AI_VASTU_REQUIREMENTS_PROVIDER",
        "AI_VASTU_ARCHITECT_PROVIDER",
        "AI_VASTU_VASTU_PROVIDER",
        "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER",
        "AI_VASTU_REVISION_PROVIDER",
        "AI_VASTU_PLAN_RECOGNITION_PROVIDER",
    ):
        if os.getenv(name, "").strip().lower() != "nvidia_nim":
            raise RuntimeError("NVIDIA NIM provider switches are invalid.")
    return NvidiaNimModelPolicy.from_environment()


def _input() -> InterpretationInput:
    return InterpretationInput(
        draft_id=DRAFT_ID,
        user_id=USER_ID,
        project_id=PROJECT_ID,
        prompt=(
            "30 x 50 ft plot with road explicitly on North, two bedrooms, "
            "one-car parking. Preserve uncertainty and require confirmation."
        ),
        references=(),
    )


def _primary(policy: NvidiaNimModelPolicy) -> None:
    if policy.text_chain != (PRIMARY_TEXT_MODEL,):
        raise RuntimeError("Active text policy is not primary-only.")
    draft = create_provider().interpret(_input())
    if draft.provider != "nvidia_nim" or draft.model != PRIMARY_TEXT_MODEL:
        raise RuntimeError("Primary model did not satisfy RequirementDraft.")


def _image(format_name: str) -> bytes:
    image = Image.new("RGB", (320, 400), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 290, 370), outline="black", width=4)
    draw.line((160, 30, 160, 370), fill="black", width=3)
    draw.line((30, 200, 290, 200), fill="black", width=3)
    draw.text((125, 8), "NORTH", fill="black")
    draw.text((60, 100), "LIVING", fill="black")
    draw.text((190, 100), "KITCHEN", fill="black")
    output = io.BytesIO()
    image.save(output, format=format_name)
    return output.getvalue()


def _pdf() -> bytes:
    output = io.BytesIO()
    document = canvas.Canvas(output, pagesize=(320, 400), invariant=True)
    document.drawString(125, 380, "NORTH")
    document.rect(30, 30, 260, 330)
    document.drawString(60, 250, "LIVING")
    document.drawString(190, 250, "KITCHEN")
    document.showPage()
    document.save()
    return output.getvalue()


def _pdf_local_render() -> None:
    pages = PdfiumPageRenderer().render(filename="plan.pdf", data=_pdf())
    if (
        len(pages) != 1
        or pages[0].content_type != "image/png"
        or not pages[0].data.startswith(b"\x89PNG\r\n\x1a\n")
    ):
        raise RuntimeError("Local PDF render qualification assertion failed.")


def _vision(kind: str, policy: NvidiaNimModelPolicy) -> None:
    cases = {
        "PNG": ("plan.png", "image/png", PlanReferenceKind.IMAGE, lambda: _image("PNG")),
        "JPEG": (
            "plan.jpg",
            "image/jpeg",
            PlanReferenceKind.IMAGE,
            lambda: _image("JPEG"),
        ),
        "PDF": ("plan.pdf", "application/pdf", PlanReferenceKind.PDF, _pdf),
    }
    filename, content_type, reference_kind, data_factory = cases[kind]
    data = data_factory()
    draft = create_plan_intake_service().recognize(
        PlanRecognitionInput(
            project_id=PROJECT_ID,
            intake_id=INTAKE_ID,
            prompt="Report only visible plan evidence and uncertainty.",
            references=(
                PlanReferenceBlob(
                    filename=filename,
                    content_type=content_type,
                    kind=reference_kind,
                    data=data,
                ),
            ),
        )
    )
    if draft.provider != "nvidia_nim" or draft.model != VISION_MODEL:
        raise RuntimeError("Vision provider/model provenance is invalid.")
    if draft.content_hash != draft.compute_content_hash():
        raise RuntimeError("Vision content hash is invalid.")
    if (
        not draft.envelope.requires_confirmation
        or not draft.orientation.requires_confirmation
        or any(not room.requires_confirmation for room in draft.rooms)
    ):
        raise RuntimeError("Vision observations are not confirmation-required.")


def _nvidia_failure(exc: BaseException) -> NvidiaNimRequestError | None:
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, NvidiaNimRequestError):
            return current
        current = current.__cause__
    return None


def _run(
    label: str,
    model_id: str,
    probe: Callable[[], None],
    *,
    success_status: str = "PASS_LIVE",
) -> str:
    try:
        probe()
    except Exception as exc:
        failure = _nvidia_failure(exc)
        if failure is not None:
            fields = (
                f"{label} FAIL role={label.removeprefix('NVIDIA ').lower().replace(' ', '_')} "
                f"model={failure.model_id or model_id} category={failure.category.value} "
                f"stage={failure.stage.value} attempts={failure.attempts}"
            )
            if failure.http_status is not None:
                fields += f" http_status={failure.http_status}"
            print(fields)
        else:
            print(
                f"{label} FAIL "
                f"role={label.removeprefix('NVIDIA ').lower().replace(' ', '_')} "
                f"model={model_id} category={ProviderFailureCategory.INVALID_RESPONSE.value} "
                f"stage={NvidiaNimFailureStage.FINAL_QUALIFICATION_ASSERTION.value} "
                "attempts=1"
            )
        return "FAIL"
    print(f"{label} {success_status} model={model_id}")
    return success_status


def main() -> None:
    pdf_local_status = _run(
        "NVIDIA VISION PDF LOCAL RENDER",
        "local_png_renderer",
        _pdf_local_render,
        success_status="PASS_LOCAL",
    )
    if not os.getenv("NVIDIA_API_KEY", "").strip():
        for label in (
            "NVIDIA MODEL INVENTORY",
            "NVIDIA TEXT PRIMARY", "NVIDIA VISION PNG",
            "NVIDIA VISION JPEG", "NVIDIA VISION PDF-PATH",
        ):
            print(f"{label} BLOCKED_CREDENTIALS")
        print("PHASE29C NVIDIA_NIM BLOCKED_CREDENTIALS")
        raise SystemExit(2)
    try:
        policy = _policy()
    except Exception:
        print("PHASE29C NVIDIA_NIM FAIL category=configuration")
        raise SystemExit(1) from None
    try:
        verified = NvidiaNimClient.from_environment().verify_pinned_models_available()
    except NvidiaNimRequestError as exc:
        fields = (
            "NVIDIA MODEL INVENTORY FAIL role=model_inventory "
            f"model=active_policy category={exc.category.value} "
            f"stage={exc.stage.value} attempts={exc.attempts}"
        )
        if exc.http_status is not None:
            fields += f" http_status={exc.http_status}"
        print(fields)
        raise SystemExit(1) from None
    except Exception:
        print("NVIDIA MODEL INVENTORY FAIL category=configuration")
        raise SystemExit(1) from None
    if verified != (PRIMARY_TEXT_MODEL, VISION_MODEL):
        print("NVIDIA MODEL INVENTORY FAIL category=invalid_response")
        raise SystemExit(1)
    print(
        "NVIDIA MODEL INVENTORY PASS_LIVE verified=2 "
        f"text_primary={PRIMARY_TEXT_MODEL} vision={VISION_MODEL}"
    )
    probes = (
        ("NVIDIA TEXT PRIMARY", PRIMARY_TEXT_MODEL, lambda: _primary(policy), "PASS_LIVE"),
        ("NVIDIA VISION PNG", VISION_MODEL, lambda: _vision("PNG", policy), "PASS_LIVE"),
        ("NVIDIA VISION JPEG", VISION_MODEL, lambda: _vision("JPEG", policy), "PASS_LIVE"),
        ("NVIDIA VISION PDF-PATH", VISION_MODEL, lambda: _vision("PDF", policy), "PASS_LIVE"),
    )
    results = [pdf_local_status]
    for label, model_id, probe, success_status in probes:
        results.append(
            _run(label, model_id, probe, success_status=success_status)
        )
    expected = ("PASS_LOCAL", *("PASS_LIVE" for _ in probes))
    if tuple(results) != expected:
        print("PHASE29C NVIDIA_NIM FAIL required_stages=incomplete")
        raise SystemExit(1)
    print("PHASE29C NVIDIA_NIM REQUIREMENTS_VISION PASS_LIVE")


if __name__ == "__main__":
    main()
