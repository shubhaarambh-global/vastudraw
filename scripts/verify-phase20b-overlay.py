from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = (
    "scripts/record-vastu-expert-approval.py",
    "scripts/freeze-vastu-spec.py",
    "scripts/check-vastu-production-release.py",
    "scripts/apply-phase20b.py",
    "docs/adr/ADR-043-vastu-human-attestation-and-freeze.md",
    "docs/architecture/phase-20b-validation.md",
)
missing = [item for item in required if not (ROOT / item).exists()]
if missing:
    raise SystemExit("Missing Phase 20B files: " + ", ".join(missing))
print("Phase 20B overlay files present.")
