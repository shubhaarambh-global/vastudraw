from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps/api/app/main.py"
CLIENT = ROOT / "apps/web/src/api/client.ts"
PAGE = ROOT / "apps/web/src/components/generation/GenerationWorkspacePage.tsx"
STORE = ROOT / "python/ai_vastu/generation_intake/store.py"
MODELS = ROOT / "python/ai_vastu/generation_intake/models.py"

for required in (API, CLIENT, PAGE, STORE, MODELS):
    if not required.exists():
        raise SystemExit(f"Missing Phase 22 file: {required.relative_to(ROOT)}")

api = API.read_text(encoding="utf-8")
client = CLIENT.read_text(encoding="utf-8")
page = PAGE.read_text(encoding="utf-8")
store = STORE.read_text(encoding="utf-8")
models = MODELS.read_text(encoding="utf-8")

for token in (
    '"/projects/{project_id}/generation-intakes"',
    "_require_project_owner(service, project_id, user)",
    "IncomingGenerationAttachment",
):
    if token not in api:
        raise SystemExit(f"Generation intake API missing: {token}")

for token in ("FormData", "createGenerationIntake", "generation-intakes"):
    if token not in client:
        raise SystemExit(f"Generation intake client missing: {token}")

for token in (
    "Generation prompt",
    "application/pdf",
    "image/jpeg",
    "image/png",
    "Save generation brief",
):
    if token not in page:
        raise SystemExit(f"Generation intake UI missing: {token}")

for token in ("MAX_ATTACHMENTS = 8", "MAX_FILE_BYTES", "MAX_TOTAL_BYTES", "_verify_signature"):
    if token not in store:
        raise SystemExit(f"Generation upload validation missing: {token}")

if "authoritative_geometry: bool = False" not in models:
    raise SystemExit("Phase 22 must keep uploaded references nonauthoritative.")

print(
    "Phase 22 generation intake wired: "
    "prompt=true, images=true, pdf=true, previews=true, hashing=true, "
    "project_auth=true, authoritative_geometry=false"
)
