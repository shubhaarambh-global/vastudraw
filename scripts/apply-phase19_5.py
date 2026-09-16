import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

root_package = ROOT / "package.json"
root = json.loads(root_package.read_text(encoding="utf-8"))
scripts = root.setdefault("scripts", {})
scripts["project-editor:check"] = "python scripts/check-project-editor-workspace.py"

validate = scripts.get("validate")
if not isinstance(validate, str):
    raise SystemExit("Root package.json does not contain a validate script.")

if "pnpm project-editor:check" not in validate:
    anchor = "pnpm web-api:check && "
    if anchor not in validate:
        raise SystemExit("Could not find web-api validation anchor.")
    validate = validate.replace(
        anchor,
        anchor + "pnpm project-editor:check && ",
        1,
    )
    scripts["validate"] = validate

root_package.write_text(json.dumps(root, indent=2) + "\n", encoding="utf-8")

web_package = ROOT / "apps/web/package.json"
web = json.loads(web_package.read_text(encoding="utf-8"))
web_scripts = web.setdefault("scripts", {})
web_test = web_scripts.get("test")
if not isinstance(web_test, str):
    raise SystemExit("apps/web package.json does not contain a test script.")

workspace_test = "./src/editor/project-workspace.test.ts"
if workspace_test not in web_test:
    web_scripts["test"] = f"{web_test} {workspace_test}"

web_package.write_text(json.dumps(web, indent=2) + "\n", encoding="utf-8")

print("Phase 19.5 package scripts integrated.")
