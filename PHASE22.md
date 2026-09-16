# Phase 22 — Multimodal generation prompt + image/PDF intake

## Objective

Replace the informational Generation page with a real SaaS intake workflow for client prompts and
reference files while preserving the canonical-geometry authority boundary.

## Implemented

- Project-bound generation prompt.
- JPG/JPEG, PNG, and PDF upload.
- Multi-file preview/removal before submission.
- Authenticated project ownership enforcement.
- Server-side file-count and byte limits.
- File-signature validation to reject MIME spoofing.
- SHA-256 per attachment and deterministic intake integrity hash.
- Persistent sidecar manifests and server-generated storage names.
- Production storage root fails closed unless explicitly configured.
- No OCR and no silent geometry extraction.
- No change to frozen Vastu v1.0 bundle or production readiness hashes.

## Not in Phase 22

Phase 22 does not claim that free-form client text or uploaded documents can directly author
PlanDocument geometry. Structured interpretation and explicit user confirmation are the next phase.
