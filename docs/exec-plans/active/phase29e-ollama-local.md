# Phase 29E - Local Ollama / Qwen3-VL Development Provider

Status: **QUALIFIED LOCAL DEVELOPMENT PROVIDER — 3/3 PASS_LOCAL; NOT PRODUCTION
QUALIFIED**

## Scope

Use the isolated `ollama_local` advisory provider as the local-development
default with the exact local model
`qwen3-vl:8b-instruct-q4_K_M` at `http://127.0.0.1:11434`.

Live local qualification covers the real `RequirementDraft` path and real
`PlanRecognitionDraft` PNG, JPEG, and locally-rendered PDF paths. The
architectural-intelligence, soft-Vastu, Architectural Brain, and revision
adapters are contract-tested offline and are not included in the live
`PASS_LOCAL` claim unless separately exercised.

## Non-goals

- no NVIDIA, OpenRouter, Gemini, Supabase, payment, or other live calls;
- no production or staging Ollama selection;
- no model download, fallback, retry, output repair, or provider fallback;
- no frozen Vastu, deterministic geometry, PlanDocument, revision ancestry,
  billing-security, payment, or Git-metadata changes;
- no change to NVIDIA request behavior or existing live evidence.

## Architecture

1. Add a standalone bounded Ollama HTTP client. Environment construction
   requires explicit `APP_ENV=development`, the exact loopback HTTP origin,
   and the exact model pin. HTTP proxy inheritance and redirects are disabled.
2. Send `stream=false`, the real contract JSON schema through `format`, and
   `options.temperature=0`. Parse only strict JSON objects, then apply the
   existing Pydantic/application contract. Do not strip Markdown/reasoning,
   extract JSON, or repair output.
3. Use finite connect/read/total/write/pool limits, one attempt, a bounded
   request and response, fixed sanitized errors, and distinct transport,
   strict-JSON, application-validation, and provenance stages.
4. Add thin provider adapters for requirements, plan recognition,
   architectural intelligence, soft-Vastu reasoning, Architectural Brain,
   and revision intent. Application-owned identity, provenance, hashes,
   advisory flags, and confirmation semantics are overwritten after model
   output.
5. Validate and pass PNG/JPEG bytes directly to Ollama. Continue rendering PDF
   locally with the unchanged `PdfiumPageRenderer`; Ollama receives PNG pages,
   never raw PDF bytes.
6. Keep production settings and staging preflight NVIDIA-only. Add rejection
   tests for every Ollama selector under staging and production.
7. Use the dedicated profile as the explicit local-development default and keep
   the canonical local checker. Production settings and staging preflight remain
   NVIDIA-only and have no silent local fallback.

## Resource policy

- endpoint: exact `http://127.0.0.1:11434`;
- model: exact `qwen3-vl:8b-instruct-q4_K_M`;
- connect timeout: 3 seconds (maximum 10);
- read timeout: 300 seconds (maximum 300);
- total timeout: 360 seconds (maximum 360);
- write/pool timeout: finite and capped by the remaining total deadline;
- response: shared 2 MiB cap;
- request: bounded aggregate messages/images;
- retries: zero.

## Validation

Run focused client, adapter, media, factory, production-boundary, requirements,
and plan-intake tests first. Then run existing NVIDIA/provider suites,
`pnpm phase29c:check`, the canonical Ollama local checker, the full Python
suite, Ruff, mypy, `git diff --check`, and `pnpm validate`. Record exact counts
and distinguish environmental failures from application regressions.

Canonical reliability evidence: three consecutive complete runs passed endpoint,
exact model, real `RequirementDraft`, PNG/JPEG/PDF-path `PlanRecognitionDraft`,
strict JSON, provenance, reference identity, confirmation-required semantics,
and canonical content hash. Aggregate result: **3/3 `PASS_LOCAL`**.

## Human-review triggers

Stop for review before allowing a non-loopback endpoint, staging/production
Ollama selection, a different model, retries/fallback, schema/output repair,
an AI authority expansion, or any change to NVIDIA behavior.
