from __future__ import annotations

import json
import os
from io import BytesIO
from uuid import uuid4

import httpx
from PIL import Image, ImageDraw

from ai_vastu.openrouter_http import OpenRouterModelPolicy
from ai_vastu.plan_intake import (
    PlanRecognitionInput,
    PlanReferenceBlob,
    PlanReferenceKind,
    create_plan_intake_service,
)

DEEPSEEK = "deepseek/deepseek-v4-flash-0731:free"
NEMOTRON = "nvidia/nemotron-3-ultra-550b-a55b:free"
GEMINI = "gemini-3.1-flash-lite"


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is required for Phase 28 live qualification.")
    return value


def check_switches() -> None:
    for name in (
        "AI_VASTU_REQUIREMENTS_PROVIDER",
        "AI_VASTU_ARCHITECT_PROVIDER",
        "AI_VASTU_VASTU_PROVIDER",
        "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER",
        "AI_VASTU_REVISION_PROVIDER",
    ):
        if os.getenv(name, "").strip().lower() != "openrouter":
            raise SystemExit(f"{name} must equal 'openrouter'.")

    plan_provider = os.getenv("AI_VASTU_PLAN_RECOGNITION_PROVIDER", "").strip().lower()
    if plan_provider != "gemini":
        raise SystemExit("AI_VASTU_PLAN_RECOGNITION_PROVIDER must equal 'gemini'.")


def qualify_deepseek() -> None:
    api_key = required("OPENROUTER_API_KEY")
    policy = OpenRouterModelPolicy.from_environment()

    if policy.primary != DEEPSEEK:
        raise SystemExit(f"Unexpected primary model: {policy.primary}")
    if policy.fallback != NEMOTRON:
        raise SystemExit(f"Unexpected legacy fallback model: {policy.fallback}")

    payload = {
        "model": DEEPSEEK,
        "messages": [
            {
                "role": "user",
                "content": "Return the required JSON for Vastu-AI qualification.",
            }
        ],
        "temperature": 0,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "phase28_text_probe",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "ok": {"type": "boolean"},
                        "role": {
                            "type": "string",
                            "enum": ["text_reasoning"],
                        },
                    },
                    "required": ["ok", "role"],
                    "additionalProperties": False,
                },
            },
        },
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=90.0) as client:
        response = client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
        )

    if response.status_code != 200:
        raise SystemExit(
            f"DeepSeek qualification failed: HTTP {response.status_code}: {response.text[:1000]}"
        )

    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise SystemExit("DeepSeek response contained no choices.")

    raw = choices[0].get("message", {}).get("content", "")
    parsed = json.loads(raw)
    if parsed.get("ok") is not True:
        raise SystemExit(f"Unexpected DeepSeek response: {parsed}")

    print(f"text reasoning: OK ({DEEPSEEK})")


def qualify_gemini() -> None:
    required("GEMINI_API_KEY")

    model = os.getenv("AI_VASTU_PLAN_RECOGNITION_MODEL", GEMINI).strip()
    if model != GEMINI:
        raise SystemExit(f"Unexpected Gemini model: {model}")

    image = Image.new("RGB", (640, 800), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((70, 70, 570, 730), outline="black", width=6)
    draw.line((320, 70, 320, 730), fill="black", width=5)
    draw.line((70, 400, 570, 400), fill="black", width=5)
    draw.text((145, 220), "LIVING", fill="black")
    draw.text((400, 220), "KITCHEN", fill="black")
    draw.text((135, 560), "BEDROOM", fill="black")
    draw.text((390, 560), "BEDROOM", fill="black")
    draw.text((292, 25), "NORTH", fill="black")
    draw.text((285, 745), "30 FT", fill="black")
    draw.text((580, 380), "50 FT", fill="black")

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    project_id = uuid4()
    intake_id = uuid4()

    request = PlanRecognitionInput(
        project_id=project_id,
        intake_id=intake_id,
        prompt=(
            "Phase 28 live qualification. Read only explicit information and preserve uncertainty."
        ),
        references=(
            PlanReferenceBlob(
                filename="phase28-live.png",
                content_type="image/png",
                kind=PlanReferenceKind.IMAGE,
                data=buffer.getvalue(),
            ),
        ),
    )

    draft = create_plan_intake_service().recognize(request)

    if draft.project_id != project_id:
        raise SystemExit("Gemini changed project identity.")
    if draft.intake_id != intake_id:
        raise SystemExit("Gemini changed intake identity.")
    if draft.provider != "gemini":
        raise SystemExit(f"Unexpected provider: {draft.provider}")
    if draft.model != GEMINI:
        raise SystemExit(f"Unexpected Gemini model: {draft.model}")
    if not draft.content_hash:
        raise SystemExit("Gemini draft has no content hash.")
    if not draft.rooms:
        raise SystemExit("Gemini recognized no rooms.")

    print(f"plan recognition: OK ({GEMINI})")
    print(f"rooms recognized: {len(draft.rooms)}")
    print(f"content hash: {draft.content_hash}")


check_switches()
qualify_deepseek()
qualify_gemini()
print("PHASE 28 HYBRID AI LIVE QUALIFICATION PASSED")
