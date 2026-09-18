from __future__ import annotations

import base64
import os

from ai_vastu.openrouter_http import (
    OpenRouterClient,
    OpenRouterModelPolicy,
    image_url_part,
)

key = os.getenv("OPENROUTER_API_KEY", "").strip()
if not key:
    raise SystemExit(
        "OPENROUTER_API_KEY is not loaded in this terminal. "
        "Load it securely, then rerun pnpm phase26:openrouter-live."
    )

client = OpenRouterClient(api_key=key)
policy = OpenRouterModelPolicy.from_environment()

def validate_ok(parsed: dict[str, object], model: str) -> str:
    if parsed.get("ok") is not True:
        raise ValueError(f"{model} did not return {{\"ok\": true}}.")
    return model

def probe(label: str, model: str, content: object) -> None:
    used = client.complete_validated_json(
        messages=(
            {
                "role": "system",
                "content": "Return exactly one JSON object: {\"ok\": true}.",
            },
            {"role": "user", "content": content},
        ),
        models=(model,),
        validator=validate_ok,
        temperature=0.0,
    )
    print(f"{label}: OK ({used})")

probe("primary architectural brain", policy.primary, "Return the requested JSON.")

probe("fallback reasoning", policy.fallback, "Return the requested JSON.")

png = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZKjY"
    "AAAAASUVORK5CYII="
)
probe(
    "vision plan reader",
    policy.vision,
    [
        {"type": "text", "text": "Inspect this tiny image and return the requested JSON."},
        image_url_part("image/png", png),
    ],
)

print("OpenRouter live qualification passed for all three pinned free models.")
