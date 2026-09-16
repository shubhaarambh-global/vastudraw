from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_package_json() -> None:
    path = ROOT / "package.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    scripts = payload["scripts"]
    scripts["mvp:check"] = "python scripts/check-production-mvp.py"
    scripts["mvp:release"] = "python scripts/assert-production-release.py"

    validate = scripts["validate"]
    if "pnpm mvp:check" not in validate:
        marker = "pnpm dwg:check && "
        if marker not in validate:
            raise SystemExit("Could not locate Phase 14 dwg:check in validate script.")
        validate = validate.replace(marker, marker + "pnpm mvp:check && ", 1)
        scripts["validate"] = validate

    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def patch_api() -> None:
    path = ROOT / "apps/api/app/main.py"
    text = path.read_text(encoding="utf-8")

    if "from pathlib import Path" not in text:
        text = text.replace("import os\n", "import os\nfrom pathlib import Path\n", 1)

    release_import = (
        "from ai_vastu.release import (\n"
        "    ProductionReadinessReport,\n"
        "    evaluate_production_mvp_readiness,\n"
        ")\n"
    )
    if "from ai_vastu.release import" not in text:
        marker = "from ai_vastu.projects import (\n"
        index = text.find(marker)
        if index == -1:
            raise SystemExit("Could not locate projects import in API main.py.")
        text = text[:index] + release_import + text[index:]

    text = text.replace(
        'FastAPI(title="AI Vastu Architect API", version="0.11.0")',
        'FastAPI(title="AI Vastu Architect API", version="0.15.0")',
    )
    text = text.replace('"phase": "11"', '"phase": "15"')

    route = (
        "\n    @app.get(\n"
        "        \"/system/release-readiness\",\n"
        "        response_model=ProductionReadinessReport,\n"
        "        tags=[\"system\"],\n"
        "    )\n"
        "    def release_readiness() -> ProductionReadinessReport:\n"
        "        repository_root = Path(__file__).resolve().parents[3]\n"
        "        return evaluate_production_mvp_readiness(repository_root)\n"
    )
    if '"/system/release-readiness"' not in text:
        marker = "\n    @app.post(\n        \"/projects\","
        index = text.find(marker)
        if index == -1:
            raise SystemExit("Could not locate API project routes insertion point.")
        text = text[:index] + route + text[index:]

    path.write_text(text, encoding="utf-8")


def append_once(path: Path, heading: str, content: str) -> None:
    text = path.read_text(encoding="utf-8")
    if heading in text:
        return
    path.write_text(text.rstrip() + "\n\n" + content.strip() + "\n", encoding="utf-8")


def patch_docs() -> None:
    append_once(
        ROOT / "README.md",
        "## Phase 15 — Production MVP release gate",
        '''## Phase 15 — Production MVP release gate

Phase 15 adds a deterministic, fail-closed public-MVP release-readiness report. The
engineering CI gate verifies that the readiness mechanism is stable; the separate
`pnpm mvp:release` promotion command exits non-zero while blockers remain.

The current repository is intentionally **BLOCKED** for public production release.
The principal blockers are the still-DRAFT/empty Vastu Specification v1, missing
project authorization, absence of the planned production persistence adapter, and
missing end-to-end generation/API/editor wiring. This is a truthful release gate,
not a claim that those capabilities already exist.''',
    )
    append_once(
        ROOT / "THIRD_PARTY.md",
        "## Phase 15 dependency note",
        '''## Phase 15 dependency note

Phase 15 introduces no new third-party runtime dependency. It composes existing
repository metadata and subsystem contracts into a deterministic release-readiness
gate.''',
    )


def main() -> None:
    patch_package_json()
    patch_api()
    patch_docs()
    print("Phase 15 repository integration applied.")


if __name__ == "__main__":
    main()
