# Current Handoff

## Completed phase

Stage 2D9I - production export and download workflow - is GREEN on the
affected export, API, browser, generation-regression, and static-validation
gates.

The selected, persisted canonical candidate is now downloadable as SVG, JPEG,
PDF, or DXF without regenerating or mutating architectural geometry. Multi-floor
projects support individual floor artifacts in stable floor order and a genuine
combined multi-page PDF with one canonical floor per page.

Canonical `PlanDocument` remains authoritative and stays at version `1.1.0`.
The full backend gate is 472 passed with the exact same 13 documented
UI/schema/release-policy failures. No 2D9I regression is present.

## Preflight findings

- The 2D9H Python renderer already provided professional JPEG, per-floor PDF,
  and canonical vector DXF output. Browser SVG used equivalent professional
  presentation semantics, but there was no backend SVG exporter.
- `export_all_floor_bundles` produced every floor but emitted one PDF per floor;
  it did not produce a combined PDF document.
- Candidate selection is persisted as an immutable project `RevisionRecord`.
  Its canonical document, content hash, and `source_candidate_id` provide the
  correct production export boundary.
- Existing project services provide server-side project ownership checks. The
  export endpoint reuses those checks and returns not-found semantics for a
  project owned by another user.
- Existing billing and entitlement policy is enforced during generation and
  candidate selection. Export consumes only an already selected persisted
  revision, adds no charge, and adds no development or billing bypass.
- Direct in-memory responses fit the current storage architecture. Export does
  not need repository files, permanent temporary files, or a new object-storage
  subsystem.
- The existing `PlanDocument 1.1.0` contract is sufficient. Export manifests
  are operational response metadata rather than canonical geometry.

## Export and download architecture

### Authoritative source and candidate identity

The identity chain is explicit:

`selected UI candidate -> selection response -> persisted revision -> export request -> rendered artifact`

- The browser verifies that the candidate ID and source hash returned by
  selection match the candidate currently displayed before enabling export.
- `POST /projects/{project_id}/exports` loads the persisted revision; it never
  invokes generation or accepts client-authored export geometry.
- The request candidate ID must equal the revision's `source_candidate_id`.
  Cross-candidate and cross-project mismatches fail closed.
- Idempotent selection now also rejects an existing revision when its source
  candidate or canonical hash differs from the posted selection.
- Every response includes the source document hash, selected candidate ID, and
  artifact hash. The browser verifies source and candidate identity again
  before starting the download.
- Export checks the canonical hash before rendering and compares the serialized
  document and hash afterward. Rendering cannot alter the source document.

### API route, authorization, and errors

- Route: `POST /projects/{project_id}/exports`.
- Request fields are explicit: `candidate_id`, `revision_id`, allowlisted
  `format`, `scope`, and optional `floor_index`.
- Supported formats are the closed enum `svg`, `jpeg`, `pdf`, and `dxf`.
  Path-like or otherwise malformed format values are rejected by validation;
  raw extensions are never concatenated into a filesystem path.
- The route uses established authentication and `is_project_owner` server-side
  ownership validation. It does not trust browser IDs alone and does not expose
  local paths.
- Candidate/revision/project mismatch, missing floor, source-hash mismatch, and
  renderer failure produce bounded errors without stack traces or partial
  artifacts.
- Each request is atomic: one complete in-memory artifact is returned or no
  artifact is returned.
- Responses use `Content-Disposition`, `ETag`, private immutable cache control,
  identity/hash headers, and a base64url-encoded export-manifest header. CORS
  exposes only the download metadata needed by the browser.

### Export manifest and filenames

The internal operational manifest records:

- format;
- floor index and floor label where applicable;
- sanitized filename and media type;
- source `PlanDocument` hash;
- selected candidate identity;
- artifact byte size and artifact hash;
- combined versus single-floor scope.

Filenames are deterministic, bounded, lowercase, and sanitized through Unicode
normalization plus a conservative ASCII allowlist. Examples:

- `vastudraw-sharma-residence-ground-floor.svg`
- `vastudraw-sharma-residence-first-floor.dxf`
- `vastudraw-sharma-residence-all-floors.pdf`

No internal UUID is exposed in the normal filename, and user input cannot add a
path, arbitrary extension, or invalid filename characters.

### Format behavior

- SVG: a new deterministic backend vector exporter uses the 2D9H drawing scene
  and presentation model. It includes the site, canonical walls and openings,
  door/window symbols, canonical stair/treads, room labels, dimensions, north,
  scale, purposeful spaces, and presentation fixtures/furniture.
- JPEG: continues to use the professional 2D9H raster renderer.
- PDF: individual floors use the professional renderer. Combined export uses a
  true ReportLab multi-page document, one sorted canonical floor per page, with
  the same sheet semantics and no blank intermediary pages.
- DXF: remains vector/canonical output. It is never rasterized.
- Ground-only export produces one Ground Floor artifact. G+1, G+2, and G+3
  expose 2, 3, and 4 individual floors respectively in canonical order.
- Combined scope is intentionally PDF-only. Individual SVG/JPEG/PDF/DXF floor
  artifacts remain available for every canonical floor.

### Browser experience

- Restrained controls were added to the approved candidate workspace without a
  SaaS-shell or wizard redesign.
- Users can download PDF, SVG, JPEG, or DXF for the selected floor. Multi-floor
  candidates receive a stable floor selector and a separate combined-PDF action.
- Preparing/downloading, success, and bounded failure states are visible.
  Actions are disabled during an active request and reliably re-enabled after
  success or failure.
- Switching candidates clears selection and export state, preventing a stale
  artifact from being downloaded under a new visual selection.

### Persistence, caching, and bundles

- Artifacts are rendered and returned in memory. Production requests create no
  arbitrary files inside the repository and no indefinite temporary artifacts.
- Stable `ETag`/artifact hashes allow ordinary HTTP/client reuse. There is no new
  cross-request render cache, so stale geometry cannot survive a source-hash
  change.
- A ZIP bundle was not introduced. The current product flow benefits from direct
  per-format downloads plus a combined PDF, without adding another archive
  lifecycle or partial-bundle failure mode.

## Schema and version impact

- Canonical `PlanDocument` stays at `1.1.0`.
- No canonical model, persisted JSON schema, migration, content-hash rule, or
  generated schema changed.
- `ExportFormat` gained SVG and transient export bundles gained SVG bytes. The
  production request/manifest models are operational export contracts only.
- No `vastudraw-schema-change` workflow was required.

## Files changed for 2D9I

Backend export/API:

- `python/ai_vastu/exporting/svg_exporter.py` (new)
- `python/ai_vastu/exporting/workflow.py` (new)
- `python/ai_vastu/exporting/models.py`
- `python/ai_vastu/exporting/pdf_exporter.py`
- `python/ai_vastu/exporting/service.py`
- `python/ai_vastu/exporting/__init__.py`
- `python/ai_vastu/requirements/candidate_orchestrator.py`
- `apps/api/app/main.py`
- `apps/api/app/confirmed_generation_routes.py` (narrow additions while
  preserving pre-existing user changes)

Browser:

- `apps/web/src/api/client.ts`
- `apps/web/src/api/client.test.ts`
- `apps/web/src/components/generation/Phase26CCandidateWorkspace.tsx`
- `apps/web/src/components/generation/phase26c3.css`

Tests and documentation:

- `tests/exporting/test_production_workflow.py` (new)
- `apps/api/tests/test_exports.py` (new)
- `docs/exporting/phase-2d9i-workflow.md` (new)
- `docs/CURRENT_HANDOFF.md`

The worktree also contains extensive intentional pre-existing frontend,
API/auth/billing, local configuration, archive, script, and generated-package
changes. They were preserved and are not attributed to 2D9I.

## Tests added

The 28 focused Python tests cover:

- selected-candidate SVG, JPEG, PDF, and DXF;
- professional renderer semantics in SVG/JPEG/PDF and vector DXF output;
- Ground, G+1, G+2, and G+3 floor counts and deterministic ordering;
- true 2-, 3-, and 4-page combined PDFs;
- individual and combined deterministic filenames;
- every canonical upper floor in individual export;
- source serialization and content-hash immutability;
- deterministic repeated SVG/PDF output;
- selected-candidate identity and cross-candidate isolation;
- project ownership and unauthorized/cross-project rejection;
- unsupported and path-like format rejection;
- missing floor, source-hash mismatch, and bounded atomic failure behavior;
- canonical stairs and openings without invented geometry.

Browser client tests additionally verify the authenticated binary request,
identity response headers, and rejection of unsafe response filenames.

## Representative artifact inspection

The generated bytes and semantic structure were inspected programmatically:

- SVG contains professional 2D9H layers, canonical opening and stair graphics,
  labels, dimensions, north, scale, source hash, and floor identity;
- JPEG and PDF signatures and renderer output are non-empty and deterministic;
- DXF retains vector layers and canonical stairs/openings;
- combined G+1/G+2/G+3 PDFs contain exactly 2/3/4 pages in Ground-to-Third order;
- individual upper-floor artifacts contain their own canonical floor geometry;
- no source document or content hash changes during any export.

No temporary artifact or QA fixture was committed.

## Validation results

Focused 2D9I gate:

- `python -m pytest tests/exporting/test_production_workflow.py apps/api/tests/test_exports.py -o addopts="" -q -p no:cacheprovider`
  - 28 passed.

Affected backend gate:

- Exporting, plan-schema, project, billing, API, multi-candidate, generation
  orchestration, 2D9F multi-floor, and 2D9G vertical suites:
  - 134 passed;
  - 2 failures, both exact known baseline failures:
    `apps/api/tests/test_health.py::test_health` and
    `apps/api/tests/test_release_readiness.py::test_release_readiness_endpoint_reports_ready_after_phase20b`;
  - no new failure.

Static gates:

- `ruff check python apps/api tests` - PASS.
- `mypy python apps/api/app` - PASS across 198 source files.

Frontend gates:

- TypeScript typecheck - PASS.
- Web lint - PASS.
- Focused API client plus professional renderer tests - 14 passed.
- Full web tests - 25 passed, 1 exact pre-existing navigation-policy failure
  (`navigation.test.ts` expects `generation`, while the intentional dirty UI
  route is `new-plan`).
- Next.js production source compilation completed successfully in 4.3 seconds,
  then the managed Windows environment rejected TypeScript worker startup with
  `spawn EPERM`. Typecheck, lint, tests, and source compilation are green; this
  remains an environment-level final-worker limitation rather than a 2D9I
  source failure.

Full backend suite baseline comparison:

- 485 tests collected: 472 passed, 13 failed.
- The increased collection/pass count is from the 28 new 2D9I tests.
- All 13 failing identifiers exactly match the documented pre-2D9I baseline.
- No new, renamed, or unexplained 2D9I failure exists.

Exact remaining baseline failures:

1. `tests/release/test_readiness.py::test_current_public_mvp_is_ready_after_phase20b_freeze`
2. `tests/test_phase19_policy.py::test_dashboard_is_real_root_route_and_editor_remains_available`
3. `tests/test_phase1_policy.py::test_phase1_schema_contract`
4. `tests/test_phase20_policy.py::test_phase20b_release_gate_is_ready_with_zero_blockers`
5. `tests/test_phase21_policy.py::test_phase21_saas_navigation_has_real_routes_and_active_state`
6. `tests/test_phase2_policy.py::test_phase2_does_not_change_plan_document_schema_version`
7. `tests/test_phase3_policy.py::test_geometry_vendor_imports_are_confined_to_adapters`
8. `tests/test_phase4_policy.py::test_phase4_keeps_plan_document_schema_version_stable`
9. `tests/test_phase5_policy.py::test_phase5_keeps_plan_document_schema_version_stable`
10. `tests/test_phase6_policy.py::test_phase7_keeps_phase6_and_plan_contract_versions_stable`
11. `tests/test_phase9_policy.py::test_phase9_contract_versions_are_explicit_and_plan_schema_stays_stable`
12. `apps/api/tests/test_health.py::test_health`
13. `apps/api/tests/test_release_readiness.py::test_release_readiness_endpoint_reports_ready_after_phase20b`

## Known limitations and open risks

- Export is available only after a candidate has been selected into a persisted
  revision. This is deliberate: the selected revision is the production source
  of truth.
- Combined scope currently applies to PDF. SVG, JPEG, and DXF are intentionally
  downloaded per floor.
- There is no ZIP/project bundle, persistent object-storage artifact record, or
  cross-request render cache. The present in-memory one-artifact-per-request
  workflow is simpler, atomic, and sufficient for the current product.
- Entitlement is inherited from successful generation/selection; export itself
  performs ownership and identity validation but does not create a second billable
  event.
- The renderer continues to expose the generator's limited canonical window
  population rather than inventing facade openings.
- The managed Windows runner still prevents the final Next.js worker process
  even though source compilation, typecheck, lint, and tests complete.
- The pre-existing ignored `.pytest-2d9h-temp/` Windows-ACL directory remains as
  documented by 2D9H. 2D9I temporary test files and databases were removed.

## Git status

The worktree remains intentionally dirty with the 2D9I files listed above plus
pre-existing frontend, API/auth/billing, local configuration, archive, script,
and generated-package changes. Existing diffs were inspected before touching
already modified files and preserved with narrow compatible edits.

No reset, restore, checkout, clean, history rewrite, staging, or commit was
performed. Temporary 2D9I QA output, fixture source, and database directories
were removed.

## Readiness and recommended next stage

Stage 2D9I is ready to hand off. The selected canonical candidate has a secure,
deterministic, production-facing SVG/JPEG/PDF/DXF download workflow, including
true combined multi-page PDF output and all canonical floors.

Recommended next stage: begin 2D9J as a deliberate baseline/release-policy
reconciliation phase, starting by classifying the exact 13 backend failures and
the one web navigation-policy failure against the intentional current UI and
schema state. Do not change generation or renderer contracts merely to make
legacy policy assertions pass.
