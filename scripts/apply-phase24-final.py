from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_generation_adapter() -> None:
    path = ROOT / "python/ai_vastu/requirements/generation_adapter.py"
    text = path.read_text(encoding="utf-8")
    marker = "    width = confirmed.plot_width_mm\n    depth = confirmed.plot_depth_mm\n"
    guard = (
        "    if confirmed.floor_count != 1:\n"
        "        raise UnsupportedConfirmedRequirement(\n"
        "            \"Commercial MVP currently supports exactly one generated floor.\"\n"
        "        )\n"
        "    for room in confirmed.rooms:\n"
        "        if room.floor_preference not in {None, 0}:\n"
        "            raise UnsupportedConfirmedRequirement(\n"
        "                \"Commercial MVP cannot silently drop an upper-floor preference.\"\n"
        "            )\n\n"
    )
    if guard not in text:
        if marker not in text:
            raise SystemExit("Could not locate Phase 24B compiler entry point.")
        text = text.replace(marker, guard + marker, 1)
        path.write_text(text, encoding="utf-8")


def patch_package_json() -> None:
    path = ROOT / "package.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    scripts = data.setdefault("scripts", {})
    scripts["phase24:check"] = "python scripts/check-phase24-final.py"

    validate = scripts.get("validate")
    if not isinstance(validate, str):
        raise SystemExit("Root package.json has no validate script.")

    if "pnpm phase24:check" not in validate:
        marker = "pnpm confirmed-generation:check"
        if marker in validate:
            validate = validate.replace(
                marker,
                marker + " && pnpm phase24:check",
                1,
            )
        else:
            validate = "pnpm phase24:check && " + validate
    scripts["validate"] = validate

    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


patch_generation_adapter()
patch_package_json()
print("Phase 24 final canonical generation binding integrated.")
