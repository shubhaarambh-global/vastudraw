# Current Handoff

## Current local qualification - Phase 29F GREEN (2026-10-05)

Phase 29F local full-stack acceptance is qualified. Phase 29E remains frozen at
1940b09fe729fb5d37ac007598c7e245d0fdacdf; no Git staging/history operation occurred.
See [the exact acceptance report](phase29f-local-acceptance.md) for the full
59-file inventory, root causes, commands and local evidence. Earlier NOT GREEN
entries below describe historical checkpoints, superseded by this entry.

Final: 1319 Python tests PASS (six dependency warnings); focused148 PASS including
Ollama79; earlier dedicated affected405 PASS, final affected317 included in full;
Ruff PASS; mypy236 files PASS; web33 tests PASS; contracts1 test PASS;
web build/lint/typecheck/format PASS; pnpm.cmd validate exit0; diff whitespace PASS.
Node24.20.0 / pnpm10.17.1 used. Actual Vastu3/3 and recovery3/3 evidence retained.

Deterministic fixes prevent bedroom/parking transit, preserve ensuite access,
connect public circulation, generate canonical road-facing 3000mm vehicle
openings, reject obstructed bays and unsupported internal/exterior doorway spans.
Bounded existing-concept/variant search returns four valid alternatives; AI stays
advisory, without provider/model fallback or response repair/retry.
Dev-only Ollama revision chat regenerates exact dimensions, correctly converts
clear/envelope wall reserve and discloses pre-generation grid rounding.
Immutable ancestry, manual lock/exact-dimension save, history and exact-revision
editor exports remain canonical. Frozen rules/schema/wet-stack softness unchanged.

Real desktop1440/tablet768/mobile390 browser journey, undo/redo/save/history,
loading/empty/error states, outage503/recovery, exports, navigation and final
API/web restart persistence PASS. Project f2603dae-292e-4d38-b110-ee2aec730dae
has eight revisions; latest57ad4c12-8855-4164-894f-9858b2684bd8 hash
 d9077c0a947edeea4ac05da90a2be97fdf35231138cdeff4963edb358785787d.
Isolated entitlement exhaustion proves liveHTTP402 with disabled gateways and
staging/production bypass denial, preserving operator data.

API8000 and development web3000 remain running. No human-only local step remains.
Operator owns Git. Hosted/production readiness, structural work and arbitrary
wall/opening revision command application are not claimed.


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

## Stage 2D9L-C - Bounded Circulation Topology Repair

Status: **IMPLEMENTED IN SNAPSHOT; LOCAL VALIDATION REQUIRED**

### Context

2D9L-A and 2D9L-B were validated locally before this snapshot handoff:
- residential occupied-area target remains a soft objective rather than a hard room-coverage floor;
- canonical residual polygon measurement and purposeful boundary-connected open-space classification are in place;
- focused Ruff/mypy and broader geometry/architectural-brain/solver regressions were reported green.

The single-floor production defect remained that CP-SAT could return a geometrically feasible room placement whose door-capable adjacency graph was disconnected. Auto-opening synthesis then failed after the solve.

### 2D9L-C implementation

- Added pinned `networkx==3.6.1` as a non-authoritative graph-analysis dependency.
- Added `CirculationTopologyAnalysis` and `analyze_room_access_graph()`.
- Existing canonical wall/opening geometry remains authoritative; NetworkX only analyzes already-proven graph edges.
- Sanitary rooms remain reachable leaves and cannot become transit nodes.
- Existing `build_circulation_graph()` now uses the shared topology-analysis layer instead of maintaining a separate hand-written reachability traversal.
- Added `CirculationRepairPair` to residential planner configuration.
- Added system-derived hard repair-pair constraints to CP-SAT. These constraints are not universal architectural defaults: they are introduced only after a solved layout proves circulation-disconnected.
- Auto-circulation now performs at most four deterministic repair attempts.
- Repair candidates connect a reachable non-sanitary room to a disconnected room, ranked first by current geometric separation and then deterministic architectural/access priority.
- Candidate repair pairs that conflict with compiled hard adjacency prohibitions are skipped.
- Infeasible repair pairs are discarded rather than weakening any existing invariant.
- After each feasible repair solve, canonical geometry is rebuilt and circulation is re-evaluated from scratch.
- Existing circulation validation remains the final authority after opening synthesis.
- Single-floor `require_horizontal_circulation` was deliberately **not** globally flipped to `True`; the existing heuristic topology targets therefore do not become arbitrary universal hard rules.
- Restored irregular purposeful-site-space UUID hardening so non-rectangular spaces with the same bounding box cannot collide.

### Tests added/updated

- `tests/architectural_geometry/test_circulation.py`
  - NetworkX articulation/reachability regression;
  - sanitary-room transit remains prohibited.
- `tests/solver/test_models.py`
  - repair pair must reference two distinct rooms.
- `tests/solver/test_circulation_repair.py`
  - system-derived repair pair enforces a door-capable shared wall and emits `CIRCULATION_REPAIR_ENFORCED`.
- `tests/generation/test_circulation_repair_selection.py`
  - disconnected solved geometry produces the expected deterministic repair pair and exact minimum door-capable shared length.

### Dependency register

`THIRD_PARTY.md` records NetworkX 3.6.1 / BSD-3-Clause and explicitly limits it to graph computation. It has no geometry or Canonical PlanDocument authority.

### Validation available in this snapshot environment

The snapshot sandbox does not contain OR-Tools, pyclipr, Ruff or mypy and has no package-network access. Therefore full repository validation cannot be truthfully claimed here.

Completed here:
- Python compile validation for all modified Python/test files;
- direct execution of the isolated NetworkX topology-analysis logic, including sanitary-leaf and unknown-room fail-closed cases.

Required local validation after applying the 2D9L-C package:

```powershell
$env:Path = "$(Resolve-Path '.\.venv\Scripts');$env:Path"
$repoRoot = (Resolve-Path ".").Path
$pythonRoot = (Resolve-Path ".\python").Path
$env:PYTHONPATH = "$repoRoot;$pythonRoot"

.\.venv\Scripts\python.exe -m ruff check `
  python/ai_vastu/architectural_geometry `
  python/ai_vastu/generation `
  python/ai_vastu/solver `
  tests/architectural_geometry/test_circulation.py `
  tests/generation/test_circulation_repair_selection.py `
  tests/solver/test_circulation_repair.py `
  tests/solver/test_models.py

.\.venv\Scripts\python.exe -m mypy `
  python/ai_vastu/architectural_geometry `
  python/ai_vastu/generation `
  python/ai_vastu/solver

.\.venv\Scripts\python.exe -m pytest `
  tests/architectural_geometry/test_circulation.py `
  tests/generation/test_auto_circulation.py `
  tests/generation/test_circulation_repair_selection.py `
  tests/solver/test_circulation_repair.py `
  tests/solver/test_models.py -q
```

If those focused gates are green, run the broader affected suite before returning to the 30x50 production qualification path:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests/geometry `
  tests/architectural_geometry `
  tests/generation `
  tests/architectural_brain `
  tests/solver `
  tests/multi_candidate `
  tests/requirements -q
```

### Next action

Apply the 2D9L-C package, run the focused local validation once, then rerun the real 30x50 multi-candidate production path. If circulation is repaired but the production critic still rejects every candidate, diagnose the remaining rejection evidence without weakening site accounting, Vastu, deduplication, geometry validation or Canonical PlanDocument authority.

---

## Stage 2D9L / 2D9K final qualification closure

Status: **V1 QUALIFIED**

2D9L production-candidate repair is checkpointed at commit `cf6f389b7d9537b8711413bb737f7dea6dd341a6`
and tagged `phase2d9l-green`.

The final Stage 2D9K end-to-end qualification passed from the verified working
state represented by the local qualification evidence directory:

`D:\shubhaarambh\Vastu-AI\ai-vastu-architect-phase25\.local\qa-2d9k\final-20260922-183955`

Qualification covered the full repository gate, the real 50 ft x 30 ft
East-road production candidate path, deterministic repeatability, bounded
circulation repair, purposeful site allocation, architectural critic acceptance,
cross-floor soft wet-stack coordination, persisted exact revision identity,
ownership isolation, and SVG/JPEG/PDF/DXF exports from the reopened canonical
PlanDocument.

Architecture decisions retained:

- Canonical PlanDocument remains authoritative.
- OR-Tools remains the deterministic placement/constraint solver.
- NetworkX is used for circulation/topology computation, not as an authority layer.
- Shapely/GEOS remains confined to the approved geometry adapter boundary.
- Wet-stack coordination is a soft cross-floor quality objective, not a universal hard rule.
- Parking has no arbitrary universal hard maximum; sizing is contextual and quality-driven.
- Unexplained buildable-envelope residuals continue to fail closed.
- Existing Vastu, overlap, circulation, site-accounting, deduplication, and export-integrity gates were not weakened.

The historical `phase2d9k-not-qualified` tag remains untouched as evidence of
the earlier failed qualification.

## Phase 29A — Production Configuration Contract

Status: **IMPLEMENTED AND LOCALLY VALIDATED; NOT A PRODUCTION QUALIFICATION**

### Baseline and worktree

- Branch: `phase29`
- Starting HEAD: `cbd295f5e9028186acbfb14f40c1142e3a003b27`
- Phase 29A and Phase 29B were checkpointed together after local validation at
  commit `abb24feb0209a18f14877c2f8154e24c4dbcffcc`. No qualification tag,
  deployment, database migration, or live account action was performed.
- The worktree was already dirty at entry, including a user-edited `AGENTS.md`, Agent OS files, archives, payloads, and scripts. These were preserved. No reset, clean, broad checkout/restore, or archive deletion was performed.
- Rollback point: qualified `post-v1-development-qualified` at
  `cbd295f5e9028186acbfb14f40c1142e3a003b27`. The Phase 29A/29B checkpoint is
  `abb24feb0209a18f14877c2f8154e24c4dbcffcc`; preserve the pre-existing user
  changes and untracked payloads during any rollback.
- Canonical schema generation during validation produced no tracked diff in `packages/contracts/schema/plan-document.schema.json` or `packages/contracts/src/generated/plan-document.ts`.

### Implementation

Production configuration now agrees with runtime consumers:

- Supabase authentication is selected with `AI_VASTU_AUTH_MODE=supabase` and audience `authenticated`, matching the existing shared verifier.
- `AI_VASTU_DATABASE_URL` is the canonical PostgreSQL URL. Production billing now trims it consistently with other consumers.
- `AI_VASTU_WEB_ORIGINS` drives CORS; explicit `AI_VASTU_TRUSTED_HOSTS` drives an outermost TrustedHost middleware.
- Requirements and generation-upload storage roots must be explicitly absolute and configured.
- A true `AI_VASTU_DEV_BILLING_BYPASS` is rejected in production.
- Production provider routing is validated as the qualified hybrid: OpenRouter for text/reasoning and direct Gemini `gemini-3.1-flash-lite` for plan recognition.
- `AI_VASTU_PAYMENT_GATEWAY` must explicitly select `phonepe`, `razorpay`, or `disabled`. Razorpay credentials are conditional on Razorpay selection. PhonePe/disabled selections block Razorpay checkout and webhooks before provider construction or billing repository side effects.
- The production launch checker rejects PhonePe until Phase 29D implements it and rejects disabled payments. Its storage probes use unique temporary files and remove only the file created by that invocation.
- The launch runbook and `.env.example` describe the canonical settings and the Phase 29D payment blocker.

Protected deterministic geometry, Vastu semantics/hashes, canonical PlanDocument, units, project revision behavior, and generation behavior were not changed. No data migration was introduced.

### Changed Phase 29A files

- `.env.example`
- `apps/api/app/billing_routes.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_phase29a_runtime.py` (new)
- `docs/exec-plans/active/phase29a-production-configuration.md` (new)
- `docs/CURRENT_HANDOFF.md`
- `docs/agent-memory/knowledge-graph.json` (verified Phase 29A node and edge)
- `docs/runbooks/production-launch.md`
- `python/ai_vastu/billing/factory.py`
- `python/ai_vastu/production/settings.py`
- `scripts/check-production-launch.py`
- `tests/billing/test_factory.py` (new)
- `tests/production/test_gemini_settings.py`
- `tests/production/test_openrouter_settings.py`
- `tests/production/test_phase29a_fixtures.py` (new)
- `tests/production/test_settings.py`
- `tests/test_phase25_policy.py`

The pre-existing local changes in `AGENTS.md`, `.codex/`, and `docs/agent-system/` are user-owned and were preserved. `docs/agent-memory/` was also pre-existing and user-owned; the only intentional Phase 29A change there is the verified `subsystem:phase29a-production-config` node and its `branch:phase29` edge.

### Independent review and tests

- Two independent planners converged on config/runtime wiring only; Architecture Guardian challenged and accepted the bounded scope.
- Fixture Engineer added deterministic production config boundary, secret-redaction, gateway-selection, and rate/HSTS limit cases.
- Regression Tester: 218/218 affected tests passed; 10/10 Phase 25/27/28 policy tests and eight offline subsystem checks passed.
- Adversarial Tester found no Phase 29A bypass. It identified pre-existing auxiliary JWT role/expiry divergence, recorded below.
- Security Reviewer accepted the Phase 29A changes after path and middleware-order fixes.
- Independent QA accepted the code changes after billing URL normalization and safe unique storage probe fixes.

Final repository gate from the Phase 29A working tree:

- `git diff --check`: PASS (Windows LF/CRLF notices only).
- `pnpm validate`: PASS.
- Ruff: PASS (`python:lint`).
- mypy: PASS, 199 source files.
- Python tests: 596 passed, 0 failed (five dependency deprecation warnings).
- Plan schema generation/check: PASS; generated contract tree unchanged.
- Vastu checks/review/production release: PASS; frozen bundle hash unchanged.
- Offline deterministic constraints, planner, geometry, validation, scoring, project revisions, exports and generation checks: PASS.
- Web TypeScript, lint, formatting and tests: PASS; 26 web tests and one contracts test passed.
- Next.js production build: PASS; routes generated.
- Phase 25/26/27/28 offline gates: PASS.
- No live PostgreSQL, Supabase, OpenRouter, Gemini, PhonePe, or Razorpay service was exercised.

### Remaining blockers and next work

Phase 29A completion does not qualify production. The following existing launch blockers remain:

1. **Phase 29B, HIGH:** auxiliary billing, requirements, and confirmed-generation JWT resolvers accept suitably signed tokens without requiring `exp` and `role=authenticated`; the shared canonical verifier rejects them. Offline ES256/JWKS-mocked reproduction confirmed this difference. Consolidate auxiliary resolvers onto the shared verifier and test required claims across every route family.
2. **Phase 29D, HIGH:** webhook event recording and entitlement mutation are separate transactions, so a failure after recording can suppress retries before credit is granted. Implement atomic event/entitlement updates and authoritative payment reconciliation before live payment enablement.
3. **Phase 29D, BLOCKER for PhonePe:** PhonePe checkout/webhooks are not implemented or live-qualified. PhonePe selection remains fail-closed in current checkout routes and launch gate.
4. **Phase 29E, MEDIUM:** rate-limit-generated 429 responses bypass CORS middleware and omit CORS headers. No authentication bypass was demonstrated; test middleware error responses and preflight behavior.
5. **Phase 29F:** live credentials/account actions and production database/storage deployment evidence are absent. The production launch checker connects to PostgreSQL and writes/removes storage probes, so only run it against an explicitly reviewed target.

### Next phase

**Phase 29B — Auth and Persistence Hardening**

First action: unify auxiliary JWT resolution with the canonical Supabase verifier, preserve ownership checks, and add offline signed-token regressions for missing/expired `exp`, wrong role, issuer, audience, algorithm, and subject on billing, requirements, confirmed-generation, and project routes. Do not run live service checks without the required credentials/account authorization.

---

## Phase 29B - Auth and Persistence Hardening

Status: **IMPLEMENTED AND LOCALLY VALIDATED; NOT A PRODUCTION QUALIFICATION**

### Baseline and scope

- Branch: `phase29`; starting qualified HEAD remains
  `cbd295f5e9028186acbfb14f40c1142e3a003b27`.
- Phase 29A and 29B are checkpointed at
  `abb24feb0209a18f14877c2f8154e24c4dbcffcc` in the existing dirty worktree.
  No qualification tag, deployment, database migration, live credential use,
  external account action, or production write was performed.
- Protected solver, Architectural Brain, Vastu, canonical geometry,
  PlanDocument schema, millimetre units, and immutable project revision behavior
  were not changed.
- The bounded plan is recorded in
  `docs/exec-plans/active/phase29b-auth-persistence-hardening.md`.

### Implementation

- Added one shared FastAPI authentication dependency backed by
  `request.app.state.access_token_verifier`. Project, billing, requirements,
  and confirmed-generation routes now use the same canonical verifier and
  preserve the `401` Bearer challenge.
- The canonical verifier requires expiry, issuer, audience, UUID subject, and
  `role=authenticated`, accepts only ES256/RS256, and now normalizes malformed
  non-finite expiry overflow to the existing authentication failure path.
- Project-scoped billing and requirements operations check current ownership
  before provider construction, requirements mutation, entitlement reads, or
  entitlement mutation. Foreign and missing projects retain concealed `404`
  behavior. Stored requirement identity and current project ownership are both
  required for draft, confirmation, and confirmed-record access.
- Requirements JSON writes use unique same-directory temporary files, flush and
  fsync before `os.replace`, clean only their own temporary file, preserve the
  last readable record on replacement failure, and retain existing
  reconfirmation replacement semantics.
- Generation upload storage now requires an explicitly configured absolute path
  in staging as well as production. Development behavior remains compatible.
- Billing PostgreSQL connections disable prepared statements for transaction
  pooler compatibility.
- The production backup script now uses `AI_VASTU_DATABASE_URL`, requires
  existing absolute storage/output directories, rejects filesystem roots and
  Windows drive-relative rooted paths, keeps output outside both storage roots,
  validates each command artifact, archives requirements plus generation
  uploads, and hashes all three artifacts. The runbook reflects this scope.

### Phase 29B files

- `apps/api/app/auth_dependencies.py` (new)
- `apps/api/app/main.py`
- `apps/api/app/billing_routes.py`
- `apps/api/app/requirements_routes.py`
- `apps/api/app/confirmed_generation_routes.py`
- `apps/api/tests/test_phase29a_runtime.py`
- `apps/api/tests/test_phase29b_auth.py` (new)
- `apps/api/tests/test_phase29b_security_fixtures.py` (new)
- `python/ai_vastu/auth/verifier.py`
- `python/ai_vastu/billing/postgres_repository.py`
- `python/ai_vastu/generation_intake/store.py`
- `python/ai_vastu/requirements/store.py`
- `scripts/backup-production.ps1`
- `docs/runbooks/backup-restore.md`
- `tests/billing/test_postgres_repository_policy.py` (new)
- `tests/generation_intake/test_store.py`
- `tests/requirements/test_store_and_confirmation.py`
- `tests/test_phase29b_backup_policy.py` (new)
- `docs/exec-plans/active/phase29b-auth-persistence-hardening.md` (new)
- `docs/CURRENT_HANDOFF.md`
- `docs/agent-memory/knowledge-graph.json`

`main.py` and `billing_routes.py` also contain the preserved Phase 29A hunks.
The user-owned `AGENTS.md`, Agent OS files, archives, payloads, scripts, and
other pre-existing untracked files remain untouched.

### Independent evidence

- Two independent planners were challenged by Architecture Guardian before the
  coordinator fixed scope. No SQL/RLS migration, payment redesign, pool
  lifecycle redesign, provider change, or protected generation change was
  admitted.
- Fixture Engineer: 11 signed-token/injected-verifier fixtures passed.
- Regression Tester: 52 focused tests and 257 affected API/projects/
  requirements/billing/generation-intake/production tests passed; affected Ruff,
  mypy across 40 source files, and `git diff --check` passed.
- Adversarial Tester: 56 focused tests passed. Its non-finite-expiry and backup
  path findings were fixed and retested. No authentication bypass, cross-user
  access, torn JSON, or temporary-file leak remained.
- Security Reviewer: 109 pre-fix focused/affected tests plus five final backup
  tests passed, with an additional 28/28 invalid ES256 route matrix rejected.
  It accepted local Phase 29B security after the fixes.
- Independent QA: 52 focused tests and 32 additional signed RS256 route probes
  passed; local Phase 29B implementation accepted.
- Release Auditor verified branch `phase29`, the then-current HEAD and peeled
  baseline tags, the disclosed dirty/uncommitted tree, protected-path cleanliness,
  `git diff --check`, and the local-vs-live claims. It accepted this local
  handoff wording and blocked any qualification tag.

Coordinator validation from the final Phase 29B working tree:

- Combined focused Phase 29A/29B integration set: 54 passed before final
  adversarial regressions; final auth/backup regression set: 17 passed.
- `git diff --check`: PASS (Windows LF/CRLF notices only).
- `pnpm validate`: PASS.
- Ruff: PASS.
- mypy: PASS, 200 source files.
- Python: 643 passed, 0 failed, five dependency deprecation warnings.
- Contracts: generated schema/types match authoritative models; one contract
  test passed; generated contract files have no tracked diff.
- Frozen Vastu, constraints, planner, geometry, validation, scoring, revisions,
  exports, generation, requirements, billing, persistence, auth, Phase 25-28,
  and OpenRouter deterministic gates: PASS.
- Web formatting/lint/typecheck: PASS; 26 tests passed; Next.js production build
  passed with all routes generated.
- No PostgreSQL, Supabase/JWKS, OpenRouter, Gemini, PhonePe, Razorpay, real
  `pg_dump`, real archive, restore, or deployed filesystem was exercised.

### Known limitations and launch blockers

1. **Production blocker - database isolation evidence:** migration review does
   not demonstrate RLS/revokes for project/revision and billing tables. This is
   not proof of deployed exposure. A separately reviewed migration/deployment
   step must verify effective `PUBLIC`, `anon`, `authenticated`, and server-role
   grants, plus TLS enforcement, before public deployment.
2. **Phase 29D high:** payment event recording and entitlement mutation remain
   separate commits. A failure after recording can suppress credit application
   on retry. Atomic processing and authoritative reconciliation are required.
3. **Phase 29D blocker:** PhonePe remains unimplemented and fail-closed.
4. **Phase 29E medium:** limiter-generated `429` responses still omit CORS
   headers.
5. **Windows file-store availability:** concurrent readers/replacements can
   raise transient `PermissionError` under Windows sharing semantics. The
   adversarial stress test found no torn JSON or leaked temporary files. Treat
   concurrent Windows requirements-store deployment as unsupported until a
   retry/coordination policy is implemented; Linux production behavior was not
   exercised.
6. Backup tests use offline command stubs. Real dump/archive integrity,
   concurrent-write consistency, encryption, retention, restore, permissions,
   and fault-domain separation remain deployment evidence.

### Next phase

**Phase 29C - Hybrid AI Production Integration**

First action: inspect the qualified OpenRouter text/reasoning and direct Gemini
plan-vision boundaries, then design offline provider failure/timeout/response-
validation fixtures without moving any geometry or feasibility authority into
AI output. Do not use real credentials or live provider accounts without an
explicitly reviewed target.

---

## Phase 29C - Hybrid AI Production Integration

Status: **IMPLEMENTED, COMMITTED, AND LOCALLY VALIDATED; LIVE PROVIDERS BLOCKED BY CREDENTIALS; NOT PRODUCTION QUALIFIED**

### Checkpoint and rollback

- Branch: `phase29`.
- Phase 29C implementation commit:
  `6b770bca1cfa88f8be55ad526d2681c155fe606a`
  (`feat: harden production hybrid AI routing`).
- Rollback point immediately before Phase 29C:
  `a6f59747d00facf2b6387e31a7e4e670ef215ef9`.
- Phase 29A/29B implementation remains checkpointed at
  `abb24feb0209a18f14877c2f8154e24c4dbcffcc`.
- No qualification tag, deployment, migration, production write, payment call,
  database/storage probe, or external account action was performed.

### Runtime architecture and provider policy

- Production configuration explicitly requires OpenRouter for requirements,
  architectural reasoning, soft-Vastu reasoning, Architectural Brain, and
  revisions; persisted Analyze Plan recognition uses direct Gemini.
- OpenRouter remains pinned to development primary
  `deepseek/deepseek-v4-flash-0731:free` and the existing approved free-only
  fallback. Random, paid, unpinned, duplicate, mixed, and cross-provider chains
  fail closed.
- Direct Gemini plan recognition remains pinned to
  `gemini-3.1-flash-lite`, retries only one eligible transient failure, and
  never switches provider/model.
- The retained `/requirements/interpret` visual-attachment compatibility path
  still uses the pinned OpenRouter vision model. That behavior is now documented
  accurately but remains an unresolved launch/product decision; Phase 29C did
  not introduce a composite provider or silently reroute it.
- AI output remains advisory. Direct-Gemini image/PDF envelope, orientation,
  and room observations are forced to confirmation-required and cannot claim
  `USER_CONFIRMED`; deterministic parsing, confirmation, validation, geometry,
  Vastu, hashes, revisions, and billing authority remain unchanged.

### Provider runtime and API hardening

- Added shared typed provider failure categories and validated per-attempt/total
  timeout budgets. OpenRouter and Gemini responses are streamed under a 2 MiB
  decoded-body cap and the shared total deadline, including slow/chunked bodies.
- Provider authentication, rejection, quota, timeout, connection, 5xx,
  malformed JSON, empty content, and schema failures produce fixed sanitized
  internal/API outcomes. Provider bodies, prompts, keys, authorization headers,
  and uploaded bytes are not returned to clients.
- Requirements interpretation and upload validation/storage run off the async
  event loop. Provider failure does not save a requirements draft, append a
  revision, or record successful billing.
- Architectural Brain provider outages remain distinct from deterministic
  candidate rejection; genuine deterministic rejection remains `422`.
- Gemini keys use `x-goog-api-key`, not query parameters.
- Unknown `APP_ENV` values fail closed before development auth/SQLite can be
  selected.
- Plan-analysis POST requests have their own production rate-limit scope.
  Limiter/configuration errors receive CORS headers, TrustedHost remains
  outermost, and outer abuse buckets are keyed by client IP rather than
  rotatable/unverified bearer text.
- JPEG/PNG uploads require exact extension/MIME agreement and Pillow format
  verification with decompression-bomb rejection. PDFs receive bounded header
  plus terminal-`%%EOF` truncation screening. Unknown/extensionless uploads are
  rejected; Pillow remains confined to an explicit media-validation adapter.
- Legacy Phase 27 live output is now explicitly preflight-only with
  `production_qualification=false`.

### Main implementation and evidence files

- Runtime/config: `python/ai_vastu/provider_runtime.py`,
  `python/ai_vastu/openrouter_http.py`, `python/ai_vastu/gemini_http.py`,
  `python/ai_vastu/production/settings.py`,
  `python/ai_vastu/production/middleware.py`,
  `python/ai_vastu/runtime_environment.py`.
- Provider/API boundaries: requirements, plan-intake, Architectural Brain,
  architectural-intelligence, and Vastu provider/error modules plus
  `apps/api/app/main.py`, `apps/api/app/requirements_routes.py`, and
  `apps/api/app/confirmed_generation_routes.py`.
- Upload security: `python/ai_vastu/upload_validation.py`,
  `python/ai_vastu/media_validation_adapter.py`, and generation-intake store/API
  regressions.
- Operations/evidence: `.env.example`, `phase28-hybrid.env.example`,
  `PHASE28_HYBRID_AI.md`, production/final runbooks,
  `scripts/check-phase29c-hybrid.py`, `scripts/check-phase29c-live.py`, and
  corrected Phase 25/27/28 checks.
- New Phase 29C tests/fixtures live under `tests/provider_runtime`,
  `tests/gemini`, `tests/adversarial`, `tests/fixtures/phase29c`, and focused
  requirements/plan-intake/Architectural-Brain/production/API test modules.
  The exact 59-file scope is recorded by the implementation commit above.

### Independent review evidence

- Two independent planners were challenged by Architecture Guardian before the
  coordinator selected the narrow integration. No composite provider, provider
  factory duplication, schema change, or deterministic-authority change was
  admitted.
- Fixture Engineer: 16 fixture tests and 95 combined provider/fixture tests
  passed with secret-free JPG/PNG/PDF and failure matrices.
- Regression Tester: 145 focused, 420 affected provider/API/production, and 139
  deterministic-authority tests passed; thirteen offline subsystem gates passed.
- Adversarial Tester: 22 independent adversarial cases and a 173-test combined
  matrix passed after MIME/extension/signature fixes.
- Security Reviewer: local ACCEPT after response-cap, APP_ENV, limiter identity,
  key transport, and corrupt-upload fixes; final reviewed matrix 216 passed.
- Independent QA: local ACCEPT after slow-stream and false qualification-claim
  fixes; final focused/affected matrix 245 passed. No unresolved BLOCKER, HIGH,
  or MEDIUM QA finding remained.

### Coordinator validation

- `git diff --check`: PASS (Windows LF/CRLF notices only).
- `pnpm validate`: PASS on 2026-09-27.
- Ruff: PASS.
- mypy: PASS across 206 source files.
- Python: 830 passed, 0 failed, five dependency deprecation warnings.
- Contracts: generated schema/types match authoritative models; one contract
  test passed; no tracked contract drift remained.
- Frozen Vastu specification/review/production gates: PASS; bundle hash remains
  `b11b66be61d6436fcaa43c1c5b743c0090051154146d91caf904eb5108546667`.
- Deterministic constraints, planner, geometry, validation, scoring, revisions,
  exports, generation, and all Phase 24-29C offline gates: PASS.
- Web formatting/lint/typecheck: PASS; 26 tests passed.
- Next.js production build: PASS with all routes generated.
- OpenRouter live status: `BLOCKED_CREDENTIALS`.
- Gemini live status: `BLOCKED_CREDENTIALS`.
- The live checker made no provider call because neither credential was present.

### Remaining production blockers and limitations

1. PostgreSQL/Supabase grants, RLS, and production TLS remain unverified live.
2. PhonePe is unimplemented; payment-event and entitlement mutation atomicity,
   idempotency, replay protection, and reconciliation remain Phase 29D work.
3. OpenRouter and Gemini live provider qualification is blocked by credentials.
4. Real backup/archive/restore evidence remains absent.
5. Deployment-isolation and deployed end-to-end evidence remain absent.
6. Concurrent Windows JSON requirements-store deployment remains unsupported
   pending retry/coordination handling.
7. The visual requirements compatibility route decision remains unresolved.
8. IP limiter correctness depends on exact trusted-proxy configuration and
   staging verification; expired rate-window row retention/cleanup must be
   operationalized before production qualification.
9. PDF screening detects truncation/signature failures but is not a full PDF
   structural parser.

### Next phase

**Phase 29D - PhonePe + Payment Atomicity**

First action: inspect the existing billing repository, checkout, webhook, event,
and entitlement transaction boundaries; then design PhonePe-independent checkout
and atomic/idempotent callback processing without changing the frozen pricing
catalog or enabling Razorpay as a production dependency.

---

## Phase 29D - PhonePe + Payment Atomicity

Status: **PASS_LOCAL; LIVE PAYMENT, DATABASE, AND DEPLOYMENT QUALIFICATION OUTSTANDING**

### Checkpoint scope

- Branch: `phase29`; starting HEAD for the final Phase 29D checkpoint is
  `eddd465c9e45bbf0d32b604b245b8667b7a3b935`.
- The launch catalog is server-authoritative at free first generation, INR 399
  single-project access, INR 3,399 ten-project access, INR 2,499 monthly, and
  INR 24,999 yearly.
- Authenticated checkout intent is persisted before provider I/O. PhonePe
  Standard Checkout v2 uses an isolated bounded adapter, fixed provider
  endpoints, server-side credentials, and sanitized failures.
- PhonePe callback/webhook input is an authenticated reconciliation trigger,
  not settlement authority. Entitlement is granted only after authoritative
  provider order-status confirmation.
- Provider event recording, monotonic payment-order state, and entitlement
  mutation share one atomic repository transaction with duplicate, replay,
  stale-state, and concurrent-settlement protection. The reconciliation command
  uses the same settlement path.
- Monthly and yearly products remain fail-closed for checkout because Standard
  Checkout is not represented as recurring AutoPay. Razorpay remains optional
  and cannot become a production dependency for PhonePe.
- Production configuration, payment-specific rate limits, checkout/status/
  webhook routes, RLS/revocation migration policy, billing UI, fixtures,
  adversarial tests, runbooks, and launch gates were updated together.
- Agent OS routing, orchestration, protected-contract, memory, QA, testing, and
  release-review guidance is included as repository governance. GPT-5.6 Sol
  Medium is the fixed development-agent profile unless the user approves a
  different profile.
- Canonical PlanDocument, deterministic geometry, solver, frozen Vastu,
  project-revision, generation, and export authority were not changed.

### Final local evidence

- Python: **940 passed**.
- Web: **32 passed**.
- Ruff: **PASS**.
- mypy: **PASS across 208 source files**.
- Formatting, lint, TypeScript typecheck, and production build: **PASS**.
- Phase 29C gate: **PASS**.
- Phase 29D gate: **PASS**.
- `git diff --check`: **PASS**; Windows LF/CRLF notices only.
- Security review: **no unresolved BLOCKER or HIGH finding**.
- Independent QA corrections are complete. The corrected Phase 29D tree is the
  tree covered by the final local validation evidence.
- The user directed continuation from this GREEN checkpoint without rerunning
  Phase 29A-29D validation; the counts above are preserved checkpoint evidence,
  not a newly repeated validation run.

### Qualification boundary

Phase 29D is a local checkpoint, not a production qualification. The following
remain outstanding and must not be converted into PASS without live evidence:

1. Live PhonePe sandbox checkout, callback/webhook delivery, pending/success/
   failure behavior, replay handling, reconciliation, and exactly-once
   entitlement evidence.
2. Live PostgreSQL/Supabase TLS, grants, ownership isolation, applicable RLS,
   migrations, revision persistence, backup, and restore evidence.
3. Live Supabase/JWT, production CORS/rate-limit, OpenRouter, and direct Gemini
   qualification.
4. Deployment-isolated end-to-end workflow evidence.

No real-money transaction, production deployment, database mutation, external
account action, or production-qualified tag is authorized by this checkpoint.

### Next phase

**Phase 29E - Live / Deployment End-to-End Qualification**

First action: audit available deployment configuration and credential presence
without exposing secret values or making write-producing live calls. Complete
all safe local preparation, then classify each external gate strictly as
`PASS_LOCAL`, `PASS_LIVE`, `BLOCKED_CREDENTIALS`, `BLOCKED_HUMAN_ACTION`,
`BLOCKED_EXTERNAL_SERVICE`, or `FAIL`.

---

## Phase 29E - Development E2E Qualification

Status: **PASS_LOCAL FOR THE DEVELOPMENT WORKFLOW; LIVE EXTERNAL QUALIFICATION REMAINS BLOCKED**

### Development payment boundary

- `APP_ENV=development`.
- PhonePe and Razorpay are disabled. No payment credential, network call,
  callback, webhook, sandbox flow, or real-money transaction was used.
- The existing billing bypass was enabled explicitly only inside the isolated
  E2E test. Existing negative tests prove it remains unavailable in staging and
  production.
- PhonePe and Razorpay production implementations and security tests remain
  intact.
- PhonePe live qualification: `BLOCKED_HUMAN_ACTION`.
- Razorpay live qualification: `BLOCKED_HUMAN_ACTION`.
- These deferred payment gates are expected and are not Phase 29E failures.

### Local workflow and correction

The new fixture-backed development workflow E2E exercises:

auth -> project creation -> JPG/PNG/PDF intake -> fixture plan recognition ->
human confirmation -> fixture requirements interpretation -> confirmed program
-> real deterministic candidate generation -> hard validation -> Vastu scoring
-> selection -> immutable persistence/reload -> revision -> PDF export ->
development billing bypass.

PhonePe and Razorpay methods are patched with call-failing tripwires. The passed
workflow test therefore provides direct evidence that this route sequence makes
no payment-provider call. This is not a deployed, PostgreSQL, Supabase, or live-
provider E2E.

The first run exposed a real candidate-selection API defect: valid canonical
PlanDocument JSON was rejected because the nested document was validated in
Python-strict mode directly from an HTTP object. The route now accepts the same
request shape but parses the nested canonical document with
`PlanDocument.model_validate_json`, matching the established revision endpoint.
No PlanDocument schema, migration, geometry, hash, Vastu, or solver rule changed.

A second focused regression proves malformed canonical-plan input is rejected
before the billing repository is created or a payment-provider method can be
called.

Phase 29E files changed:

- `apps/api/app/confirmed_generation_routes.py`
- `apps/api/tests/test_phase29e_development_e2e.py`
- `docs/exec-plans/active/phase29e-live-deployment-qualification.md`
- `docs/CURRENT_HANDOFF.md`

### Validation evidence

- Development E2E file: **2 passed** (complete local workflow and malformed-
  selection rejection).
- Focused auth/JWT, ownership, persistence, uploads, exports, provider-runtime,
  production-settings, rate-limit, backup-safeguard, and project-policy matrix:
  **224 passed**.
- Additional database-policy and hybrid-provider-fixture matrix: **29 passed**.
- Ruff on Phase 29E code/test files: **PASS**.
- mypy on Phase 29E code/test files: **PASS**.
- No Phase 29A-29D broad gate was rerun.
- No external database, Supabase, OpenRouter, Gemini, payment, deployment, or
  backup/restore service was contacted.
- PostgreSQL/Supabase policy, JWT, AI adapter, payment, and backup evidence is
  fixture/static/local safeguard evidence only. It does not qualify a live
  runtime, PostgreSQL dump/restore, deployed RLS/grants/TLS, or provider path.
- Independent QA, architecture, and release review accepted these scoped local
  gates while rejecting any production-qualified or release-ready claim.

### Remaining Phase 29E gates

- PostgreSQL connectivity/TLS, deployed grants/RLS/migrations, live ownership,
  and revision persistence: `BLOCKED_CREDENTIALS`.
- Supabase/JWT live configuration and two-user deployed denial:
  `BLOCKED_CREDENTIALS`.
- OpenRouter live: `BLOCKED_CREDENTIALS`.
- Direct Gemini JPG/PNG/PDF live: `BLOCKED_CREDENTIALS`.
- Real backup creation: `BLOCKED_CREDENTIALS`.
- Disposable restore drill, deployed CORS/rate limits, and deployment isolation:
  `BLOCKED_HUMAN_ACTION`.
- Deployed production-equivalent E2E: `BLOCKED_CREDENTIALS`.
- Live payments: `BLOCKED_HUMAN_ACTION` by explicit development policy.

No gate is `PASS_LIVE`. No production-qualified tag is justified. Git metadata
remains intentionally untouched in the managed read-only sandbox.

### Phase 29E staging preparation after checkpoint

- Phase 29D authoritative local checkpoint: `63d7a68`.
- Phase 29E authoritative local checkpoint:
  `e6b0d1266d6803964255dc86c9dd66527e317486`.
- Added an offline-only staging preflight that validates configuration shape,
  verified-TLS intent, isolated durable roots, production-profile guards,
  disabled payments, absent payment-provider configuration, and browser/API
  target consistency without DNS, HTTP, database, JWKS, or provider calls.
- The preflight output contains variable names and fixed findings only, never
  configured values, and can report at most `PASS_LOCAL`.
- The preflight is configuration-structure evidence only; target isolation,
  distinct test identities, approved backup/restore roots, and service behavior
  remain human/live gates. An evidence validator rejects unsupported
  `PASS_LIVE` entries and keeps payments `BLOCKED_HUMAN_ACTION`.
- Added a blocked-by-default staging evidence template covering database/auth,
  AI, backup/restore, non-payment E2E, cleanup, and deferred payments.
- No local Phase 29A-29E suite was rerun for this preparation. Only the new
  focused preflight tests and targeted static checks were run.
- Post-checkpoint preparation files:
  - `python/ai_vastu/production/staging_preflight.py`
  - `scripts/check-phase29e-staging-preflight.py`
  - `scripts/validate-phase29e-staging-evidence.py`
  - `tests/production/test_phase29e_staging_preflight.py`
  - `docs/exec-plans/templates/phase29e-staging-evidence.json`
  - `docs/exec-plans/active/phase29e-staging-setup.md`
  - `docs/CURRENT_HANDOFF.md`
- Focused preflight tests: **14 passed**.
- Targeted Ruff: **PASS**.
- Targeted mypy: **PASS across 4 source files**.
- The egress tripwire forbids socket, DNS, HTTP-client, and PostgreSQL connection
  entry points while exercising the complete structural preflight.
- No external service or payment provider was contacted. Protected solver,
  Vastu, geometry, canonical-unit, revision, and AI-authority contracts were
  unchanged.
- Live database/Supabase/OpenRouter/Gemini/backup gates remain
  `BLOCKED_CREDENTIALS`; deployment, restore, and payment gates remain
  `BLOCKED_HUMAN_ACTION`; no `PASS_LIVE` claim is made.

### Phase 29E provider qualification - 2026-09-30

Status: **DIRECT GEMINI PASS_LIVE; OPENROUTER FAIL; PHASE 29C NOT LIVE-QUALIFIED**

- `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, and all Phase 29E hybrid-provider
  switches were present. Secret values were not printed or persisted.
- The recovered execution history contained no completed candidate request, so
  each bounded OpenRouter candidate was submitted exactly once with the real
  `RequirementDraft` schema and advisory/confirmation-required checks.
- Compatibility results:
  - `nvidia/nemotron-3-super-120b-a12b:free`: rejected after 33,813 ms;
    OpenRouter accepted the request, but the result failed `RequirementDraft`
    validation.
  - `qwen/qwen3.8-27b:free`: rejected after 70,796 ms; JSON and schema parsing
    completed, but the plot-width advisory contract was incorrect.
  - `google/gemma-4-31b-it:free`: rejected after 1,360 ms with sanitized HTTP
    502 / unavailable evidence.
  - `nvidia/nemotron-3-ultra-550b-a55b:free`: `PASS_LIVE` after 114,390 ms;
    real schema validation, unfenced JSON, advisory semantics, and required
    confirmations passed.
- No evidence-qualified replacement primary emerged from the three primary
  candidates. The DeepSeek primary pin was therefore not changed. Nemotron
  Ultra remains the pinned fallback based on its successful live probe; no
  paid or random fallback was used.
- The canonical `python scripts/check-phase29c-live.py` command was run exactly
  once. Direct Gemini passed, while OpenRouter returned sanitized
  `request_rejected`; the current primary-to-fallback path did not complete.
  The canonical Phase 29C live gate is therefore `FAIL`, not `PASS_LIVE`.
- A separate direct-Gemini plan-intake matrix passed exactly once per format:
  PNG in 6,218 ms, JPEG in 7,641 ms, and PDF in 6,078 ms. Each used
  `gemini-3.1-flash-lite`, recognized four synthetic rooms, retained reference
  identity, and kept envelope, orientation, and room geometry confirmation-
  required.
- Focused provider/runtime/error-boundary pytest passed using the established
  workspace-local `tmp_path` fixture. Initial setup attempts encountered only
  the documented managed-Windows pytest temp ACL failure. Ruff passed, mypy
  passed for the three affected provider/runtime modules, and `git diff
  --check` passed with LF/CRLF notices only.
- The previously validated OpenRouter model-unavailable fallback patch and
  Gemini identity-content-encoding/decoding patch remain intact. No payment,
  Supabase, deployment, CORS, backup, restore, Git-index, commit, or tag action
  was performed.

Next action: do not change the production primary without a new bounded live
candidate that passes the full compatibility contract. Investigate the single
canonical OpenRouter `request_rejected` result only in a separately authorized
provider-debugging pass; do not infer Phase 29C qualification from the
successful standalone Nemotron Ultra or Gemini evidence.

### Phase 29E rotated-provider requalification - 2026-10-01

Status: **FAIL - OPENROUTER REQUEST REJECTED; GEMINI AUTHENTICATION FAILED**

- The rotated `OPENROUTER_API_KEY` and `GEMINI_API_KEY` were present, and all
  seven hybrid-provider switches retained the required OpenRouter text/reasoning
  and direct-Gemini plan-recognition routing. No credential value or derivative
  was printed or persisted.
- Each bounded OpenRouter model received exactly one fresh schema-realistic
  compatibility request under the rotated credential:
  - `nvidia/nemotron-3-super-120b-a12b:free`: rejected after 111,875 ms because
    the response failed real `RequirementDraft` validation;
  - `qwen/qwen3.8-27b:free`: rejected after 640 ms with HTTP 429 /
    `rate_limited`;
  - `google/gemma-4-31b-it:free`: rejected after 860 ms with HTTP 401 /
    `authentication`;
  - `nvidia/nemotron-3-ultra-550b-a55b:free`: `PASS_LIVE` after 71,437 ms with
    unfenced JSON, real schema validation, advisory semantics, five questions,
    three warnings, and confirmation-required observations.
- No replacement-primary candidate qualified. The DeepSeek primary pin remains
  unchanged, and Nemotron Ultra remains the only live-compatible pinned
  fallback. No paid or random route was used.
- The canonical `python scripts/check-phase29c-live.py` command was run exactly
  once under the rotated credentials. OpenRouter returned sanitized
  `request_rejected`; direct Gemini returned sanitized `authentication`.
  Phase 29C remains `FAIL` and is not live-qualified.
- The PNG/JPEG/PDF Gemini matrix was not repeated after the canonical direct-
  Gemini call conclusively failed authentication. The 2026-09-30 media evidence
  remains valid historical model/path evidence, but it does not qualify the
  current rotated Gemini credential.
- No source, model pin, test, payment, Supabase, deployment, CORS, backup,
  restore, or Git metadata was changed by this requalification. The existing
  OpenRouter fallback and Gemini decoding patches remain intact.

Next action: verify or rotate the current Gemini credential through the approved
secret mechanism, then run one minimal direct-Gemini call before any media
matrix. Investigate OpenRouter's canonical `request_rejected` result in a
separately bounded provider-debugging pass; do not promote any rejected primary
candidate.

### Phase 29C/29E NVIDIA NIM-only migration - 2026-10-01

Status: **PASS_LOCAL; LIVE QUALIFICATION BLOCKED_CREDENTIALS; PRODUCTION
ENTITLEMENT BLOCKED_HUMAN_ACTION**

- The user explicitly superseded the Phase 29C hybrid provider architecture.
  All six active runtime switches now use `nvidia_nim`; OpenRouter and direct
  Gemini remain source-available legacy adapters but are inactive and rejected
  by the production profile.
- Active contract: `NVIDIA_API_KEY` and fixed base URL
  `https://integrate.api.nvidia.com/v1`. The production/staging profile does not
  require `OPENROUTER_API_KEY` or `GEMINI_API_KEY`.
- Exact pins: primary `nvidia/nemotron-3.5-lightning-30b-a3b`, fallback
  `nvidia/nemotron-3-ultra-550b-a55b`, and vision
  `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`.
- Added a fixed-host NVIDIA client with exact model allowlists, bounded total
  budget and response size, sanitized authentication/rate-limit/timeout/
  invalid-response errors, and an exact primary-to-fallback chain with no
  random or paid routing.
- Added NVIDIA adapters for requirements, architectural intelligence, soft
  Vastu reasoning, Architectural Brain, revisions, and plan intake. Provider
  identity and content hashes are application-owned. AI-derived envelope,
  orientation, and room observations remain confirmation-required.
- PNG and JPEG use the pinned NVIDIA vision model. PDF is rendered locally with
  bounded `pypdfium2` page/dimension/pixel/byte/deadline limits; raw PDFs are
  never sent to a cloud provider. `/requirements/interpret` reference files are
  filename context only in the NVIDIA text adapter; persisted Analyze Plan is
  the visual-recognition path.
- Deterministic geometry, frozen Vastu, validators, PlanDocument, project/
  revision semantics, auth/ownership, Supabase, exports, billing/payments,
  production security boundaries, and soft wet-stack behavior were unchanged.
- Official NVIDIA hosted catalog metadata was checked on 2026-10-01 for all
  three exact IDs. Hosted availability does not prove Vastudraw schema
  compatibility and does not grant production entitlement.

Validation evidence:

- NVIDIA client/adapters/media/plan-intake: **80 passed**.
- Adversarial Phase 29C provider boundaries: **26 passed**.
- Production settings/preflight/operations: **171 passed**.
- Affected requirements, Architectural Brain/intelligence, plan intake,
  provider runtime, soft-Vastu, and API error mapping: **153 passed**.
- Phase 29C API provider error mapping alone: **13 passed**.
- Complete Python suite, including both Phase 29E development E2E tests:
  **1,047 passed** with five deprecation warnings.
- `pnpm phase29c:check`: **PASS_LOCAL**, including local PDF rendering, factory
  routing, secret redaction, and zero network calls.
- Phase 29E staging preflight: **BLOCKED_CREDENTIALS** in the unloaded local
  environment; it reports `nvidia_text` and `nvidia_vision`, not legacy live
  gates. Payments, restore/deployment, and NVIDIA production entitlement remain
  `BLOCKED_HUMAN_ACTION`.
- Phase 29E evidence-template validator: **PASS_LOCAL**.
- Phase 27 current-production gate, Phase 28 historical hybrid gate, Phase 29C
  NVIDIA gate, Phase 29D offline gate, and the Phase 26 historical Python gates:
  **PASS**.
- Ruff across Python/API/tests/scripts: **PASS**. Full mypy: **PASS across 217
  source files**. `git diff --check`: **PASS** with only existing LF/CRLF
  notices.
- `pnpm validate` passed Python lint, full mypy, all 1,047 Python tests,
  contracts, frozen Vastu, deterministic solver/geometry/validation/scoring,
  revision, web/editor (32 tests), export, intake, requirements, Phase 24/25/26,
  billing, UI, persistence, auth, MVP, and Phase 27/28/29C/29D checks. Its
  remaining recursive workspace tail stopped at `format:check` because the host
  has Node 20.11.1 (the repository requires Node >=24) and pnpm child-process
  spawn returned Windows `EPERM`; this is an environment blocker, not a passing
  full `pnpm validate` claim.

Live evidence:

- `NVIDIA_API_KEY` was not visible to the process. The canonical checker made no
  provider call and reported `BLOCKED_CREDENTIALS` for text primary, text
  fallback, vision PNG, vision JPEG, vision PDF path, and the aggregate Phase
  29C gate. No `PASS_LIVE` claim is made.
- No OpenRouter, Gemini, PhonePe, or Razorpay request was made.
- The project `.venv` does not yet contain newly declared `pypdfium2==5.13.0`;
  a bounded pip attempt produced no output and was interrupted. Deterministic
  tests ran with the already-installed system package. A normal dependency
  sync is required before using the project `.venv` directly.
- `NVIDIA_NIM_PRODUCTION_ENTITLEMENT = BLOCKED_HUMAN_ACTION` until an
  appropriate NVIDIA AI Enterprise or production endpoint arrangement is
  explicitly available, irrespective of any future hosted development pass.

No commit, tag, Git index, payment configuration, or payment workflow was
created or modified by this migration.

### Phase 29E NVIDIA qualification continuation - 2026-10-01

Status: **PASS_LOCAL; LIVE QUALIFICATION BLOCKED_CREDENTIALS; PRODUCTION
ENTITLEMENT BLOCKED_HUMAN_ACTION**

- Reverified the three exact model pins against current official NVIDIA catalog
  evidence before application qualification. All remain advertised as hosted
  endpoints; this is availability evidence only.
- Added a fixed-host, bearer-authenticated, bounded `/v1/models` inventory gate
  to the canonical NVIDIA client. The live checker now requires all three exact
  IDs before making any completion request. Missing, aliased, malformed,
  oversized, authentication, timeout, rate-limit, and availability failures
  fail closed with sanitized categories.
- Completion responses must report the exact requested model ID in NVIDIA's
  response envelope. Missing IDs and uppercase, suffix, alias, or different-
  model responses fail closed instead of receiving application-owned
  provenance for a model that was not actually reported.
- The live sequence is now inventory -> primary requirements text -> exact
  fallback text -> PNG -> JPEG -> locally rendered PDF. It stops on the first
  failure. Primary text and vision use the actual runtime factories, so the
  qualification exercises the active `nvidia_nim` routing rather than only
  directly constructed adapters.
- Updated the two active Phase 29E operator plans to require the NVIDIA-only
  profile and to keep OpenRouter/Gemini credentials out of the qualification
  child process. Legacy adapters remain source-available but inactive.
- The exact `pypdfium2==5.13.0` package is available in the system Python site
  packages. Two bounded installation attempts into `.venv` hung without
  download output and were interrupted. Local qualification therefore used
  the project venv with that exact system package appended to `PYTHONPATH`; a
  normal venv dependency sync remains required.
- Focused NVIDIA client/adapter, provider-media, plan-intake, adversarial
  provider-boundary, production settings/operations/preflight, and provider
  runtime tests: **261 passed**.
- `pnpm phase29c:check`: **PASS_LOCAL**, with real NVIDIA factory routing,
  local PDF rendering, secret redaction, and zero network calls.
- Ruff across Python/API/tests/scripts: **PASS**. Full mypy: **PASS across 217
  source files**. The PDFium dependency is isolated with a narrow
  `ignore_missing_imports` override because upstream does not publish typing
  metadata; no other module is relaxed.
- Repository-wide `pnpm validate` passed Ruff, full mypy, all **1,064 Python
  tests** (five deprecation warnings), schema generation/drift, frozen Vastu,
  constraints, planner, geometry, validation, and scoring. It then stopped at
  `projects:check` because this managed Windows account cannot open or clean a
  Python `TemporaryDirectory`, even when TEMP/TMP points inside the workspace.
  The same revision surface passed within the 1,064-test suite. The remaining
  validation tail was not reached, so this is not a full `pnpm validate` pass.
- `git diff --check`: **PASS** with existing LF/CRLF notices only. Durable
  memory JSON parses successfully.
- The execution environment inherited by commands still has the six legacy
  provider switches (`openrouter` text/reasoning and `gemini` plan recognition)
  and does not expose `NVIDIA_API_KEY`. The canonical live checker was invoked
  in an explicit NVIDIA-only child environment with legacy credentials removed;
  it made zero provider calls and reported `BLOCKED_CREDENTIALS` for inventory,
  requirements text, vision, and PDF-path qualification. No `PASS_LIVE` claim
  is made. A future aggregate success label is explicitly scoped to
  `REQUIREMENTS_VISION`; it does not claim live schema qualification for every
  NVIDIA-backed advisory adapter.
- OpenRouter, Gemini, payments, Git metadata, canonical geometry, frozen Vastu,
  revisions, auth/ownership, and deterministic authority were not modified or
  exercised.

Next action: make `NVIDIA_API_KEY` visible to the command execution environment,
synchronize `.venv`, and run the canonical live checker once in an explicit
NVIDIA-only child environment. Keep NVIDIA production entitlement separately
`BLOCKED_HUMAN_ACTION` even if every hosted development/staging probe passes.

### Phase 29E NVIDIA bounded live qualification attempt - 2026-10-01

Status: **BLOCKED_CREDENTIALS; NO PASS_LIVE CLAIM; PRODUCTION ENTITLEMENT
BLOCKED_HUMAN_ACTION**

- Attempt timestamp: `2026-10-01T17:21:10.7038203+05:30`.
- The project `.venv` now imports exactly `pypdfium2==5.13.0`; the previous
  dependency-sync blocker is resolved.
- Before the live command, process, Windows user, and Windows machine
  environment scopes were checked without printing any secret value. None
  exposed a non-empty `NVIDIA_API_KEY`. The command process still inherited
  the six legacy provider-switch values rather than the NVIDIA-only profile.
- The canonical checker was run once with the fixed NVIDIA base URL, all three
  exact model pins, and all six provider switches explicitly set to
  `nvidia_nim`. `OPENROUTER_API_KEY` and `GEMINI_API_KEY` were removed from the
  child environment before execution.
- Guarded result, exit code `2`:
  - model inventory: `BLOCKED_CREDENTIALS`;
  - primary requirements text: `BLOCKED_CREDENTIALS`;
  - exact fallback requirements text: `BLOCKED_CREDENTIALS`;
  - vision PNG: `BLOCKED_CREDENTIALS`;
  - vision JPEG: `BLOCKED_CREDENTIALS`;
  - locally rendered PDF path: `BLOCKED_CREDENTIALS`;
  - aggregate `PHASE29C NVIDIA_NIM`: `BLOCKED_CREDENTIALS`.
- The credential guard stopped before the NVIDIA inventory request, so zero
  NVIDIA completion or inventory calls were made. OpenRouter, Gemini, PhonePe,
  Razorpay, deployment, database, backup, and restore paths were not called.
- No model-specific diagnosis is applicable because no live model was reached.
  No source, architecture, model pin, or Git metadata was changed.

Next action: expose the reviewed `NVIDIA_API_KEY` to the same command execution
environment, confirm the NVIDIA-only switches are visible there, and rerun the
same canonical checker. Do not broaden the run or change architecture if an
individual live model then fails; diagnose only that exact model.

### Phase 29E NVIDIA live-evidence policy correction - 2026-10-01

Status: **PASS_LOCAL; PARTIAL_LIVE / NOT YET QUALIFIED; PRODUCTION ENTITLEMENT
BLOCKED_HUMAN_ACTION**

This continuation records manual PowerShell evidence supplied by the human
operator. Codex did not receive `NVIDIA_API_KEY` and made no NVIDIA, OpenRouter,
Gemini, payment, Supabase, database, or other live-service request.

Exact evidence classification:

| Gate | Status |
|---|---|
| NVIDIA inventory | `PASS_LIVE` |
| NVIDIA Ultra text | `PASS_LIVE` |
| NVIDIA Lightning text | `NOT_QUALIFIED_TIMEOUT` |
| NVIDIA Nano Omni PNG | `PASS_LIVE` |
| NVIDIA Nano Omni JPEG | `BLOCKED_PROVIDER_UNAVAILABLE` |
| NVIDIA Nano Omni PDF local render | `PASS_LOCAL` |
| NVIDIA Nano Omni PDF inference | `NOT_QUALIFIED` |
| PHASE29C NVIDIA_NIM | `PARTIAL_LIVE / NOT YET QUALIFIED` |
| Production NVIDIA entitlement | `BLOCKED_HUMAN_ACTION` |

Root cause and policy correction:

- The old `NVIDIA TEXT PRIMARY` probe called the ordinary requirements factory,
  whose policy was Lightning followed by Ultra. A Lightning failure could
  therefore call Ultra under the primary label and only fail afterward at the
  provenance assertion. The label did not isolate the selected primary.
- Ultra is now the sole active text/reasoning primary:
  `nvidia/nemotron-3-ultra-550b-a55b`. The active text chain is a singleton.
- Lightning is retained only as historical `NOT_QUALIFIED_TIMEOUT` evidence.
  It is excluded from the active allowlist, inventory requirement, production
  settings, examples, runtime chain, and live completion sequence. A populated
  legacy `AI_VASTU_NVIDIA_FALLBACK_MODEL` fails configuration closed.
- The canonical live checker inventories only the two active IDs (Ultra and
  Nano Omni), then probes Ultra requirements, Nano Omni PNG, Nano Omni JPEG,
  local PDF-to-PNG rendering, and Nano Omni rendered-PDF inference. It has no
  text-fallback probe and stops on the first failure.
- Ultra keeps the request shape that passed the real `RequirementDraft`
  contract: strict JSON prompting and application schema validation without the
  Lightning-only/unsupported `response_format` request field.

Retry and diagnostics:

- NVIDIA hosted inference permits at most one immediate retry of the exact same
  model, for two total attempts, only after `unavailable` or `timeout`.
- Both attempts share the existing 240-second total deadline; every attempt is
  capped by the remaining total budget. Deadline exhaustion stops before a
  second call.
- Authentication, request rejection, rate limiting, malformed/oversized output,
  strict-JSON failure, application/schema validation failure, and returned-model
  provenance failure are never retried. No model or provider substitution is
  possible.
- Qualification failures emit only fixed role, exact attempted model ID,
  `ProviderFailureCategory`, allowlisted stage, attempt count, and a validated
  numeric HTTP status when present. Prompts, user content, credentials,
  authorization headers, raw response bodies, and parsed model output are not
  emitted.
- HTTPX exposes per-operation transport timeouts rather than an asynchronously
  preemptible whole-request wall clock. The application total deadline remains
  authoritative for retry admission, streaming checks, validation, and final
  acceptance; an in-flight OS transport operation is separately bounded by the
  120-second attempt timeout.
- The PDF architecture is unchanged: bounded local `pypdfium2` rendering emits
  PNG pages and raw PDF bytes never cross the provider boundary. The verified
  renderer pass is not classified as a provider-inference pass or defect.

Files changed by this continuation:

- provider/policy: `python/ai_vastu/nvidia_nim_http.py`,
  `python/ai_vastu/production/settings.py`,
  `python/ai_vastu/production/staging_preflight.py`;
- gates/profiles: `scripts/check-phase29c-live.py`,
  `scripts/check-phase29c-hybrid.py`, `scripts/check-phase27-final-release.py`,
  `.env.example`, `.env.production.example`,
  `phase29-nvidia-nim.env.example`;
- tests: `tests/nvidia_nim/test_http.py`,
  `tests/nvidia_nim/test_nvidia_nim_http.py`,
  `tests/production/test_phase29c_operations.py`,
  `tests/production/test_settings.py`,
  `tests/production/test_openrouter_settings.py`,
  `tests/production/test_phase29e_staging_preflight.py`, and
  `tests/adversarial/test_phase29c_provider_boundaries.py`;
- operator/architecture records:
  `docs/architecture/phase29-nvidia-nim-runtime.md`,
  `docs/runbooks/production-launch.md`,
  `docs/exec-plans/active/phase29c-nvidia-nim-only.md`,
  `docs/exec-plans/active/phase29e-live-deployment-qualification.md`,
  `docs/exec-plans/active/phase29e-staging-setup.md`,
  `docs/agent-memory/knowledge-graph.json`, and this handoff.

No change was made to `pdf_render_adapter.py`, frozen Vastu rules, deterministic
OR-Tools geometry, canonical `PlanDocument` contracts, billing production
security, payments, Supabase, or Git metadata.

Local validation:

- focused NVIDIA/provider-media/plan-intake/settings/preflight/release wiring:
  **225 passed** after independent review added three explicit one-attempt
  strict-JSON/provenance regression cases;
- broader affected requirements, plan-intake, Architectural Brain,
  architectural-intelligence, soft-Vastu, adversarial provider-boundary, API
  error, and production suites: **385 passed**, two deprecation warnings;
- full Python application suite before those three test-only review additions:
  **1,072 passed**, five deprecation warnings; the final 225-test focused gate
  passed all three additions without an implementation change;
- `pnpm phase29c:check`: **PASS_LOCAL**, factory routing and local PDF rendering
  exercised with zero network calls and secret redaction;
- Ruff across `python`, `apps/api`, `tests`, and `scripts`: **PASS**;
- mypy across `python` and `apps/api/app`: **PASS across 217 source files**;
- `git diff --check`: **PASS**, with existing LF/CRLF notices only;
- memory graph validation: **PASS**, 20 nodes and 17 edges;
- `pnpm validate`: Python lint, mypy, all **1,072** Python tests, contract
  generation/drift, frozen Vastu, constraints, planner, geometry, validation,
  and scoring passed. The gate then stopped at `projects:check` because the
  managed Windows account cannot open/clean its SQLite `TemporaryDirectory`,
  including with workspace-local `TEMP/TMP`. The remaining recursive tail was
  not reached, so this is not a full `pnpm validate` pass. Node is also
  v20.11.1 while the repository requires Node >=24.

Manual final bounded live command (run only from the operator shell that already
holds the reviewed NVIDIA credential; the command neither reads nor prints its
value):

```powershell
$env:AI_VASTU_REQUIREMENTS_PROVIDER = "nvidia_nim"
$env:AI_VASTU_ARCHITECT_PROVIDER = "nvidia_nim"
$env:AI_VASTU_VASTU_PROVIDER = "nvidia_nim"
$env:AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER = "nvidia_nim"
$env:AI_VASTU_REVISION_PROVIDER = "nvidia_nim"
$env:AI_VASTU_PLAN_RECOGNITION_PROVIDER = "nvidia_nim"
$env:AI_VASTU_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
$env:AI_VASTU_NVIDIA_PRIMARY_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
$env:AI_VASTU_NVIDIA_VISION_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
$env:AI_VASTU_NVIDIA_ATTEMPT_TIMEOUT_SECONDS = "120"
$env:AI_VASTU_NVIDIA_TOTAL_TIMEOUT_SECONDS = "240"
$env:AI_VASTU_NVIDIA_RETRY_DELAY_SECONDS = "0"
$env:AI_VASTU_NVIDIA_MAX_RETRY_AFTER_SECONDS = "0"
Remove-Item Env:AI_VASTU_NVIDIA_FALLBACK_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:OPENROUTER_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
& .\.venv\Scripts\python.exe scripts\check-phase29c-live.py
```

Do not infer overall NVIDIA or production qualification from a partial rerun.
Every required completion stage must pass in the canonical sequence, while
production entitlement remains independently `BLOCKED_HUMAN_ACTION`.

### Phase 29E Nano Omni strict-JSON request hardening - 2026-10-02

Status: **PASS_LOCAL; PARTIAL_LIVE / NOT YET QUALIFIED; PRODUCTION ENTITLEMENT
BLOCKED_HUMAN_ACTION**

Codex made no NVIDIA, OpenRouter, Gemini, payment, Supabase, database, or other
live-service call. `NVIDIA_API_KEY` remained unavailable and was not inspected.

Latest operator-supplied canonical live classification remains:

| Gate | Status |
|---|---|
| NVIDIA model inventory | `PASS_LIVE` |
| NVIDIA Ultra text | `PASS_LIVE` |
| NVIDIA Nano Omni PNG | `NOT_QUALIFIED_STRICT_JSON` |
| NVIDIA Nano Omni JPEG | `BLOCKED_PROVIDER_503` |
| NVIDIA Nano Omni PDF local render | `PASS_LOCAL` |
| NVIDIA Nano Omni PDF inference | `NOT_QUALIFIED` |
| PHASE29C NVIDIA_NIM | `PARTIAL_LIVE` |
| Production NVIDIA entitlement | `BLOCKED_HUMAN_ACTION` |

Root cause and bounded correction:

- The current Nano Omni plan-recognition call omitted
  `chat_template_kwargs.enable_thinking`. NVIDIA documents reasoning as enabled
  by default for this model; reasoning/prose could therefore precede the final
  answer in `message.content`, which Vastudraw correctly rejected at the
  `strict_json` stage after one attempt.
- `NvidiaNimClient.complete_validated_json` now exposes only a dedicated
  `disable_thinking: bool` option. Non-booleans fail before HTTP, and `True` is
  permitted only for the exact pinned Nano Omni vision singleton chain. There
  is no arbitrary `extra_body` or `chat_template_kwargs` mapping passthrough.
- NVIDIA Nano Omni plan recognition explicitly opts in. The exact added request
  field is `"chat_template_kwargs":{"enable_thinking":false}`. No secrets,
  prompts, user content, or raw plan bytes are part of this fixed field.
- Ultra and every default text request retain their prior body shape. No output
  stripping, Markdown/prose cleanup, INVALID_RESPONSE retry, timeout expansion,
  model fallback, or provider fallback was added.
- Strict JSON parsing, `PlanRecognitionDraft` validation, returned-model
  provenance, project/intake identity, content hashing, confirmation-required
  normalization, sanitized diagnostics, PNG/JPEG data URIs, and bounded local
  PDF-to-PNG rendering remain unchanged.

`response_format` decision:

- Current official NVIDIA Nano Omni model/API documentation establishes the
  request-side `chat_template_kwargs.enable_thinking=false` control and shows
  JSON prompting examples, but the hosted Nano Omni endpoint documentation
  reviewed on 2026-10-02 does not establish support for
  `response_format={"type":"json_object"}`. Searches within the official model
  card, hosted endpoint page, and Nano Omni API page found no `response_format`
  contract. Lightning behavior was not generalized to Nano Omni.
- Consequently no Nano Omni `response_format` field was added. Strict JSON
  remains an application prompt/parser/schema contract and fails closed.

Files changed by this continuation:

- `python/ai_vastu/nvidia_nim_http.py`;
- `python/ai_vastu/plan_intake/nvidia_nim_provider.py`;
- `tests/nvidia_nim/test_nvidia_nim_http.py`;
- `tests/plan_intake/test_nvidia_nim_provider.py`;
- `docs/CURRENT_HANDOFF.md`.

No payment, Supabase, Vastu, deterministic geometry, `PlanDocument`, PDF
renderer, or Git metadata file was changed by this continuation.

Offline validation:

- focused NVIDIA HTTP/client and plan-recognition tests: **96 passed**, one
  existing pytest cache warning;
- NVIDIA, plan-intake, and provider-media affected suites: **131 passed**, one
  existing pytest cache warning;
- independent regression review: **107 passed**, no material finding;
- independent adversarial review: **95 passed**, no material finding;
- `pnpm phase29c:check`: **PASS_LOCAL**, factories, bounded local PDF rendering,
  zero network calls, and secret redaction exercised;
- full Python suite with the established workspace-local `tmp_path` fixture:
  **1,081 passed**, six warnings;
- Ruff across `python`, `apps/api`, `tests`, and `scripts`: **PASS**;
- mypy across `python` and `apps/api/app`: **PASS across 217 source files**;
- `git diff --check`: **PASS**, with existing LF/CRLF notices only.

The required `pnpm validate` wrapper was attempted with the repository venv on
`PATH`. Ruff and mypy passed, then the wrapper's bare Windows `pytest`
entrypoint stopped during collection with 134 `ModuleNotFoundError` errors for
the repository-local `tests.*` package. The direct, authoritative
`.venv\Scripts\python.exe -m pytest` invocation from the same worktree passed
all 1,081 tests. The wrapper tail was not reached, so this is not a
`pnpm validate` pass. Node remains v20.11.1 while the repository declares
Node >=24.

Operator rerun command (one PowerShell command; run only in the reviewed shell
that already holds `NVIDIA_API_KEY`):

```powershell
& { $env:AI_VASTU_REQUIREMENTS_PROVIDER = "nvidia_nim"; $env:AI_VASTU_ARCHITECT_PROVIDER = "nvidia_nim"; $env:AI_VASTU_VASTU_PROVIDER = "nvidia_nim"; $env:AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER = "nvidia_nim"; $env:AI_VASTU_REVISION_PROVIDER = "nvidia_nim"; $env:AI_VASTU_PLAN_RECOGNITION_PROVIDER = "nvidia_nim"; $env:AI_VASTU_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"; $env:AI_VASTU_NVIDIA_PRIMARY_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"; $env:AI_VASTU_NVIDIA_VISION_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"; $env:AI_VASTU_NVIDIA_ATTEMPT_TIMEOUT_SECONDS = "120"; $env:AI_VASTU_NVIDIA_TOTAL_TIMEOUT_SECONDS = "240"; $env:AI_VASTU_NVIDIA_RETRY_DELAY_SECONDS = "0"; $env:AI_VASTU_NVIDIA_MAX_RETRY_AFTER_SECONDS = "0"; Remove-Item Env:AI_VASTU_NVIDIA_FALLBACK_MODEL -ErrorAction SilentlyContinue; Remove-Item Env:OPENROUTER_API_KEY -ErrorAction SilentlyContinue; Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue; & .\.venv\Scripts\python.exe scripts\check-phase29c-live.py }
```

Do not claim Nano Omni PNG, rendered-PDF inference, Phase29C NVIDIA NIM, or
production NVIDIA entitlement qualified until new operator evidence satisfies
the canonical sequence.

### Phase 29E NVIDIA PNG-canonical plan intake - 2026-10-02

Status: **PASS_LOCAL; PARTIAL_LIVE / NOT YET QUALIFIED; PRODUCTION ENTITLEMENT
BLOCKED_HUMAN_ACTION**

Codex made no NVIDIA, OpenRouter, Gemini, payment, Supabase, database, or other
live-service call. `NVIDIA_API_KEY` remained unavailable and was not inspected.

Latest operator-supplied canonical live evidence:

| Gate | Status |
|---|---|
| NVIDIA model inventory | `PASS_LIVE` |
| NVIDIA Ultra text | `PASS_LIVE` |
| NVIDIA Nano Omni PNG with `enable_thinking=false` | `PASS_LIVE` |
| NVIDIA Nano Omni JPEG | `FAIL unavailable`, HTTP 503 after 2 bounded attempts |
| NVIDIA Nano Omni PDF local render | `PASS_LOCAL` |
| NVIDIA Nano Omni PDF inference | `NOT_REACHED` in the latest legacy-sequential run |
| PHASE29C NVIDIA_NIM | `PARTIAL_LIVE` |
| Production NVIDIA entitlement | `BLOCKED_HUMAN_ACTION` |

Root cause and provider-facing media policy:

- NVIDIA officially documents JPEG/JPG and PNG support for hosted Nano Omni.
  The repeated JPEG HTTP 503 is therefore recorded as an operational hosted-
  endpoint observation, not as evidence that NVIDIA lacks JPEG support.
- Vastudraw now makes NVIDIA plan-recognition raster input PNG-canonical:
  validated PNG uploads remain byte-for-byte PNG; an actual JPG/JPEG upload is
  decoded locally, EXIF orientation is applied, pixels are converted to RGB,
  and a deterministic metadata-free PNG is sent to Nano Omni; PDFs continue
  through the existing bounded local page renderer and its PNG output. The PDF
  renderer itself was not changed.
- User-facing JPG/JPEG support and the original reference filename/content
  provenance remain intact. Only the provider-facing media representation is
  normalized; no architectural geometry or inferred plan data is mutated.
- The raster boundary permits only `image/png` and `image/jpeg`, checks exact
  magic bytes and decoded Pillow format, requires one frame and a complete
  decode, and fails closed for malformed, truncated, MIME-mismatched, or
  unsupported data. Input is capped at 20 MiB, each dimension at 4,096 pixels,
  decoded area at 16,000,000 pixels, and normalized PNG output at 12 MiB.
  Pillow decompression-bomb warnings and errors are rejected. Errors are fixed,
  sanitized messages and do not include filenames, image bytes, prompts,
  secrets, or raw model responses.
- JPEG output uses `ImageOps.exif_transpose`, RGB conversion, and Pillow PNG
  encoding with `optimize=False` and `compress_level=9`; repeated normalization
  of the same accepted input is byte-deterministic. Supported JPEG modes,
  including grayscale and CMYK, normalize safely to provider-facing RGB PNG.
- Nano Omni plan recognition still sends the fixed allowlisted request field
  `"chat_template_kwargs":{"enable_thinking":false}`. Ultra text request bodies
  remain unchanged. Strict JSON and `PlanRecognitionDraft` validation remain
  fail-closed; no reasoning/prose stripping, `INVALID_RESPONSE` retry, or retry
  expansion was added. Existing one-retry behavior for bounded transient
  `TIMEOUT`/`UNAVAILABLE` failures remains unchanged.
- Official Nano Omni documentation reviewed for this work still does not
  establish hosted support for `response_format={"type":"json_object"}`.
  Lightning behavior was not generalized, and no speculative
  `response_format` field was added.

Canonical live-checker behavior:

- The local PDF-render probe runs and reports independently before credential
  and inventory checks. Inventory remains the safety prerequisite for hosted
  completions.
- After inventory succeeds, Ultra text, PNG intake, actual-JPEG production
  intake, and rendered-PDF intake each run and report independently. A JPEG
  failure no longer prevents the PDF-path probe from running.
- The JPEG probe begins with real JPEG bytes and calls the production
  `PlanIntakeService`; it can report `PASS_LIVE` only after the production
  normalizer supplies PNG to Nano Omni and strict JSON, application,
  provenance, and content-hash validation all pass.
- The aggregate reports `PHASE29C NVIDIA_NIM PASS_LIVE` only when every required
  stage passes. Calls remain individually bounded and no additional retry or
  uncontrolled provider-call loop was introduced.

Windows repository-script correction:

- `scripts/run-project-python.mjs` resolves the repository-local interpreter as
  `.venv\\Scripts\\python.exe` on Windows or `.venv/bin/python` elsewhere,
  invokes it without a shell, preserves arguments/cwd/exit status, and refuses
  to fall back to ambient Python.
- All Python-backed `package.json` scripts, including pytest, Ruff, mypy, phase
  checks, and live-check entrypoints, now use that runner. No machine-specific
  absolute path was added.

Files changed by this continuation:

- `package.json`;
- `python/ai_vastu/media_validation_adapter.py`;
- `python/ai_vastu/plan_intake/nvidia_nim_provider.py`;
- `scripts/check-phase29c-live.py`;
- `scripts/run-project-python.mjs` (new);
- `tests/provider_media/test_nvidia_plan_raster.py` (new);
- `tests/plan_intake/test_nvidia_nim_provider.py`;
- `tests/production/test_phase29c_operations.py`;
- `docs/CURRENT_HANDOFF.md`.

No payment, Supabase, frozen Vastu, OR-Tools/deterministic geometry,
`PlanDocument`, production billing-security, PDF-renderer, or Git metadata file
was changed by this continuation. Contract regeneration during validation
produced no contract diff.

Offline validation:

- final focused NVIDIA/media/plan-intake/checker/policy suite: **135 passed**,
  one existing pytest cache warning;
- affected subsystem suite before the final vendor-boundary adjustment:
  **162 passed**; the final focused rerun includes and passes that boundary;
- independent regression/adversarial follow-up: **132 passed**, no material
  finding;
- `pnpm phase29c:check`: **PASS_LOCAL**, including NVIDIA factories, bounded PDF
  rendering, zero network calls, and secret redaction;
- full authoritative Python suite with the established workspace-local temp
  compatibility plugin: **1,101 passed**, six warnings;
- Ruff: **PASS**;
- mypy: **PASS across 217 source files**;
- `pnpm python:lint`, `pnpm python:typecheck`, and venv-routed pytest collection:
  **PASS**;
- `pnpm validate` used the corrected venv runner: Ruff, mypy, all **1,101**
  pytest tests, contract checks, frozen-Vastu checks, constraint/planner/
  geometry/validation/scoring checks passed. It then stopped at
  `projects:check` because this host denied SQLite access and cleanup under
  `C:\\Users\\chint\\AppData\\Local\\Temp`; this is the known Windows temp ACL
  limitation, so `pnpm validate` is **not an overall pass**. The environment
  also reports Node v20.11.1 while the repository declares Node >=24.

Next canonical live run: execute the single PowerShell command below only in
the reviewed operator shell that already holds `NVIDIA_API_KEY`. Do not infer
Phase29C or production qualification unless every independently reported stage
passes:

```powershell
& { $env:AI_VASTU_REQUIREMENTS_PROVIDER = "nvidia_nim"; $env:AI_VASTU_ARCHITECT_PROVIDER = "nvidia_nim"; $env:AI_VASTU_VASTU_PROVIDER = "nvidia_nim"; $env:AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER = "nvidia_nim"; $env:AI_VASTU_REVISION_PROVIDER = "nvidia_nim"; $env:AI_VASTU_PLAN_RECOGNITION_PROVIDER = "nvidia_nim"; $env:AI_VASTU_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"; $env:AI_VASTU_NVIDIA_PRIMARY_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"; $env:AI_VASTU_NVIDIA_VISION_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"; $env:AI_VASTU_NVIDIA_ATTEMPT_TIMEOUT_SECONDS = "120"; $env:AI_VASTU_NVIDIA_TOTAL_TIMEOUT_SECONDS = "240"; $env:AI_VASTU_NVIDIA_RETRY_DELAY_SECONDS = "0"; $env:AI_VASTU_NVIDIA_MAX_RETRY_AFTER_SECONDS = "0"; Remove-Item Env:AI_VASTU_NVIDIA_FALLBACK_MODEL -ErrorAction SilentlyContinue; Remove-Item Env:OPENROUTER_API_KEY -ErrorAction SilentlyContinue; Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue; & .\.venv\Scripts\python.exe scripts\check-phase29c-live.py }
```

### Phase 29E Ollama/Qwen local development provider - 2026-10-03

Status: **PASS_LOCAL for the qualified local requirements and plan-recognition
paths; NOT PRODUCTION QUALIFIED**

Provider architecture and authority:

- `ollama_local` is a separate first-class provider identity. It does not
  impersonate or overload NVIDIA, OpenAI, Gemini, or OpenRouter.
- Thin adapters cover requirements, architectural intelligence, soft-Vastu
  reasoning, Architectural Brain concepts, revision intent, and plan
  recognition. The real `RequirementDraft`, advisory contracts, and
  `PlanRecognitionDraft` schemas are sent through Ollama's native `format`
  field. All output must be one strict JSON object and then pass the existing
  application/Pydantic contract; there is no Markdown stripping, reasoning
  removal, regex extraction, or repair.
- Application-owned IDs, provider/model provenance, schema versions,
  reference names, confirmation flags, visual observation sources, advisory
  authority flags, and content hashes are restored after model output. AI is
  non-authoritative for dimensions, geometry, frozen Vastu validation, and
  solver feasibility.
- PNG and JPEG are validated and sent as their actual raster bytes. PDF still
  uses the existing bounded local `PdfiumPageRenderer`; only rendered PNG page
  bytes reach Ollama. The PDF renderer, deterministic OR-Tools geometry,
  frozen Vastu rules, canonical `PlanDocument`, hard validators, immutable
  revision semantics, and payment/security contracts were not weakened.
- Existing NVIDIA provider behavior and evidence remain separate and intact:
  inventory `PASS_LIVE`, Ultra text `PASS_LIVE`, Nano Omni PNG `PASS_LIVE`,
  Nano JPEG affected by repeated hosted 503/unavailable responses, Phase29C
  NVIDIA `PARTIAL_LIVE`, and production NVIDIA entitlement
  `BLOCKED_HUMAN_ACTION`.

Endpoint, model, and resource policy:

- exact endpoint: `http://127.0.0.1:11434`; localhost aliases, HTTPS, alternate
  ports, and remote hosts are rejected;
- exact model: `qwen3-vl:8b-instruct-q4_K_M`; response and inventory identity
  must agree with the pin, contradictory inventory fields are rejected, and
  no fallback or model download exists;
- explicit `APP_ENV=development` is required. All six factories reject local
  selection in staging and production before HTTP. Production settings and
  staging preflight remain explicitly NVIDIA-only; there is no localhost
  fallback;
- proxy inheritance and redirects are disabled; one attempt, zero hidden
  retries; `stream=false`; `options.temperature=0`;
- connect 3 seconds (maximum 10), read 300 (maximum 300), total 360 (maximum
  360), write 30 (maximum 60), pool 3 (maximum 10); the total deadline covers
  transport, strict parsing, and application validation result acceptance;
- request cap 48 MiB and shared response cap 2 MiB; failures are categorized
  as unavailable, timeout, invalid response/application validation, or other
  bounded provider categories without prompts, raw output, image bytes, or
  transport text in exposed exception chains.

Canonical local qualification evidence:

- endpoint/model availability used read-only `/api/version` and `/api/tags`;
  no model pull/download was attempted;
- real `RequirementDraft`: schema `24A.1`, provider `ollama_local`, exact model,
  width `9000 mm`, depth `15000 mm`, bedroom count `2`, north road, and room
  observations including bedroom; every proposed value remained
  confirmation-required and no value became `USER_CONFIRMED`. In the observed
  run the model omitted floor and parking counts, so the draft correctly
  remained not ready for automatic confirmation;
- real PNG, actual JPEG, and PDF-to-local-PNG `PlanRecognitionDraft` paths each
  recognized NORTH, LIVING, KITCHEN, BEDROOM, and TOILET; each preserved schema
  `26B.5.1`, exact provider/model provenance, the original reference name,
  confirmation-required `MODEL_INFERENCE` observations, and a valid canonical
  content hash;
- independently reported stages all passed: `OLLAMA ENDPOINT`, `OLLAMA MODEL`,
  `REQUIREMENTS TEXT`, `PLAN PNG`, `PLAN JPEG`, `PLAN PDF-PATH`, `STRICT JSON`,
  `PROVENANCE`, and `CONTENT HASH`; aggregate
  `OLLAMA LOCAL QUALIFICATION PASS_LOCAL`;
- architectural intelligence, soft-Vastu reasoning, Architectural Brain, and
  revision adapters are contract-tested offline only and are not included in
  the live `PASS_LOCAL` claim.

Validation evidence:

- final focused Ollama/client/adapter/media/checker/Windows-runner suite:
  **57 passed**;
- affected provider/requirements/plan-intake/NVIDIA/production suite before
  final adversarial hardening: **418 passed**; independent regression review
  additionally reported **199 passed** and **197 passed** scopes;
- final authoritative Python suite through `pnpm python:test`: **1,163 passed**,
  six warnings;
- Ruff: **PASS**; mypy: **PASS across 224 source files**;
- `pnpm phase29c:check`: **PASS_LOCAL**, zero network;
- `pnpm ollama:local`: **PASS_LOCAL** for every required stage;
- `git diff --check`: **PASS**, with line-ending notices only;
- `pnpm validate`: the corrected venv/test runner passed Ruff, mypy, all
  **1,163** Python tests, contract generation/checks, frozen-Vastu checks,
  deterministic constraints/planner/geometry/validation/scoring, project
  revisions, editor/API/export/generation, requirements, billing, persistence,
  auth, and Phase 24 through Phase 29D offline gates. It then stopped at the
  workspace `format:check` because this host runs unsupported Node v20.11.1
  while the repository requires Node >=24, and pnpm's packaged child-process
  spawn returned `EPERM`. A direct retry reproduced the same boundary. This is
  not an overall `pnpm validate` pass and remains an environment blocker.

Windows repository validation correction:

- every Python-backed package command resolves the repository-local venv
  interpreter without an absolute machine path and without ambient-Python
  fallback;
- pytest uses a repository-local, per-process fixture root on Windows, fixing
  the prior bare-pytest package import and inaccessible `tmp_path` failures;
- project-revision, requirements, and billing smoke scripts use the same
  process-scoped accessible workspace temp policy. Their checks passed. No
  tests were skipped or weakened.

Files changed for this Ollama continuation:

- `.env.example`, `phase29-ollama-local.env.example`, `package.json`,
  `pytest_workspace_tmp.py`;
- `docs/exec-plans/active/phase29e-ollama-local.md`,
  `docs/CURRENT_HANDOFF.md`;
- `python/ai_vastu/ollama_local_http.py`,
  `python/ai_vastu/media_validation_adapter.py`;
- `python/ai_vastu/requirements/providers/{__init__,ollama_local}.py`,
  `python/ai_vastu/requirements/service.py`;
- `python/ai_vastu/plan_intake/{__init__,service,ollama_local_provider}.py`;
- `python/ai_vastu/architectural_intelligence/providers/{__init__,ollama_local}.py`,
  `python/ai_vastu/architectural_intelligence/service.py`;
- `python/ai_vastu/vastu_reasoning/providers/{__init__,ollama_local}.py`,
  `python/ai_vastu/vastu_reasoning/service.py`;
- `python/ai_vastu/architectural_brain/{provider,revisions,ollama_local_provider,ollama_local_revision}.py`;
- `scripts/check-ollama-local.py`, `scripts/run-project-python.mjs`,
  `scripts/workspace_temp.py`, `scripts/check-project-revisions.py`,
  `scripts/check-requirements-interpreter.py`, and
  `scripts/check-billing-entitlements.py`;
- `tests/ollama_local/test_ollama_local_http.py`,
  `tests/ollama_local/test_ollama_local_adapters.py`,
  `tests/ollama_local/test_qualification_script.py`,
  `tests/plan_intake/test_ollama_local_provider.py`,
  `tests/production/test_openrouter_settings.py`, and
  `tests/production/test_phase29c_operations.py`.

Canonical local operator command (no credential is required or read):

```powershell
& { $env:APP_ENV = "development"; $env:AI_VASTU_REQUIREMENTS_PROVIDER = "ollama_local"; $env:AI_VASTU_ARCHITECT_PROVIDER = "ollama_local"; $env:AI_VASTU_VASTU_PROVIDER = "ollama_local"; $env:AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER = "ollama_local"; $env:AI_VASTU_REVISION_PROVIDER = "ollama_local"; $env:AI_VASTU_PLAN_RECOGNITION_PROVIDER = "ollama_local"; $env:AI_VASTU_OLLAMA_BASE_URL = "http://127.0.0.1:11434"; $env:AI_VASTU_OLLAMA_MODEL = "qwen3-vl:8b-instruct-q4_K_M"; $env:AI_VASTU_OLLAMA_CONNECT_TIMEOUT_SECONDS = "3"; $env:AI_VASTU_OLLAMA_READ_TIMEOUT_SECONDS = "300"; $env:AI_VASTU_OLLAMA_TOTAL_TIMEOUT_SECONDS = "360"; $env:AI_VASTU_OLLAMA_WRITE_TIMEOUT_SECONDS = "30"; $env:AI_VASTU_OLLAMA_POOL_TIMEOUT_SECONDS = "3"; & .\.venv\Scripts\python.exe scripts\check-ollama-local.py; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

### Phase 29E optional APINEX development provider - 2026-10-03

Status: **IMPLEMENTED_LOCAL; APINEX overall NOT_QUALIFIED**

Architecture and policy:

- `apinex` is an isolated first-class provider identity for optional, explicit
  development use. It does not impersonate OpenAI/OpenRouter and does not replace
  the qualified `ollama_local` Qwen development default.
- All six selectors support explicit `apinex`: requirements, architectural
  intelligence, soft-Vastu reasoning, Architectural Brain, revisions, and plan
  recognition. Each selection requires `APP_ENV=development`; staging and
  production fail before HTTP. Existing production/staging settings remain
  NVIDIA-only.
- The exact base URL is `https://api.apinex.bond/v1`; the exact model is
  `free/gpt-6-luna`. Alternate scheme, host, path, model, fallback model, catalog
  substitution, and returned-model mismatch fail closed.
- The credential exists only in the operator process environment. It is not stored
  in tracked configuration, fixtures, logs, qualification output, or exception
  text.
- HTTP redirects and proxy inheritance are disabled. Runtime uses one attempt and
  no automatic retry or provider/model fallback. Defaults are connect 5 seconds,
  read 180, total 240, write 30, and pool 5; maxima are 15, 300, 360, 60, and 15.
  Requests are capped at 48 MiB and responses at 2 MiB.

Structured and media behavior:

- Schema-bearing calls send `response_format.type=json_schema`, `strict=true`, the
  real canonical schema, `temperature=0`, and `stream=false`, plus an explicit raw
  JSON/exact-schema/no-Markdown/no-extra-keys instruction. Provider schema signaling
  is never trusted as validation: strict duplicate-aware JSON parsing and existing
  Pydantic/application validation still fail closed. No Markdown stripping, regex
  extraction, reasoning removal, coercive repair, or application bypass exists.
- Real `RequirementDraft` application authority overwrites draft/user/project IDs,
  prompt, references, provider, and model. Model-proposed values stay
  confirmation-required and cannot become `USER_CONFIRMED`.
- Real `PlanRecognitionDraft` application authority preserves schema `26B.5.1`,
  project/intake IDs, reference names, exact provider/model, confirmation-required
  visual observations, safe source normalization, and canonical content hashes.
- Valid PNG and JPEG bytes are sent as matching `image_url` data URLs. PDF uses the
  unchanged bounded local Pdfium renderer and sends only rendered PNG pages; raw PDF
  bytes never reach APINEX.
- Real client plans or prompts must not be sent to APINEX merely because the optional
  development adapter exists. No APINEX privacy or retention guarantee has been
  verified.

Live-evidence boundary:

- Existing operator evidence remains: endpoint/auth `PASS_LIVE`, exact model
  inventory `PASS_LIVE`, exact text `PASS_LIVE`, structured text `PASS_LIVE`, first
  PNG schema probe **FAIL**, and second bounded PNG structured-vision probe
  `PASS_LIVE`.
- JPEG, PDF-path, real `RequirementDraft`, real `PlanRecognitionDraft`, and aggregate
  APINEX qualification remain `NOT_QUALIFIED`. Mock/unit/local validation cannot
  promote these statuses. No APINEX live call was made by Codex.
- The dedicated `scripts/check-apinex-live.py` gate uses synthetic data only and
  independently reports endpoint, inventory, text, structured text, requirements,
  PNG, JPEG, PDF-path, strict JSON, provenance, and content hash. Every stage is
  required for aggregate `PASS_LIVE`; dependencies are reported without hiding
  independent media results.

Local validation evidence (no APINEX/cloud call):

- focused APINEX client/adapter/checker tests: **51 passed**, with one
  permission-only pytest cache warning;
- canonical `pnpm python:test`: **1,216 passed**, six warnings; the repository
  runner and workspace-local pytest fixture completed successfully, with no
  fallback runner required;
- Ruff: **PASS**; mypy: **PASS across 231 source files**;
- `pnpm phase29c:check`: **PASS_LOCAL**, with `network_calls=false`;
- correctly configured canonical Ollama gate: all nine stages and aggregate
  **PASS_LOCAL**;
- `git diff --check`: **PASS**, line-ending notices only;
- the globally installed `pnpm.exe` still reported its known embedded Node 20.11.1
  unsupported-engine warning, but it did not block the Python suite, Ruff, mypy,
  or Phase 29C gates. No fallback runner, APINEX live call, or credential access
  occurred;
- the earlier `pnpm validate` attempt was not an overall pass because the managed
  host failed at workspace `format:check` with `spawn EPERM`. The latest prior real
  operator Node 24.20.0 / pnpm 10.17.1 `pnpm validate` remains **PASS end-to-end**.

Files changed for APINEX:

- `.env.example`, `phase29-apinex.env.example`, `package.json`;
- `docs/exec-plans/active/phase29e-apinex-optional.md`,
  `docs/CURRENT_HANDOFF.md`;
- `python/ai_vastu/apinex_http.py`;
- requirements: `providers/apinex.py`, `providers/__init__.py`, `service.py`;
- plan intake: `apinex_provider.py`, `__init__.py`, `service.py`;
- architectural intelligence: `providers/apinex.py`, `providers/__init__.py`,
  `service.py`;
- soft-Vastu reasoning: `providers/apinex.py`, `providers/__init__.py`,
  `service.py`;
- Architectural Brain: `apinex_provider.py`, `apinex_revision.py`, `provider.py`,
  `revisions.py`;
- `scripts/check-apinex-live.py`;
- `tests/apinex/{__init__,test_apinex_http,test_adapters,test_qualification_script}.py`.

Canonical APINEX operator command (run only in the reviewed shell where the
credential is already present):

```powershell
& { & .\.venv\Scripts\python.exe scripts\check-apinex-live.py; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

### Phase 29E Ollama local reproducibility requalification - 2026-10-03

Status: **PASS_LOCAL after 3/3 consecutive complete canonical passes; NOT
PRODUCTION QUALIFIED**

The fresh Windows operator result that triggered this continuation remains
part of the evidence: endpoint, model, requirements, JPEG, PDF-PATH, and strict
JSON passed, while PNG surfaced only a generic `PlanIntakeProviderError` and
the aggregate provenance/hash probes surfaced generic `RuntimeError`. That run
was not green and the earlier one-run qualification claim was not treated as
reproducible.

Root cause and diagnosis:

- PNG, JPEG, and PDF-PATH use the same model, native schema, temperature zero,
  strict parser, application validator, and authority normalization. The PNG
  and JPEG checker images are the same 1000x1400 RGB drawing; the accepted PNG
  is a real 20,155-byte PNG and the accepted JPEG is a real 96,099-byte JPEG.
  The PDF path independently renders a 21,580-byte PNG through the unchanged
  bounded `PdfiumPageRenderer`.
- A pre-adjustment three-run diagnostic series showed transport timeout
  failures migrating between formats: run 1 passed PNG but timed out JPEG and
  PDF-PATH; run 2 reproduced the operator pattern with PNG timing out while
  JPEG and PDF-PATH passed; run 3 passed. Each failed call had
  `category=timeout`, `stage=provider_transport_http`, and `attempts=1`.
  Therefore this was not a deterministic PNG signature, MIME, request-schema,
  Pydantic, normalization, provenance, reference-name, or hash defect. It was
  variable local Qwen vision latency exceeding the prior 180-second read /
  240-second total development budget.
- The bounded development policy now uses a 300-second read deadline and a
  360-second total deadline, which were already the enforced maxima. Connect
  remains 3 seconds, write 30, pool 3, response 2 MiB, request 48 MiB, and each
  stage still has exactly one attempt. No retry, fallback, model change,
  permissive repair, schema relaxation, or validation bypass was added.
- The canonical checker now recovers only sanitized Ollama category/stage,
  timeout kind, attempt count, safe HTTP status, and at most eight allowlisted
  Pydantic location/type pairs through a bounded exception-chain walk. The
  exception constructor re-sanitizes even preconstructed diagnostic metadata.
  Raw model output, prompts, image bytes/base64, credentials, validator input,
  messages, contexts, and arbitrary field names are never printed or retained
  in the exposed exception chain.
- Qualification assertions now use fixed safe reason codes. `PROVENANCE` and
  `CONTENT HASH` report `BLOCKED_DEPENDENCY missing=<stage>` when a required
  media draft is unavailable. In the operator failure they were cascading
  dependency failures, not independent provenance or hash defects. The final
  aggregate still fails whenever any required stage fails or is blocked.

Reproducibility evidence with the corrected policy:

| Run | Endpoint | Model | Requirements | PNG | JPEG | PDF-PATH | Strict JSON | Provenance | Hash | Aggregate |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS_LOCAL |
| 2 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS_LOCAL |
| 3 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS_LOCAL |

Validation evidence:

- focused final Ollama diagnostic/client/checker/adapter tests: **48 passed**;
- full Ollama + plan-intake + requirements regression: **142 passed**;
- full Python suite: **1,165 passed**, six warnings;
- independent NVIDIA/Ollama regression scope: **132 passed**;
- Ruff: **PASS**; mypy: **PASS across 224 source files**;
- `pnpm phase29c:check`: **PASS_LOCAL**, zero network;
- `git diff --check`: **PASS**, with line-ending notices only;
- repository `pnpm validate`: the latest canonical Windows Node 24.20.0 /
  pnpm 10.17.1 operator run is **PASS end-to-end**. It was not rerun in the
  managed Node 20 shell because that shell is below the repository's Node 24
  requirement; the affected Python/full gates above are green after this
  change.

Files changed in this continuation:

- `.env.example`;
- `phase29-ollama-local.env.example`;
- `docs/exec-plans/active/phase29e-ollama-local.md`;
- `docs/CURRENT_HANDOFF.md`;
- `python/ai_vastu/ollama_local_http.py`;
- `scripts/check-ollama-local.py`;
- `tests/ollama_local/test_ollama_local_http.py`;
- `tests/ollama_local/test_ollama_local_adapters.py`;
- `tests/ollama_local/test_qualification_script.py`.

No NVIDIA/OpenRouter/Gemini call, cloud credential access, Supabase mutation,
payment call, Git metadata mutation, frozen-Vastu change, OR-Tools geometry
change, canonical-model weakening, JSON repair, or output extraction was made.

Final canonical operator confirmation command:

```powershell
& { $env:APP_ENV = "development"; $env:AI_VASTU_REQUIREMENTS_PROVIDER = "ollama_local"; $env:AI_VASTU_ARCHITECT_PROVIDER = "ollama_local"; $env:AI_VASTU_VASTU_PROVIDER = "ollama_local"; $env:AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER = "ollama_local"; $env:AI_VASTU_REVISION_PROVIDER = "ollama_local"; $env:AI_VASTU_PLAN_RECOGNITION_PROVIDER = "ollama_local"; $env:AI_VASTU_OLLAMA_BASE_URL = "http://127.0.0.1:11434"; $env:AI_VASTU_OLLAMA_MODEL = "qwen3-vl:8b-instruct-q4_K_M"; $env:AI_VASTU_OLLAMA_CONNECT_TIMEOUT_SECONDS = "3"; $env:AI_VASTU_OLLAMA_READ_TIMEOUT_SECONDS = "300"; $env:AI_VASTU_OLLAMA_TOTAL_TIMEOUT_SECONDS = "360"; $env:AI_VASTU_OLLAMA_WRITE_TIMEOUT_SECONDS = "30"; $env:AI_VASTU_OLLAMA_POOL_TIMEOUT_SECONDS = "3"; & .\.venv\Scripts\python.exe scripts\check-ollama-local.py; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

### Phase 29E local-development AI qualification checkpoint - 2026-10-04

Status: **LOCAL OLLAMA QUALIFIED; APINEX NOT_QUALIFIED; HOSTED/PRODUCTION AI
NOT QUALIFIED**

This checkpoint freezes the verified local-development provider policy without
making a new cloud call or changing provider runtime behavior:

- `ollama_local` with `qwen3-vl:8b-instruct-q4_K_M` at the exact loopback
  endpoint remains the local-development default. The canonical qualification
  completed three consecutive full `PASS_LOCAL` runs.
- The Ollama evidence covers endpoint, exact model, real `RequirementDraft`, PNG
  and JPEG `PlanRecognitionDraft`, PDF through the existing bounded Pdfium-to-PNG
  path, strict JSON, exact provider/model provenance, reference identity,
  confirmation-required `MODEL_INFERENCE` semantics, and canonical content hash.
- NVIDIA evidence remains separate and unchanged: model inventory, Ultra text,
  and Nano Omni PNG have `PASS_LIVE` evidence, while hosted vision has also
  experienced intermittent provider-side failures. Overall NVIDIA hosted
  qualification remains incomplete, and production entitlement remains
  `BLOCKED_HUMAN_ACTION`.
- APINEX implementation and offline validation remain `PASS_LOCAL`. Historical
  manual endpoint/catalog and limited inference evidence remains chronological,
  but the latest canonical qualification result controls current status.

The canonical APINEX operator qualification was run twice. Both runs produced:

- `APINEX ENDPOINT PASS_LIVE`;
- `APINEX MODEL INVENTORY PASS_LIVE`;
- `APINEX TEXT`, `APINEX STRUCTURED TEXT`, `REQUIREMENTS TEXT`, `PLAN PNG`,
  `PLAN JPEG`, `PLAN PDF-PATH`, and `STRICT JSON`: `category=request_rejected`,
  `stage=provider_transport_http`, `attempts=1`, `http_status=402`;
- `PROVENANCE BLOCKED_DEPENDENCY` and `CONTENT HASH BLOCKED_DEPENDENCY`;
- aggregate `APINEX LIVE QUALIFICATION FAIL`.

This proves authentication/API reachability and catalog access, while current
inference is `BLOCKED_PROVIDER_HTTP_402`. It is not evidence of a Vastudraw
schema, media, or provider-adapter defect. The exact billing, quota, or account
cause is not inferred without provider evidence. APINEX remains optional,
development-only, fail-closed, and `NOT_QUALIFIED`; it does not replace Ollama.
No further APINEX live call is required for this checkpoint.

Repository evidence frozen at this checkpoint:

- focused Ollama: **48 passed**, one permission-only pytest cache warning;
- focused APINEX: **51 passed**, one permission-only pytest cache warning;
- affected provider/requirements/plan-intake suite through the canonical runner:
  **418 passed, three warnings**;
- complete Python suite: **1,216 passed, six warnings**;
- Ruff: **PASS**;
- mypy: **PASS across 231 source files**;
- Phase 29C offline gate: **PASS_LOCAL**, `network_calls=false`;
- durable memory validation: **PASS**, 22 nodes and 19 edges;
- fresh canonical localhost Ollama qualification: endpoint, exact model,
  requirements, PNG, JPEG, PDF-path, strict JSON, provenance, content hash, and
  aggregate all **PASS_LOCAL**;
- `git diff --check`: **PASS**, line-ending notices only.

An initial affected-suite invocation reported 141 setup errors because it omitted
the repository's required workspace temp-root environment. This was a harness-only
error: the identical suite passed through the canonical repository runner with all
418 tests green.

The managed-shell `pnpm validate` rerun passed Ruff, mypy, all 1,216 Python tests,
contracts, frozen Vastu, deterministic constraint/planner/geometry/validation/
scoring gates, project/editor/export/intake/requirements/billing/persistence/auth
checks, 32 web tests, and Phase 24 through Phase 29D. It then stopped at workspace
`format:check` because the native `pnpm.exe` used embedded Node v20.11.1 and its
child-process spawn returned Windows `EPERM`. Therefore that managed-shell rerun is
not a complete `pnpm validate` pass.

The authoritative checkpoint repository result remains the separately verified
operator run under Node v24.20.0 and pnpm 10.17.1: `pnpm validate` **PASS**.

The provider examples now express three non-overlapping profiles: explicit
Ollama local development by default, optional explicit APINEX development use,
and separately configured NVIDIA hosted staging/production-shaped use.
Production settings remain NVIDIA-only and fail closed; there is no silent
production fallback to local Ollama or APINEX. Legacy OpenRouter, direct Gemini,
and NVIDIA qualification contracts remain retained.

Exact checkpoint status:

```text
REPOSITORY
pnpm validate                       PASS

LOCAL DEVELOPMENT AI
ollama_local / Qwen3-VL 8B Q4      PASS_LOCAL
canonical reliability              3/3 PASS_LOCAL

NVIDIA HOSTED
separate existing partial live evidence
production entitlement             BLOCKED_HUMAN_ACTION

APINEX
implementation/offline tests       PASS_LOCAL
endpoint/model inventory           PASS_LIVE
inference                          BLOCKED_PROVIDER_HTTP_402
overall                            NOT_QUALIFIED

PRODUCTION
NOT QUALIFIED / NOT FROZEN FOR LIVE AI PROVIDERS
```

No production qualification or live-provider freeze is claimed. No NVIDIA,
APINEX, OpenRouter, Gemini, payment, Supabase, or other cloud call was made for
this finalization, and no credentials were requested or accessed.

## Phase 29F local acceptance continuation � 2026-10-05

Status: NOT GREEN / PARTIAL LOCAL ACCEPTANCE. Phase 29E checkpoint and Git
history remain untouched. Detailed evidence and browser checklist:
`docs/phase29f-local-acceptance.md`; sanitized local reports/artifacts:
`.local/phase29f-evidence`.

Retained pinned Ollama 8192 context after proven exact 4096-token truncation.
Replaced prompt-only Vastu policy guidance with catalog-derived private keyed
schema, per-rule enums/fixed non-adjustable weights, strict local checks and
bounded private text. Public profiles/catalog/hashes/normalizer unchanged.
Brain decoding now uses actual-program room/endpoint enums with application-owned
metadata. Real wall material is accounted through canonical clipped footprints;
area-rounding parity prevents false overlap. No geometry mutation, relaxed
critic, repair, retries or fallback introduced.

Final pnpm.cmd validate PASS: 1254 Python tests (5 warnings), Ruff PASS, mypy PASS
231 files, 32 web tests, build and all offline gates. Affected suites 225 PASS;
focused Ollama 74 PASS, combined wall/critic/geometry focus 89 PASS. Diff check
PASS. Node 24.20.0/pnpm 10.17.1; no native managed-shell infrastructure failure.

Live Vastu 3/3 PASS, plus 3/3 PASS after actual Ollama outage HTTP503/recovery.
Confirmed generation PASS4 alternatives. Requirements text/confirmation,
PNG/JPEG/PDF recognition, malformed422/corrupt422/oversized413, selection/save,
immutable ancestry/history/stale409, reopen and exact-revision JPG/PDF/DXF hashes
PASS. Current saved child revision 0048eb7c-04fd-4ec1-8c6a-90196e57b430.
Development bypass/no quota consumption and actual entitlement denial PASS;
live limit exhaustion unexercised. API/web restart and persisted revision/hash
PASS. Direct AI revision advisory interpretation PASS; geometry unchanged.

Ollama tray restart reports0.35.1 versus supplied0.35.0 baseline; exact pinned
qwen3-vl:8b-instruct-q4_K_M retained. No installer/model/provider fallback used.
API127.0.0.1:8000, web127.0.0.1:3000 and Ollama remain running with persistent
Phase29F SQLite. No hosted AI, Supabase or live payment calls were made.

Remaining blockers: no browser automation available, manual editor/undo/redo,
responsive/loading/empty/error UI acceptance unexercised; revision chat remains
explicitly disabled Phase26D UI. Canonical door graphs reveal bedroom-transit
privacy issues in all four alternatives, explicitly unevaluated by current
qualified policy. Parking frontage validated but vehicle aperture not drawn.
These existing policy gaps require explicit architectural qualification; no
silent product-contract rewrite performed during acceptance. No GREEN/phase
freeze claim, commit, tag, branch, staging, push or archive deletion.
