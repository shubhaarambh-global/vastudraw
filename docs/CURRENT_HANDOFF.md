# Current Handoff

## Completed phase

Stage 2D9J - baseline reconciliation and full repository green - is complete.

All application test baselines are eliminated:

- backend: 486 collected, 486 passed, 0 failed;
- web: 26 passed, 0 failed;
- contracts: 1 passed, 0 failed;
- Ruff, mypy, TypeScript, web lint, schema drift, release policy, and release API: GREEN.

Canonical `PlanDocument` remains authoritative at version `1.1.0`. No canonical
schema shape, migration, serialization, or content-hash rule changed in 2D9J.
Stages 2D9A through 2D9I remain green.

## Starting baseline reproduced

The committed starting checkpoint was `16cfdca` (`phase2d9i-green`). Before any
source edit, the focused backend baseline reproduced exactly 13 failures:

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

The web baseline reproduced as 25 passed and one failure:

- `apps/web/src/components/shell/navigation.test.ts` expected the obsolete
  `generation` navigation key instead of the approved `new-plan`/`analyze-plan`
  split.

The ordinary full pytest invocation also encountered 32 setup errors because
the managed Windows account cannot scan
`C:\Users\chint\AppData\Local\Temp\pytest-of-chint`. Those were host ACL errors,
not repository failures. The complete final suite was run with a temporary
workspace-local `tmp_path` fixture; that fixture and all temporary databases
were removed after validation.

## Root-cause classification and fixes

### Canonical schema and generated contracts

Root cause: obsolete tests and a stale generated consumer artifact.

- `PlanDocument 1.1.0` was intentionally introduced at the 2D9G checkpoint and
  has an explicit, tested `1.0.0 -> 1.1.0` migration.
- The committed JSON schema already matched the authoritative Pydantic model and
  correctly declared `1.1.0` plus `Floor.site_spaces`.
- Six historical phase-policy tests, the API health test, and the contracts
  bootstrap test still asserted `1.0.0`; they now assert the current explicit
  release contract while retaining their original ownership/version invariants.
- The official `packages/contracts` generator regenerated
  `src/generated/plan-document.ts`. It now exposes schema `1.1.0` and canonical
  purposeful site spaces.
- The browser demo document now declares `1.1.0`, and the professional renderer
  consumes the generated canonical `Floor.site_spaces` type directly.

No canonical version bump or new migration was needed.

### Navigation and product routes

Root cause: policy tests lagged the approved product structure.

Current approved navigation remains unchanged:

- Workspace: Dashboard, Projects;
- Create: New plan, Analyze plan;
- Design: Editor, Vastu review, Exports;
- Account: Pricing, Billing & usage, Settings.

The public landing page remains `/`, the authenticated dashboard remains
`/dashboard`, and the editor remains available. Python route-policy tests and
the TypeScript active-navigation test now validate those real routes, both
generation modes, all four groups, and active-state behavior. No sidebar or UI
redesign was performed.

### Release policy and API readiness

Root cause: the fail-closed release evaluator supported only canonical schema
`1.0.0`, although the current authoritative and migratable contract is `1.1.0`.

- The evaluator now has an explicit supported release-schema set containing
  `1.1.0`; it does not compare the schema constant to itself.
- A new regression test proves an unknown future schema such as `99.0.0` still
  produces `PLAN_SCHEMA_UNSUPPORTED` and a `BLOCKED` disposition.
- The export gate evidence now reflects SVG/JPEG/PDF/DXF, persisted selected
  revisions, server ownership enforcement, and multi-floor PDF sheets.
- `/system/release-readiness` continues to delegate to the same evaluator. The
  service and endpoint now agree on READY with zero blockers.
- The deterministic readiness hash for the final policy is
  `d0aec389962301981693d4825116cb2d8d43eec04a309e1764ded6de687fc658`.

### Geometry vendor boundary

Root cause: two generator modules directly imported Shapely, violating the
repository rule that vendor geometry types remain confined to adapters. The
first failure had masked the second.

- Site partition measurement and purposeful residual-rectangle measurement now
  live behind `ai_vastu.geometry.shapely_validator`.
- Vendor-neutral immutable measurement records cross the geometry boundary;
  Shapely objects do not.
- Architectural Brain site accounting and purposeful-site classification keep
  the same area, residual, adjacency, road-access, lightwell, utility-yard, and
  open-space behavior.
- Existing 2D9A site-accounting and architectural-geometry suites validate that
  unexplained residuals are still rejected and legitimate classifications are
  unchanged.

### Repository-wide Ruff

The established Ruff command includes `scripts/`. A pre-existing untracked
ResPlan index builder had one extra blank line in its import block. Only that
formatting defect was corrected; its behavior and the rest of the user-owned
file were preserved.

## Files changed for 2D9J

Implementation and generated contracts:

- `python/ai_vastu/release/readiness.py`
- `python/ai_vastu/geometry/types.py`
- `python/ai_vastu/geometry/shapely_validator.py`
- `python/ai_vastu/geometry/__init__.py`
- `python/ai_vastu/architectural_brain/site_accounting.py`
- `python/ai_vastu/architectural_geometry/site_spaces.py`
- `packages/contracts/src/generated/plan-document.ts`
- `apps/web/src/components/generation/professional-plan-model.ts`
- `apps/web/src/editor/demo-document.ts`
- `scripts/build_resplan_precedent_index.py` (format-only change in a
  pre-existing untracked user file)

Tests and policy assertions:

- `tests/release/test_readiness.py`
- `tests/test_phase1_policy.py`
- `tests/test_phase2_policy.py`
- `tests/test_phase4_policy.py`
- `tests/test_phase5_policy.py`
- `tests/test_phase6_policy.py`
- `tests/test_phase9_policy.py`
- `tests/test_phase19_policy.py`
- `tests/test_phase21_policy.py`
- `apps/api/tests/test_health.py`
- `apps/web/src/components/shell/navigation.test.ts`
- `packages/contracts/src/bootstrap.test.mjs`
- `docs/CURRENT_HANDOFF.md`

No skip, xfail, ignored exit code, or weakened truthiness assertion was added.
The release test surface gained an explicit fail-closed future-schema test.

## Validation results

### Focused and affected tests

- Original 13 backend failure files plus schema, release, API, architectural
  geometry, and Architectural Brain suites: 113 passed.
- Release evaluator and API readiness final focused gate: 5 passed.
- Web suite: 26 passed, 0 failed.
- Contracts suite: 1 passed, 0 failed.

### Full backend

- Collection: 486 tests.
- Result: 486 passed, 0 failed, 0 errors.
- Command used the temporary workspace-local `tmp_path` fixture solely because
  of the inaccessible host pytest temp root. No fixture or QA database remains.

### Static, schema, and release gates

- `ruff check python apps/api tests scripts`: PASS.
- `mypy python apps/api/app`: PASS across 198 source files.
- Web TypeScript `tsc --noEmit`: PASS.
- Contracts TypeScript `tsc --noEmit`: PASS.
- Web ESLint: PASS.
- `scripts/check-plan-schema.py`: PASS; authoritative JSON schema matches
  Pydantic.
- Contracts generated-declaration drift check: PASS.
- Production MVP check: READY, zero blockers.
- Production release assertion: READY, zero blockers.
- Release-readiness API tests: PASS.
- `git diff --check`: PASS; only Windows LF/CRLF notices were emitted.

### Production build

- Standard `next build` compiled successfully in 29.1 seconds, then the managed
  Windows host returned `spawn EPERM` while starting the TypeScript worker.
- `next build --experimental-build-mode compile` compiled successfully in 3.6
  seconds and then returned the same `spawn EPERM` while collecting page data
  with 14 workers.
- Independent web/contract TypeScript, lint, and tests are green. The failing
  operation is child-process creation, not compilation or application code.
- The host runs Node `20.11.1` while the repository declares Node `>=24`; pnpm
  reports this as an engine warning. No OS security setting or repository build
  behavior was weakened.

## Schema, navigation, and release impact

- Schema: no canonical change; remains `1.1.0`. Generated TypeScript is now in
  sync with the already-current canonical JSON schema.
- Navigation: implementation unchanged; tests now encode the approved grouped
  navigation and public landing/authenticated dashboard separation.
- Release policy: explicit support for current schema `1.1.0`, fail-closed for
  unknown versions, and current export evidence.
- Release API: unchanged endpoint architecture; now returns the evaluator's
  correct READY state.
- Generation/export: no semantic weakening. 2D9A purposeful-site invariants and
  2D9I ownership/source-identity export behavior remain covered by the fully
  green backend suite.

## Environmental limitations

- The managed Windows global pytest temp root is inaccessible. The repository's
  complete suite is green with an isolated workspace-local fixture.
- The managed host forbids the final Next.js child-worker spawn after successful
  compilation.
- Node is below the repository's declared supported major version. Production
  qualification should rerun the build under Node 24+ on a host that permits
  worker creation.

These are external execution constraints; there are zero remaining application
test baseline failures.

## Git status and working-tree safety

HEAD remains `16cfdca` (`phase2d9i-green`). Stage 2D9J changes are unstaged and
uncommitted.

The worktree still contains intentional pre-existing frontend, API/auth/billing,
configuration, archive, payload, and script files. Dirty files were inspected
before any overlapping edit. No reset, restore, checkout, clean, history
rewrite, staging, or commit was performed. Temporary 2D9J fixtures and databases
were removed.

## Readiness for 2D9K

Stage 2D9J is application-green and ready for handoff to 2D9K production
qualification. The first recommended action is to checkpoint only the verified
2D9J hunks, then run production build/route generation under Node 24+ on a host
that permits Next.js workers. Do not reopen canonical generation or renderer
contracts during that qualification unless a new evidence-backed defect appears.

## Stage 2D9K - End-to-End V1 Production Qualification

Status: **NOT QUALIFIED**

### Repository validation

The repository-wide validation gate is green after baseline reconciliation.

Validated runtime:
- Node v24.20.0
- pnpm 10.17.1
- Python 3.12.10

Final `pnpm validate` result:
- Ruff: passed
- mypy: passed across 198 source files
- Python tests: 487 passed
- PlanDocument schema/contracts: generated and drift check passed
- frozen Vastu specification/review/production gates: passed
- deterministic constraints/planner/geometry/validation/scoring gates: passed
- project revision gate: passed
- web typecheck: passed
- web tests: 26 passed
- contracts tests: 1 passed
- exports/DWG framework/generation/API/project-editor/intake/requirements gates: passed
- billing/persistence/auth/MVP gates: passed
- Phase 27 release gate: passed with bounded 1-4 floor generation contract
- Phase 28 hybrid AI gate: passed
- Prettier: passed
- ESLint: passed
- TypeScript: passed
- Next.js production build: passed
- Phase 26C.4A: passed
- Phase 26 final: passed
- Phase 26 OpenRouter deterministic-authority gate: passed

Warnings observed were dependency deprecations only and were not validation failures.

### Production qualification blocker

The representative 30x50 residential production path is still not qualified.

The base deterministic geometry solver can place the confirmed program, but the real production candidate pipeline does not produce an accepted candidate for the established qualification case.

Across both tested plot orientations and all six deterministic candidate strategies, candidate generation is rejected by the production quality loop. Observed rejection causes include:

- circulation disconnection;
- unexplained/unclassified residual site area;
- one-car parking expanding to approximately 30-38 m2 instead of remaining within the intended residential parking allocation.

This is a production candidate-planning/site-allocation defect, not a fundamental CP-SAT feasibility failure.

Renderer, persisted revision export, SVG/JPEG/PDF/DXF generation, multipage PDF generation, candidate identity checks, source-plan hashing, ownership checks and the broader repository validation gates are not the cause of this qualification failure.

The qualification process did not weaken:
- circulation validation;
- site-accounting validation;
- unexplained-residual rejection;
- parking safeguards;
- Vastu rules;
- candidate deduplication;
- canonical PlanDocument authority.

A rejected candidate must remain rejected.

### Qualification evidence

Retained evidence:

`.local/qa-2d9k/qualification-blocker-20260921`

The retained ground-floor 30x50 artifact is renderer evidence for architecture rejected by the production critic. It must not be represented as an accepted production candidate.

Multi-floor renderer/export evidence is retained separately in the same qualification evidence tree.

The temporary repository-root pytest fixture used during Windows ACL investigation was removed. Focused affected regression tests subsequently passed with TEMP/TMP redirected under `.local/qa-2d9k`.

### Baseline reconciliation performed during qualification

The qualification run also exposed stale repository checks that were reconciled with already-established product contracts:

- project smoke fixture updated from PlanDocument schema 1.0.0 to 1.1.0;
- Phase 26C checker reconciled to the current Vastudraw wizard vocabulary while retaining generation-action validation;
- SaaS UI checker reconciled to the current sidebar and frozen Vastu-status vocabulary;
- Phase 27 release checker reconciled from the retired single-floor restriction to the established bounded 1-4 floor fail-closed generation contract;
- formatting drift required by the repository-wide Prettier gate was normalized.

These changes do not resolve the 30x50 production candidate blocker.

### Architectural Brain experiment intentionally excluded from 2D9K closure

The current working-tree experiment in:

- `python/ai_vastu/architectural_brain/bridge.py`
- `tests/architectural_brain/test_phase26_final.py`

is not part of the 2D9K qualification closure.

It explores the correct authority principle that AI/precedent concept sizing must not create new authoritative hard feasibility caps. However, parking must still be bounded independently by the deterministic residential planning/site-allocation layer.

That work remains isolated for the corrective planning stage.

### Next stage

**2D9L - Production Candidate Repair & Site Allocation**

Required scope:

1. reproduce the established 30x50 failure through the real production candidate pipeline;
2. preserve AI/precedent sizing as non-authoritative intent;
3. enforce the authoritative one-car parking allocation independently of AI concept sizing;
4. prevent parking from expanding to roughly 30-38 m2;
5. provide bounded deterministic circulation/topology repair rather than weakening connectivity validation;
6. classify/allocate purposeful residual site space instead of allowing unexplained residual geometry;
7. preserve puja-sanitary, circulation, site-accounting, deduplication, Vastu, Canonical PlanDocument, renderer and export invariants;
8. obtain at least one genuinely accepted production candidate for the established 30x50 case;
9. rerun Stage 2D9K from the beginning after the repair.

Only a successful rerun of 2D9K can qualify and freeze V1.
