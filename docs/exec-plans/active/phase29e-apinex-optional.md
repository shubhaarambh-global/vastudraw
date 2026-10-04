# Phase 29E optional APINEX development provider

Status: **IMPLEMENTATION/OFFLINE PASS_LOCAL; CANONICAL INFERENCE
BLOCKED_PROVIDER_HTTP_402; NOT_QUALIFIED**

## Scope

- Add the isolated `apinex` identity as an explicitly selected development-only
  advisory provider.
- Pin `https://api.apinex.bond/v1` and `free/gpt-6-luna` with no fallback,
  substitution, retry, redirect, or proxy inheritance.
- Preserve `ollama_local` as the qualified local-development default.
- Reuse the real RequirementDraft, PlanRecognitionDraft, architectural intent,
  soft-Vastu, Architectural Brain, revision, media-validation, and Pdfium paths.
- Provide a synthetic-only live qualification gate without storing credentials.

## Protected boundaries

- APINEX output is untrusted advisory input. Strict JSON and canonical Pydantic and
  application validation remain mandatory after provider schema signaling.
- Application code owns identifiers, provenance, confirmation/source semantics,
  reference names, schema versions, hashes, and non-authoritative flags.
- PNG and JPEG remain actual validated raster inputs. PDF remains local
  `PdfiumPageRenderer -> PNG`; raw PDF bytes never reach APINEX.
- Staging and production reject APINEX. NVIDIA, Ollama, frozen Vastu, deterministic
  geometry, canonical documents, Supabase, and payment behavior are unchanged.

## Runtime policy

- Base URL: `https://api.apinex.bond/v1`, exact-match only.
- Model: `free/gpt-6-luna`, exact request, inventory, and returned-model match.
- Credential: process environment only; never stored or printed.
- Timeouts: connect 5s, read 180s, total 240s, write 30s, pool 5s.
- Maxima: connect 15s, read 300s, total 360s, write 60s, pool 15s.
- Request cap: 48 MiB. Response cap: 2 MiB. One attempt, no retry/fallback.

## Live evidence boundary

Historical manual evidence remains separate: endpoint/auth, inventory, exact text,
structured text, and a second bounded structured PNG probe passed live; an earlier
PNG schema probe failed because the response drifted into Markdown/schema mismatch.

The latest canonical operator qualification was run twice. Both runs reported:

- endpoint and exact model inventory: `PASS_LIVE`;
- text, structured text, real requirements, PNG, JPEG, PDF-path, and strict JSON:
  `category=request_rejected`, `stage=provider_transport_http`, `attempts=1`,
  `http_status=402`;
- provenance and content hash: `BLOCKED_DEPENDENCY` because no qualifying media
  draft was available;
- aggregate: `APINEX LIVE QUALIFICATION FAIL`.

Authentication/API reachability and catalog access work, but current inference is
`BLOCKED_PROVIDER_HTTP_402`. This is not evidence of a Vastudraw schema, media, or
provider-adapter defect. Do not infer an exact billing, quota, or account cause
without provider evidence. No further APINEX live call is required for this
checkpoint; the provider remains optional, fail-closed, and `NOT_QUALIFIED`.

Real client plans or prompts must not be sent to APINEX merely because this optional
development provider exists. No privacy or retention guarantee has been verified.
