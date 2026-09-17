from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_package() -> None:
    path = ROOT / "package.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    scripts = payload["scripts"]
    scripts["phase26c:check"] = "python scripts/check-phase26c.py"

    validate = scripts["validate"]
    marker = "pnpm phase26b5:check"
    if "pnpm phase26c:check" not in validate:
        if marker not in validate:
            raise SystemExit("Could not find phase26b5 validation marker.")
        validate = validate.replace(
            marker,
            marker + " && pnpm phase26c:check",
            1,
        )
        scripts["validate"] = validate

    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def patch_generation_route() -> None:
    path = ROOT / "apps/web/src/app/generation/page.tsx"
    text = path.read_text(encoding="utf-8")

    if "Phase26CGenerationPage" in text:
        return

    old_import = (
        "import { GenerationWorkspacePage } "
        'from "../../components/generation/GenerationWorkspacePage.tsx";'
    )
    if old_import not in text:
        old_import = (
            "import { GenerationWorkspacePage } "
            'from "../../components/generation/GenerationWorkspacePage";'
        )

    if old_import not in text:
        raise SystemExit("Could not identify current /generation page component import.")

    new_import = (
        "import { Phase26CGenerationPage } "
        'from "../../components/generation/Phase26CGenerationPage.tsx";'
    )
    text = text.replace(old_import, new_import, 1)
    text = text.replace("<GenerationWorkspacePage />", "<Phase26CGenerationPage />", 1)
    path.write_text(text, encoding="utf-8")


def patch_global_css() -> None:
    path = ROOT / "apps/web/src/app/globals.css"
    text = path.read_text(encoding="utf-8")
    marker = '@import "../components/generation/phase26c.css";'
    if marker not in text:
        text = marker + "\n" + text
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_package()
    patch_generation_route()
    patch_global_css()
    print("Phase 26C.1 overlay applied.")


if __name__ == "__main__":
    main()
