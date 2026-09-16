import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
root_package = ROOT / "package.json"
web_package = ROOT / "apps/web/package.json"

root = json.loads(root_package.read_text(encoding="utf-8"))
scripts = root["scripts"]
scripts["saas-ui:check"] = "python scripts/check-saas-ui.py"

validate = scripts["validate"]
if "pnpm saas-ui:check" not in validate:
    needle = "pnpm project-editor:check && pnpm persistence:check"
    if needle not in validate:
        raise SystemExit("Could not locate Phase 21 validate insertion point.")
    scripts["validate"] = validate.replace(
        needle,
        "pnpm project-editor:check && pnpm saas-ui:check && pnpm persistence:check",
    )

root_package.write_text(json.dumps(root, indent=2) + "\n", encoding="utf-8")

web = json.loads(web_package.read_text(encoding="utf-8"))
web_test = web["scripts"]["test"]
nav_test = "./src/components/shell/navigation.test.ts"
if nav_test not in web_test:
    web["scripts"]["test"] = f"{web_test} {nav_test}"
web_package.write_text(json.dumps(web, indent=2) + "\n", encoding="utf-8")

print("Phase 21 SaaS UI scripts integrated.")
