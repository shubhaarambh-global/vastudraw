from __future__ import annotations

import os
from collections.abc import Callable
from io import BytesIO
from uuid import UUID

from PIL import Image, ImageDraw

from ai_vastu.openrouter_http import (
    FALLBACK_REASONING_MODEL,
    PRIMARY_ARCHITECTURAL_MODEL,
)
from ai_vastu.plan_intake import (
    PlanRecognitionInput,
    PlanReferenceBlob,
    PlanReferenceKind,
    create_plan_intake_service,
)
from ai_vastu.provider_runtime import (
    DEFAULT_GEMINI_BUDGET,
    DEFAULT_OPENROUTER_BUDGET,
    ProviderRuntimeError,
    load_provider_budget,
)
from ai_vastu.requirements.providers import InterpretationInput
from ai_vastu.requirements.service import create_provider

GEMINI_MODEL = "gemini-3.1-flash-lite"
PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = UUID("33333333-3333-3333-3333-333333333333")
INTAKE_ID = UUID("44444444-4444-4444-4444-444444444444")


def _credential_status(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _check_openrouter_switches() -> None:
    for name in (
        "AI_VASTU_REQUIREMENTS_PROVIDER",
        "AI_VASTU_ARCHITECT_PROVIDER",
        "AI_VASTU_VASTU_PROVIDER",
        "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER",
        "AI_VASTU_REVISION_PROVIDER",
    ):
        if os.getenv(name, "").strip().lower() != "openrouter":
            raise RuntimeError("hybrid provider switches are invalid")
    load_provider_budget(
        os.environ,
        prefix="AI_VASTU_OPENROUTER",
        default=DEFAULT_OPENROUTER_BUDGET,
    )
def _check_gemini_switch() -> None:
    if os.getenv("AI_VASTU_PLAN_RECOGNITION_PROVIDER", "").strip().lower() != "gemini":
        raise RuntimeError("hybrid provider switches are invalid")
    model = os.getenv("AI_VASTU_PLAN_RECOGNITION_MODEL", "").strip()
    if model != GEMINI_MODEL:
        raise RuntimeError("hybrid provider switches are invalid")
    load_provider_budget(
        os.environ,
        prefix="AI_VASTU_GEMINI",
        default=DEFAULT_GEMINI_BUDGET,
    )


def _synthetic_png() -> bytes:
    image = Image.new("RGB", (320, 400), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 290, 370), outline="black", width=4)
    draw.line((160, 30, 160, 370), fill="black", width=3)
    draw.line((30, 200, 290, 200), fill="black", width=3)
    draw.text((125, 8), "NORTH", fill="black")
    draw.text((60, 100), "LIVING", fill="black")
    draw.text((190, 100), "KITCHEN", fill="black")
    draw.text((55, 280), "BEDROOM", fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _openrouter_probe() -> None:
    provider = create_provider()
    draft = provider.interpret(
        InterpretationInput(
            draft_id=DRAFT_ID,
            user_id=USER_ID,
            project_id=PROJECT_ID,
            prompt=(
                "Synthetic qualification brief: 30 x 50 ft, north road, "
                "two bedrooms and one-car parking. Preserve uncertainty."
            ),
            references=(),
        )
    )
    approved_models = {PRIMARY_ARCHITECTURAL_MODEL, FALLBACK_REASONING_MODEL}
    if draft.provider != "openrouter" or draft.model not in approved_models:
        raise RuntimeError("OpenRouter factory returned an unexpected provider or model")


def _gemini_probe() -> None:
    result = create_plan_intake_service().analyze(
        PlanRecognitionInput(
            project_id=PROJECT_ID,
            intake_id=INTAKE_ID,
            prompt="Synthetic qualification plan. Preserve uncertainty.",
            references=(
                PlanReferenceBlob(
                    filename="phase29c-live.png",
                    content_type="image/png",
                    kind=PlanReferenceKind.IMAGE,
                    data=_synthetic_png(),
                ),
            ),
        )
    )
    draft = result.recognition
    if draft.provider != "gemini" or draft.model != GEMINI_MODEL:
        raise RuntimeError("Gemini factory returned an unexpected provider or model")
    if (
        not draft.envelope.requires_confirmation
        or not draft.orientation.requires_confirmation
        or any(not room.requires_confirmation for room in draft.rooms)
    ):
        raise RuntimeError("Gemini observations did not remain confirmation-required")


def _run_probe(label: str, probe: Callable[[], None]) -> str:
    try:
        probe()
    except ProviderRuntimeError as exc:
        print(f"{label} FAIL category={exc.category.value}")
        return "FAIL"
    except Exception as exc:
        category = getattr(exc, "category", None)
        category_value = getattr(category, "value", None)
        if isinstance(category_value, str):
            print(f"{label} FAIL category={category_value}")
        else:
            print(f"{label} FAIL category={type(exc).__name__}")
        return "FAIL"
    print(f"{label} PASS_LIVE")
    return "PASS_LIVE"


def main() -> None:
    openrouter_ready = _credential_status("OPENROUTER_API_KEY")
    gemini_ready = _credential_status("GEMINI_API_KEY")

    if openrouter_ready:
        try:
            _check_openrouter_switches()
        except Exception:
            print("OPENROUTER FAIL category=configuration")
            openrouter_status = "FAIL"
        else:
            openrouter_status = _run_probe("OPENROUTER", _openrouter_probe)
    else:
        print("OPENROUTER BLOCKED_CREDENTIALS")
        openrouter_status = "BLOCKED_CREDENTIALS"

    if gemini_ready:
        try:
            _check_gemini_switch()
        except Exception:
            print("GEMINI FAIL category=configuration")
            gemini_status = "FAIL"
        else:
            gemini_status = _run_probe("GEMINI", _gemini_probe)
    else:
        print("GEMINI BLOCKED_CREDENTIALS")
        gemini_status = "BLOCKED_CREDENTIALS"

    statuses = (openrouter_status, gemini_status)
    if statuses != ("PASS_LIVE", "PASS_LIVE"):
        raise SystemExit(2 if "BLOCKED_CREDENTIALS" in statuses else 1)
    print("PHASE29C_LIVE PASS_LIVE")


if __name__ == "__main__":
    main()
