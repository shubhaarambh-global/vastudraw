from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_api() -> None:
    path = ROOT / "apps/api/app/main.py"
    text = path.read_text(encoding="utf-8")

    if "from fastapi.middleware.cors import CORSMiddleware" not in text:
        text = text.replace(
            "from fastapi import Depends, FastAPI, HTTPException, Request, status\n",
            "from fastapi import Depends, FastAPI, HTTPException, Request, status\n"
            "from fastapi.middleware.cors import CORSMiddleware\n",
            1,
        )

    text = text.replace('version="0.16.0"', 'version="0.17.0"')
    text = text.replace('"phase": "16"', '"phase": "17"')

    marker = "    app.state.project_service = ProjectRevisionService(project_repository)\n"
    cors = (
        "    allowed_origins = tuple(\n"
        "        origin.strip()\n"
        "        for origin in os.environ.get(\n"
        '            "AI_VASTU_WEB_ORIGINS",\n'
        '            "http://localhost:3000,http://127.0.0.1:3000",\n'
        '        ).split(",")\n'
        "        if origin.strip()\n"
        "    )\n"
        "    app.add_middleware(\n"
        "        CORSMiddleware,\n"
        "        allow_origins=list(allowed_origins),\n"
        "        allow_credentials=False,\n"
        '        allow_methods=["GET", "POST"],\n'
        '        allow_headers=["Content-Type"],\n'
        "    )\n"
    )
    if "AI_VASTU_WEB_ORIGINS" not in text:
        if marker not in text:
            raise SystemExit("Could not locate API middleware insertion point.")
        text = text.replace(marker, marker + cors, 1)

    path.write_text(text, encoding="utf-8")


def patch_health_test() -> None:
    path = ROOT / "apps/api/tests/test_health.py"
    text = path.read_text(encoding="utf-8")
    for phase in ("11", "15", "16"):
        text = text.replace(f'"phase": "{phase}"', '"phase": "17"')
    path.write_text(text, encoding="utf-8")


def patch_page() -> None:
    path = ROOT / "apps/web/src/components/editor/DemoEditorPage.tsx"
    text = path.read_text(encoding="utf-8")
    if 'import type { PlanDocument } from "@ai-vastu/contracts";' not in text:
        text = text.replace(
            'import { useState } from "react";\n',
            'import type { PlanDocument } from "@ai-vastu/contracts";\n'
            'import { useState } from "react";\n',
            1,
        )
    if 'import { ProjectWorkflowPanel } from "./ProjectWorkflowPanel.tsx";' not in text:
        text = text.replace(
            'import { PlanEditor } from "./PlanEditor.tsx";\n',
            'import { PlanEditor } from "./PlanEditor.tsx";\n'
            'import { ProjectWorkflowPanel } from "./ProjectWorkflowPanel.tsx";\n',
            1,
        )
    if "useState<PlanDocument>(demoDocument)" not in text:
        text = text.replace(
            "  const [submitted, setSubmitted] = useState<EditorChangeSet | null>(null);\n",
            "  const [submitted, setSubmitted] = useState<EditorChangeSet | null>(null);\n"
            "  const [document, setDocument] = useState<PlanDocument>(demoDocument);\n",
            1,
        )
    text = text.replace(
        "revision <code>{demoDocument.revision_id}</code>.",
        "revision <code>{document.revision_id}</code>.",
    )
    text = text.replace(
        "      <PlanEditor document={demoDocument} onSubmitChangeSet={setSubmitted} />",
        (
            "      <ProjectWorkflowPanel document={document} "
            "onDocumentLoaded={setDocument} />\n"
            "      <PlanEditor key={document.revision_id} document={document} "
            "onSubmitChangeSet={setSubmitted} />"
        ),
        1,
    )
    text = text.replace("Phase 12 · interactive editor", "Phase 17 · web/API project workflow")
    path.write_text(text, encoding="utf-8")


def patch_web_package() -> None:
    path = ROOT / "apps/web/package.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["scripts"]["test"] = (
        "node --experimental-strip-types --test "
        "./src/bootstrap.test.mjs ./src/editor/math.test.ts ./src/editor/history.test.ts "
        "./src/editor/commands.test.ts ./src/api/client.test.ts"
    )
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def patch_readiness() -> None:
    path = ROOT / "python/ai_vastu/release/readiness.py"
    text = path.read_text(encoding="utf-8")
    old = (
        "            _gate(\n"
        '                "WEB_API_WORKFLOW_NOT_IMPLEMENTED",\n'
        "                ReleaseGateStatus.BLOCKER,\n"
        '                "The web editor is not yet bound to project generation/save/load '
        'API flows.",\n'
        "            ),\n"
    )
    new = (
        "            _gate(\n"
        '                "WEB_API_WORKFLOW_IMPLEMENTED",\n'
        "                ReleaseGateStatus.PASS,\n"
        "                (\n"
        '                    "The web editor is bound to project create/load/save and "\n'
        '                    "architectural generation API flows."\n'
        "                ),\n"
        '                "project_api=create/load/save",\n'
        '                "generation_api=POST /generation/architectural",\n'
        '                "authoritative_units=mm",\n'
        "            ),\n"
    )
    if old in text:
        text = text.replace(old, new, 1)
    elif "WEB_API_WORKFLOW_IMPLEMENTED" not in text:
        raise SystemExit("Could not locate Phase 16 web/API release blocker.")
    path.write_text(text, encoding="utf-8")


def patch_release_expectations() -> None:
    for relative in ("scripts/check-production-mvp.py", "tests/release/test_readiness.py"):
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        text = text.replace('    "WEB_API_WORKFLOW_NOT_IMPLEMENTED",\n', "")
        text = text.replace('        "WEB_API_WORKFLOW_NOT_IMPLEMENTED",\n', "")
        text = text.replace('            "WEB_API_WORKFLOW_NOT_IMPLEMENTED",\n', "")
        text = text.replace("Phase 16 expected", "Phase 17 expected")
        if relative == "tests/release/test_readiness.py":
            text = text.replace(
                "            )\n\n\ndef test_readiness",
                "        )\n\n\ndef test_readiness",
            )
        path.write_text(text, encoding="utf-8")

    policy = ROOT / "tests/test_phase16_policy.py"
    if policy.exists():
        text = policy.read_text(encoding="utf-8")
        text = text.replace(
            '    assert "WEB_API_WORKFLOW_NOT_IMPLEMENTED" in source\n',
            '    assert "WEB_API_WORKFLOW_IMPLEMENTED" in source\n',
        )
        policy.write_text(text, encoding="utf-8")


def patch_package() -> None:
    path = ROOT / "package.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    scripts = payload["scripts"]
    scripts["web-api:check"] = "python scripts/check-web-api-workflow.py"
    validate = scripts["validate"]
    if "pnpm web-api:check" not in validate:
        needle = "pnpm generation:check && pnpm mvp:check"
        replacement = "pnpm generation:check && pnpm web-api:check && pnpm mvp:check"
        if needle not in validate:
            raise SystemExit("Could not locate Phase 16 validation insertion point.")
        scripts["validate"] = validate.replace(needle, replacement, 1)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def patch_env() -> None:
    path = ROOT / ".env.example"
    text = path.read_text(encoding="utf-8")
    additions = (
        "\n# Phase 17 browser/API integration\n"
        "NEXT_PUBLIC_AI_VASTU_API_BASE_URL=http://127.0.0.1:8000\n"
        "AI_VASTU_WEB_ORIGINS=http://localhost:3000,http://127.0.0.1:3000\n"
    )
    if "NEXT_PUBLIC_AI_VASTU_API_BASE_URL" not in text:
        text = text.rstrip() + "\n" + additions
    path.write_text(text, encoding="utf-8")


def patch_web_styles() -> None:
    path = ROOT / "apps/web/src/app/globals.css"
    text = path.read_text(encoding="utf-8")
    marker = ".workflow-panel"
    if marker in text:
        return
    text += """

.workflow-panel {
  margin: 0 0 18px;
  padding: 18px;
  border: 1px solid #d0d5dd;
  border-radius: 12px;
  background: #ffffff;
}

.workflow-heading,
.workflow-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.workflow-heading {
  justify-content: space-between;
  margin-bottom: 14px;
}

.workflow-heading h2 {
  margin: 0;
}

.workflow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.workflow-grid label,
.workflow-json {
  display: grid;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
}

.workflow-grid input,
.workflow-json textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  padding: 9px 10px;
  font: inherit;
  background: #ffffff;
}

.workflow-actions {
  margin: 10px 0;
}

.workflow-result {
  max-height: 320px;
  overflow: auto;
  padding: 12px;
  border-radius: 8px;
  background: #101828;
  color: #f2f4f7;
  font-size: 11px;
}
"""
    path.write_text(text, encoding="utf-8")


def patch_docs() -> None:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    heading = "# Phase 17 — Web/API project workflow"
    if heading not in text:
        text = text.rstrip() + "\n\n" + (ROOT / "PHASE17.md").read_text(encoding="utf-8") + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_api()
    patch_health_test()
    patch_page()
    patch_web_package()
    patch_readiness()
    patch_release_expectations()
    patch_package()
    patch_env()
    patch_web_styles()
    patch_docs()
    print("Phase 17 integration applied.")


if __name__ == "__main__":
    main()
