import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
root_package = ROOT / "package.json"

root = json.loads(root_package.read_text(encoding="utf-8"))
scripts = root["scripts"]
scripts["generation-intake:check"] = "python scripts/check-generation-intake.py"

validate = scripts["validate"]
if "pnpm generation-intake:check" not in validate:
    needle = "pnpm project-editor:check && pnpm saas-ui:check"
    if needle not in validate:
        raise SystemExit("Could not locate Phase 22 validate insertion point.")
    scripts["validate"] = validate.replace(
        needle,
        "pnpm project-editor:check && pnpm generation-intake:check && pnpm saas-ui:check",
    )

root_package.write_text(json.dumps(root, indent=2) + "\n", encoding="utf-8")

# Phase 21's navigation test may still be present without the explicit ignored promise
# in trees created before the local Phase 21 lint repair.
nav_test = ROOT / "apps/web/src/components/shell/navigation.test.ts"
text = nav_test.read_text(encoding="utf-8")
old = 'test("SaaS navigation marks the current product area active", () => {'
new = 'void test("SaaS navigation marks the current product area active", () => {'
if old in text:
    nav_test.write_text(text.replace(old, new, 1), encoding="utf-8")

print("Phase 22 multimodal generation intake scripts integrated.")
