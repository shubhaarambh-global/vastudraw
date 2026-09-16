from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise SystemExit(f"Could not locate expected text in {path}: {old[:100]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_main() -> None:
    path = ROOT / "apps/api/app/main.py"
    text = path.read_text(encoding="utf-8")

    if "from ai_vastu.generation import" not in text:
        marker = "from ai_vastu.plan_schema import PLAN_SCHEMA_VERSION, PlanDocument\n"
        block = (
            "from ai_vastu.generation import (\n"
            "    ArchitecturalGenerationRequest,\n"
            "    ArchitecturalGenerationResult,\n"
            "    GenerationInputError,\n"
            "    generate_architectural_plan,\n"
            ")\n"
        )
        if marker not in text:
            raise SystemExit("Could not locate generation import insertion point in API main.")
        text = text.replace(marker, block + marker, 1)

    text = text.replace('version="0.15.0"', 'version="0.16.0"')
    text = text.replace('"phase": "15"', '"phase": "16"')
    text = text.replace('"phase": "11"', '"phase": "16"')

    route_marker = "    @app.post(\n        \"/projects\",\n"
    if '"/generation/architectural"' not in text:
        route = (
            '    @app.post(\n'
            '        "/generation/architectural",\n'
            '        response_model=ArchitecturalGenerationResult,\n'
            '        tags=["generation"],\n'
            '    )\n'
            '    async def generate_architectural(\n'
            '        request: Request,\n'
            '    ) -> ArchitecturalGenerationResult:\n'
            '        try:\n'
            '            payload = ArchitecturalGenerationRequest.model_validate_json(\n'
            '                await request.body()\n'
            '            )\n'
            '            return generate_architectural_plan(payload)\n'
            '        except (GenerationInputError, ValueError) as exc:\n'
            '            raise HTTPException(\n'
            '                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,\n'
            '                detail=str(exc),\n'
            '            ) from exc\n\n'
        )
        if route_marker not in text:
            raise SystemExit("Could not locate API route insertion point.")
        text = text.replace(route_marker, route + route_marker, 1)

    path.write_text(text, encoding="utf-8")


def patch_readiness() -> None:
    path = ROOT / "python/ai_vastu/release/readiness.py"
    text = path.read_text(encoding="utf-8")

    if "from ai_vastu.generation import GENERATION_PIPELINE_VERSION" not in text:
        marker = "from ai_vastu.dwg import DwgTargetVersion, preferred_production_candidate\n"
        text = text.replace(
            marker,
            marker + "from ai_vastu.generation import GENERATION_PIPELINE_VERSION\n",
            1,
        )

    old = (
        '            _gate(\n'
        '                "GENERATION_API_NOT_IMPLEMENTED",\n'
        '                ReleaseGateStatus.BLOCKER,\n'
        '                (\n'
        '                    "The API does not yet expose the deterministic planning '
        'pipeline as a "\n'
        '                    "product workflow."\n'
        '                ),\n'
        '            ),\n'
    )
    new = (
        '            _gate(\n'
        '                "GENERATION_API_IMPLEMENTED",\n'
        '                ReleaseGateStatus.PASS,\n'
        '                (\n'
        '                    "The deterministic architectural planning pipeline is "\n'
        '                    "exposed as an API workflow."\n'
        '                ),\n'
        '                f"pipeline_version={GENERATION_PIPELINE_VERSION}",\n'
        '                "endpoint=POST /generation/architectural",\n'
        '                "vastu_rules_applied=false",\n'
        '            ),\n'
    )
    if old in text:
        text = text.replace(old, new, 1)
    elif "GENERATION_API_IMPLEMENTED" not in text:
        raise SystemExit("Could not locate Phase 15 generation readiness blocker.")

    path.write_text(text, encoding="utf-8")


def patch_release_expectations() -> None:
    for relative in (
        "scripts/check-production-mvp.py",
        "tests/release/test_readiness.py",
    ):
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        text = text.replace('    "GENERATION_API_NOT_IMPLEMENTED",\n', "")
        text = text.replace("Phase 15 expected", "Phase 16 expected")
        path.write_text(text, encoding="utf-8")

    policy = ROOT / "tests/test_phase15_policy.py"
    text = policy.read_text(encoding="utf-8")
    text = text.replace(
        '    assert "GENERATION_API_NOT_IMPLEMENTED" in source\n',
        '    assert "WEB_API_WORKFLOW_NOT_IMPLEMENTED" in source\n',
    )
    policy.write_text(text, encoding="utf-8")


def patch_health_test() -> None:
    path = ROOT / "apps/api/tests/test_health.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace('"phase": "11"', '"phase": "16"')
    text = text.replace('"phase": "15"', '"phase": "16"')
    path.write_text(text, encoding="utf-8")


def patch_package() -> None:
    path = ROOT / "package.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    scripts = payload["scripts"]
    scripts["generation:check"] = "python scripts/check-generation-api.py"
    validate = scripts["validate"]
    if "pnpm generation:check" not in validate:
        needle = "pnpm dwg:check && pnpm mvp:check"
        replacement = "pnpm dwg:check && pnpm generation:check && pnpm mvp:check"
        if needle not in validate:
            raise SystemExit("Could not locate validate insertion point in package.json.")
        scripts["validate"] = validate.replace(needle, replacement, 1)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def patch_readme() -> None:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    if "## Phase 16 — Deterministic architectural generation API" in text:
        return
    text += (
        '\n\n## Phase 16 — Deterministic architectural generation API\n\n'
        'Phase 16 exposes constraint compilation, CP-SAT planning, canonical architectural\n'
        'geometry and independent validation through `POST /generation/architectural`.\n'
        'It removes the generation-API production blocker without inventing Vastu doctrine;\n'
        'Vastu Specification v1 remains DRAFT and therefore production promotion remains blocked.\n'
    )
    path.write_text(text, encoding="utf-8")


patch_main()
patch_readiness()
patch_release_expectations()
patch_health_test()
patch_package()
patch_readme()
print("Phase 16 integration applied.")
