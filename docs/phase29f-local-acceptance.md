# Phase 29F local full-stack acceptance

Status: **GREEN - LOCAL PHASE 29F ACCEPTANCE QUALIFIED (2026-10-05)**. Phase 29E remains frozen. Local-only pass;
no hosted AI, Supabase, payment, Git history, or frozen-rule mutation.


## Final local result

All five requested continuation blockers are resolved. API and web remain running
on loopback ports 8000 and 3000; persistent operator SQLite data is preserved.
This qualifies the local development journey, not hosted/production deployment.
No human-only acceptance step remains. Git staging, commits, tags and publishing
remain entirely operator-controlled.

| Gate | Actual result |
| --- | --- |
| Final integrated focused tests | 148 PASS (`final-focused-current.log`) |
| Focused Ollama | 79 PASS; included in final focused run |
| Affected suites | Earlier dedicated 405 PASS; final 317-test affected subset is included in the passing full suite, not claimed as a separate rerun |
| Final full Python | 1,319 PASS, six dependency warnings, 528.92 s |
| Ruff | PASS |
| mypy | PASS, 236 source files |
| Web tests | 33 PASS |
| Contracts tests | 1 PASS |
| Web build, lint, typecheck, format | PASS |
| `pnpm.cmd validate` | PASS, exit 0 (`phase29f-final-gates.log`) |
| `git -c core.safecrlf=false diff --check` | PASS |
| Local Ollama Vastu | Preserved actual 3/3 plus outage-recovery 3/3 PASS; not needlessly repeated |
| Confirmed generation | Four alternatives; all four final privacy, doorway-span, vehicle, hash and frozen-bundle checks PASS |
| Browser | Real Edge/Playwright desktop 1440, tablet 768, narrow mobile 390 PASS |
| Persistence | Latest revision and all eight ancestors survive final API/web restarts |

The 317-test affected subset was enumerated in
`affected-final-collection.log`; its execution is covered by the final full
1,319-test run. The earlier dedicated 405-test run remains recorded separately.
Node **24.20.0**, pnpm **10.17.1** were actually used; no Node20/spawn-EPERM
infrastructure exception was needed. Earlier gate failures were fixed, rather
than mislabeled as a pre-existing baseline: vendor-boundary import placement,
obsolete disabled-chat assertions, temporary variable/type/lint mistakes, and
unique pytest module naming. One direct focused invocation lacked the Windows
temp-profile environment; the final passing invocation used the repository runner.

Final project: `f2603dae-292e-4d38-b110-ee2aec730dae`.
Latest revision: `57ad4c12-8855-4164-894f-9858b2684bd8`.
Latest hash: `d9077c0a947edeea4ac05da90a2be97fdf35231138cdeff4963edb358785787d`.
Evidence: `latest-immutable-ancestry-proof.json`, `restart-latest-after.json`,
`web-final-restart-proof.json`, `browser-final-restart-navigation.log`,
`browser-latest-exports-final.log`, and `responsive-manual-command-evidence.json`.

Browser evidence covers dashboard/projects, create/text/interpret/confirm,
four-plan inspection/selection/save/reopen, local AI revision, manual editor,
undo/redo/history/ancestry, Vastu advisory, exact JPEG/PDF/DXF downloads,
loading/empty/error states, responsive layouts and back/forward navigation.
PNG recognition was additionally exercised in the browser; JPEG/PDF recognition,
invalid image, corrupt PDF and oversized-input checks retain the actual earlier
API qualification. Real provider outage returned safe 503 in the browser and
recovery passed; no model/provider fallback occurred. Billing exhaustion used an
isolated persistent local fixture and live HTTP 402 denial, with disabled gateways
and staging/production bypass denial; it is not a payment-provider qualification.

Saved-plan revision chat is deliberately bounded to one unambiguous room
width/depth increase, one floor, and preserved saved constraints. Unsupported or
infeasible requests fail closed; manual persistence supports room locks and one
exact dimension. This does not claim arbitrary wall/opening command application
or new structural capability. Existing canonical schema 1.1.0 supplies OPENING;
no schema/migration or frozen Vastu change was required.

## Defect chain and fixes

1. Original Ollama context 4096 truncated strict JSON: prompt 3244 + output
   852 = 4096, `done_reason=length`. Operator control at 8192 completed JSON.
2. Retained shared pinned `OLLAMA_LOCAL_CONTEXT_LENGTH=8192`; no arbitrary
   context/model/provider configuration or fallback introduced.
3. Raw Vastu output then exposed per-rule catalog-policy mismatches. Generic
   profile schema permitted `STRONGLY_PREFERRED` for rules that only permit
   `FLEXIBLE`/`PREFERRED`. Prompt refinement reduced six violations to one but
   could not enforce catalog policy.
4. Added catalog-derived private decoding schema: exact required rule-ID keys,
   exact IDs and per-rule allowed enums, applicability enum, bounded integers,
   fixed non-adjustable weights. Application owns metadata and hashes; adapter
   converts rules to unchanged public tuple shape in catalog order.
5. Initial keyed-schema live sequence passed once then exhausted context again.
   Sanitized control reproduced prompt 3331 + output 4861 = 8192 and
   `done_reason=length`. Private rationale decoding is now limited to 256
   characters and three notes of at most 160 characters. Public rationale
   limit remains 1000. Oversized output is rejected, never truncated/repaired.
6. Real generation reached deterministic planning but returned 422: three Brain
   concepts referenced unavailable dining/corridor types; other candidates had
   thin unexplained site residuals. Added actual-program room/endpoint enums to
   the Ollama Brain schema and local membership checks. Authority metadata is
   application-owned; public concept contract unchanged. Critic/site-space
   thresholds remain untouched and reject unusable residuals.
7. Captured hard-valid plans exposed false critic rejection: geometric site
   accounting omitted actual canonical wall material. A 70 x 2030 mm region
   (142100 mmÂ²) was fully covered by existing 115 mm walls. Added exact centred,
   flat-ended wall footprints, clipped to the envelope and excluding existing
   room/site union, under the existing `WALL` category. No wall/room/solver
   geometry is changed. Original overlap guard and lattice tolerance remain.
8. Adversarial QA found independent area rounding could falsely report 1 mmÂ²
   overlap for odd room area plus half-mm wall material. WALL allocation now
   uses the difference between consistently rounded union totals. A dedicated
   101 x 101 mm / 115 mm wall case protects area conservation.

Captured documents 1 and 3 close through real wall material; documents 2, 5,
and 6 were already closed. Document 4 retains 336212 mmÂ² residual and still
fails the critic. All captured canonical serialization and hashes are unchanged.
The initial affected run exposed a stale blank-strip fixture retaining perimeter
walls; that fixture now explicitly has no wall/opening material and still
requires rejection of the same full 8 mÂ² blank strip.

The existing service missing-rule policy remains unchanged: omitted catalog
rules from other providers are restored explicitly by `_normalize_profile`.
Ollama's private wire contract requires every catalog key. Hard validators,
frozen Vastu, wet-stack softness, integer millimetres, immutable revision
semantics, exact-revision exports, and deterministic geometry remain protected.

## Verified evidence so far

- Focused Ollama client/Vastu/Brain contracts: **74 passed**; combined wall,
  critic and geometry focused checks: **89 passed**.
- Affected Ollama/Vastu/intelligence/Brain/requirements/generation/geometry:
  **225 passed**, including the corrected wall fixture and rounding regression.
- Ruff PASS; mypy PASS across 231 application source files.
- First complete `pnpm.cmd validate`: PASS under Node 24.20.0/pnpm 10.17.1,
  including 1231 Python tests, 32 web tests, format/lint/typecheck/build and all
  offline gates. This run preceded the final Brain schema/parity changes.
- Final integrated `pnpm.cmd validate`: **PASS**, exit 0, **1254 Python tests**
  (5 warnings), Ruff PASS, mypy PASS (231 source files), **32 web tests**,
  formatting/lint/typecheck/build and all offline gates PASS. Node 24.20.0 /
  pnpm 10.17.1; no managed-shell Node20/spawn-EPERM issue occurred.
- `git diff --check` PASS. No commits, tags, branches, staging, resets or pushes.
- Live Vastu **3/3 PASS**, each with 11 rules, exact `ollama_local`/
  `qwen3-vl:8b-instruct-q4_K_M`, zero unknown IDs/policy violations, valid
  content hash, normalization success.
- Catalog working/HEAD blob both
  `ce08cf12131e974c6e543e3c62fc11e3b8c48230`; all 17 frozen V1 spec files
  match HEAD. No public schema change.
- Health/CORS/development bearer auth/project/confirmed-draft reads PASS;
  invalid auth 401.
- Separate fresh project creation/read, Ollama text interpretation, explicit
  known user confirmation, persisted confirmed read PASS.
- Live PNG/JPEG/PDF upload recognition PASS, pinned provider/model and hashes.
  Bad image 422, corrupt PDF 422, >20 MiB image 413: fail closed.
- Final live confirmed generation PASS: four alternatives, validated run hash,
  development billing bypass, no quota consumption or preview revision write.
- Candidate selection/save/reopen PASS; immutable parent, saved child ancestry,
  history and stale-parent 409 PASS. Current saved revision:
  `0048eb7c-04fd-4ec1-8c6a-90196e57b430`.
- JPG/PDF/DXF exports PASS: exact saved revision/source hashes, manifest and
  artifact hashes; wrong candidate rejected 404.
- Actual billing entitlement denies `project_not_entitled`; development bypass
  is explicit and quota unchanged. Live project-limit exhaustion remains
  unexercised; offline billing gates are separate evidence.
- Direct AI revision interpretation PASS with advisory directives and unchanged
  canonical revision. Applying revised geometry through the UI is unqualified.
- Identified Ollama tray/server stopped: real generation fails closed HTTP 503.
  Restart recovery: another **3/3** real Vastu service passes with exact model
  pin, 11 rules, zero policy violations and valid hashes.
- Ollama reports **0.35.1** after tray restart, differing from the supplied
  0.35.0 baseline. No model/provider fallback or installation was performed.
- API restart and web restart HTTP 200 PASS; persistent current revision/hash
  remains exact. Repeated persistence checks exposed a harness filename-glob
  collision with timestamped result reports; snapshots now require UUID names.

Evidence: timestamped sanitized reports and exact canonical/export artifacts in
`.local/phase29f-evidence`. Logs never print model content or client prompts.
Persistent runtime uses `.local/phase29f-projects.sqlite3`,
`.local/phase29f-billing.sqlite3`, and Phase 29F requirements/intake directories.

## Commands

```powershell
& scripts/start-phase29f-api.ps1
& scripts/start-phase29f-api.ps1 -AcceptanceMode basic
& scripts/start-phase29f-api.ps1 -AcceptanceMode text_requirements
& scripts/start-phase29f-api.ps1 -AcceptanceMode vastu
& scripts/start-phase29f-api.ps1 -AcceptanceMode generation
& scripts/start-phase29f-api.ps1 -AcceptanceMode remainder
& scripts/start-phase29f-api.ps1 -AcceptanceMode uploads
& scripts/start-phase29f-api.ps1 -AcceptanceMode revision
& scripts/start-phase29f-api.ps1 -AcceptanceMode persistence
pnpm.cmd validate
```

Start API only when port 8000 is free. Acceptance modes set exact local runtime
settings, guard against hosted database configuration, and never manage processes.

## Historical browser checklist (now covered below)

At the initial backend checkpoint browser automation was unavailable. Local
Edge/Playwright was subsequently installed under `.local`; the real browser
evidence below supersedes that limitation.

At `http://127.0.0.1:3000`, verify:

1. Open/create project, submit text, upload PNG/JPEG/PDF, inspect AI suggestions,
   explicitly confirm, generate alternatives and inspect full plans.
2. Select/save a candidate, close/reopen the project, compare exact revision.
3. Manual editor: change one supported property, undo, redo, save a new revision;
   reopen and verify ancestry and retained original revision.
4. Vastu advisory display and error handling; download JPG/PDF/DXF for the
   selected saved revision and compare manifest/revision IDs.
5. Desktop and mobile (including 390 px width): navigation, plan canvas,
   candidate selector, editor, controls, loading/empty/error states.
6. While Ollama is stopped, verify visible safe error and no candidate/save;
   restart and verify recovery. Reopen after API and web restart.
7. At this historical checkpoint AI revision UI was disabled with a Phase 26D placeholder.
   Direct advisory interpreter evidence cannot certify an end-to-end revision
   chat/application workflow. This is a concrete remaining product/UI gap.

No GREEN claim until required local acceptance gaps are resolved and gates pass.

## Historical plan inspection (defects resolved below)

Independent inspection used canonical door graphs and the exact saved-revision
JPG, not scores alone. Rank 1 requires bedroom_7 transit to bedroom_1 and
common_toilet_4; rank 2 requires bedroom_1 transit to the lobby, other bedroom
and common toilets; rank 3 requires bedroom_7 transit to bedroom_1, lobby and
common_toilet_6. Rank 4 gives both bedrooms lobby access but common_toilet_4
requires bedroom_1 transit. Existing qualified circulation validation excludes
sanitary rooms from transit, permits bedrooms/parking, and explicitly reports
privacy as unevaluated. Thus hard-valid generation PASS does not establish
professional plan usability. These are existing policy limitations, not a wall
accounting regression; acceptance must not silently redefine that contract.

Parking contacts the east-road frontage, but the exported drawing does not
represent a vehicle aperture; frontage/contact validation is not evidence of
complete drawn vehicle access. Browser checks, disabled revision chat/application,
privacy policy qualification, represented vehicle access and live project-limit
exhaustion remain blockers to the complete requested customer journey.

## Historical files changed in the first backend continuation

- `python/ai_vastu/ollama_local_http.py`
- `python/ai_vastu/vastu_reasoning/providers/ollama_local.py`
- `python/ai_vastu/architectural_brain/ollama_local_provider.py`
- `python/ai_vastu/architectural_brain/site_accounting.py`
- `python/ai_vastu/geometry/shapely_validator.py`
- `python/ai_vastu/geometry/types.py`
- `tests/ollama_local/test_ollama_local_http.py`
- `tests/ollama_local/test_ollama_local_adapters.py`
- `tests/ollama_local/test_ollama_local_brain_contract.py` (new)
- `tests/architectural_brain/test_canonical_wall_site_accounting.py` (new)
- `tests/architectural_brain/test_site_accounting_critic.py`
- `scripts/start-phase29f-api.ps1` (new)
- `scripts/phase29f-local-acceptance.py` (new)
- `docs/phase29f-local-acceptance.md` (new)
- `docs/exec-plans/active/phase29f-local-acceptance.md` (new)
- `docs/CURRENT_HANDOFF.md`

Next build returned generated `apps/web/next-env.d.ts` to tracked content.
No frontend source implementation changed at that checkpoint. Pre-existing archives, payloads,
backups and untracked evidence were preserved. Git history remains at
`1940b09fe729fb5d37ac007598c7e245d0fdacdf`.

## Customer-journey continuation â€” 2026-10-05

Status at the start of this continuation: **NOT GREEN.** Earlier backend qualification
above is retained as historical evidence. This section supersedes the earlier
remaining-blocker descriptions and frontend-change statement.

### Correctness fixes

- Bedroom transit: existing circulation analysis, opening synthesis and canonical
  validation now treat bedrooms as terminals. An attached toilet may extend an
  independently accessible bedroom; common toilets and unrelated rooms may not.
  Parking is not a pedestrian circulation root. Confirmed single-floor generation
  enables hard circulation constraints. CP-SAT permits legitimate public doorway
  targets rather than forcing a soft lobby preference. A descending-rank public
  graph also prevents disconnected public components before geometry construction.
  The qualified multi-floor core relations remain separate and unchanged.
- Vehicle access: the existing canonical `OPENING` supports an unobstructed wall
  aperture. Generation constructs a real 3,000 mm road-facing parking aperture;
  canonical validation checks usable bay clearance/depth, sill/headroom, declared
  plot road edges, site containment, and routes clear of occupied rooms/walls.
  No schema extension or renderer-only opening was introduced. Regression coverage
  includes all four road sides and renderer/export wall-gap behavior.
- Revision chat: added a development-only, explicitly `ollama_local` API/UI path
  for one unambiguous room width/depth increase. A broad legacy model schema
  initially produced unsupported directives (three live HTTP 422 failures).
  The narrow guided schema now requires operation, canonical room type, axis and
  bounded positive delta, with unrelated fields null. AI supplies intent only;
  OR-Tools regenerates and independently validates geometry before immutable append.
  Unsupported requests, locked/ambiguous rooms and changes to saved site constraints
  fail closed. No automatic provider retry or fallback was added.
- Manual editor/history: exact room locks and single-room dimensions can now be
  persisted as immutable revisions; prior UI only prepared commands. Unsupported
  command kinds are explicitly rejected. History displays revision, parent and hash.
  Changed single-floor confirmed snapshots also receive deterministic access checks
  through the generic append route; stale-parent rejection precedes access checks.
  Physically identical legacy snapshots remain readable/saveable.
- Responsive defects: small CSS corrections remove mobile card/header/input
  overflow and excessive generation-entry horizontal padding. No redesign.
- Candidate availability: a browser run returned two valid alternatives, with four
  others correctly rejected for real unallocated site gaps. Strict site accounting
  and material deduplication remain intact. A second bounded deterministic search
  pass uses existing variants on the same validated candidate-specific concepts
  when fewer than four materially distinct plans survive; every rejection remains
  visible and attempt counts include the extra searches. No new AI call is made
  by this pass. Four alternatives are still a mandatory live acceptance gate.

### Executed evidence so far

- Affected Python suite: **405 passed**, five deprecation warnings, 598.82 s
  (`.local/phase29f-evidence/blocker-affected-final.log`). Earlier two new compact
  ground-only regressions were reproduced and fixed by removing forced lobby
  targets. Both compact fixtures also pass after public-graph prevention.
- Integrated focused suite: **189 passed**, three deprecation warnings, 69.92 s
  (`continuation-focused-final.log`). Subsequent bounded revision schema tests
  passed; current focused Ollama suite: **79 passed**, 1.48 s
  (`ollama-focused-current.log`). Public-graph fixed-placement regressions: two
  passed (disconnected public pairs rejected; connected arrangement accepted).
- Ruff passed. Configured mypy passed **236 source files**. An intentionally
  broader ad-hoc mypy invocation including test modules exposed typing errors
  outside the configured source scope; it is not the configured gate. First final
  validate invocation found three new local variable typing conflicts in the
  graph code; those were corrected and the configured gate passed again.
- Web unit suite previously executed in this continuation: **33 passed**;
  web format check passed. Final full Python/build/validate run is pending.
- Isolated live local billing fixture passed free entitlement allowance,
  consumed-free denial, paid-project credit exhaustion, continued existing paid
  project authorization, disabled checkout, and staging/production bypass denial.
  UUID-named persistent fixture databases preserve operator acceptance data;
  generation allowance is proven through authorization/success accounting, not
  another AI generation or any payment gateway call (`billing-limit-live.log`).
- Real Edge/Playwright desktop 1440, tablet 768 and mobile 390 checks passed
  dashboard/projects/generation/editor (`browser-layouts-qualified.log`). Empty
  project/search/input and safe missing-project error states passed
  (`browser-states.log`). Real PNG upload/analysis/Vastu advisory passed
  (`browser-upload-final.log`); earlier JPEG/PDF and invalid-upload API evidence
  remains qualified above.
- Project `eda79de2-33b9-48fb-b6bd-d8d3b4a51c75`: real browser Ollama revision
  interpretation, deterministic revision, history/reopen, manual lock undo/redo,
  exact save/reopen and three viewport widths passed. Original revision/document
  hash remained byte-equivalent; contiguous ancestry was checked through the API.
  Kitchen width increased from 2,630 to 2,960 mm for a requested 100 mm increase
  (historical defect; superseded by the exact-dimension qualification below).
- Identified local Ollama tray/server were stopped and restored in `finally`.
  Browser revision outage returned safe **503** with visible unavailable error
  (`browser-revision-outage-final.log`); recovery through real Ollama revision,
  history/editor/save and all three widths passed (`browser-revision-recovery.log`).
  An initial outage harness failed only because Next's route-announcer also has
  role=alert; selector was narrowed to the actual provider-error message.

### Historical checkpoint before final browser acceptance

At that checkpoint, four-alternative generation/inspection/selection and exact-revision browser
exports were pending; these are completed in the evidence below. Final complete validation, updated-runtime persistence
and final Git/diff evidence must finish before any GREEN claim. Earlier local
Vastu 3/3 plus recovery 3/3 evidence is preserved; it has not been rerun needlessly.
No hosted providers, Supabase, payment gateways or Git history/staging were used.


## Final continuation evidence (2026-10-05)

This section supersedes the earlier pending browser list and the historical
minimum-only revision result. Final gates and runtime restart checks are complete;
the final result above is authoritative.

- Real browser confirmed generation returned **four** alternatives; each was
  inspected, then candidate selection saved canonical revision
  `04361832-c18c-5dd7-afb4-ea39dbb12707` in project
  `f2603dae-292e-4d38-b110-ee2aec730dae`.
  `browser-20261005T130713Z-journey/generation.json` and `results.json` retain
  local evidence. Latest independent canonical checks passed on all four:
  no bedroom transit, public access intact, 3,000 mm road-facing vehicular
  opening, usable bay including no interior obstruction, valid content hashes,
  and unchanged qualified Vastu bundle (`latest-vehicle-proof.json`).
- Candidate availability required one bounded additional deterministic pass
  through the existing six advisory concepts/solver variants. Maximum attempts
  are twelve; failed candidates remain rejected, material deduplication remains
  intact, and no AI/provider retry or fallback occurs. Public circulation uses
  deterministic lower-rank doorway-connected parents to prevent disconnected
  public components before generation, with final graph validation authoritative.
- Exact revision sizing exposed a further real defect: solver minimum dimensions
  are clear dimensions plus a 230 mm wall reserve, while canonical polygons and
  solver maximum dimensions are envelopes. Treating envelope target as clear
  minimum made +100 mm become +330 mm; setting both bounds to that value made
  exact generation infeasible. The helper now converts envelope target to clear
  minimum before generation, preserves original minima/maxima, and validates
  exact achieved envelope geometry. Natural-language target rounding to the
  existing 10 mm solver grid occurs before generation, is explicitly disclosed,
  and is returned as requested/applied/rounding metadata; manual exact off-grid
  edits fail closed. No post-generation clamping occurs.
- Real local Ollama browser revision changed kitchen **2,970 -> 3,070 mm** for
  a requested +100 mm, with zero rounding. Original selected document remains
  byte-equivalent; all eight revisions have contiguous immutable ancestry.
  Evidence: `browser-20261005T134059Z-editor/revision.json` and
  `latest-immutable-ancestry-proof.json`. A later repeat increase correctly failed
  against the now-exact saved maximum and appended nothing.
- Browser manual lock, undo, redo, save, history/reopen and layouts at desktop
  1440, tablet 768, mobile 390 passed (`browser-exact-editor-final.log`). The
  Narrow-mobile and tablet manual interactions also passed under the executed
  `--viewport-width 390` and `--viewport-width 768` commands recorded in
  `responsive-manual-command-evidence.json` and the corresponding mobile/tablet
  editor logs. The canvas harness now clicks actual canonical room centres using the real fit
  transform rather than a coarse screen grid. Duplicate sibling React keys
  found during this check were corrected with a chat-specific key.
- Browser JPEG/PDF/DXF downloads passed for final saved revision
  `57ad4c12-8855-4164-894f-9858b2684bd8`: server export manifest revision/candidate
  IDs and downloaded file SHA256 match (`browser-latest-exports-final.log`).
  Initial selected-revision exports also passed; saved editor now exposes the
  existing exact-revision export API directly.
- Production-built web correctly blocks development bearer credentials; local
  browser acceptance therefore runs Next development mode. This protection is
  preserved. A readiness race and production-runtime authentication mismatch in
  harness runs were corrected without changing auth policy.
- New manual exact-dimension API coverage has four passing cases; revision chat
  coverage has eleven passing cases. These supplement the earlier focused and
  affected suite evidence. Final full validation is running. A test module name
  collision discovered at collection was corrected by naming the new API tests
  `test_saved_editor_commands.py`; no application defect was concealed.
- Final adversarial review additionally checks that a walkable opening span lies
  on both room boundaries after manual physical edits, with valid wall offsets.
  Internal and exterior guards passed 26 focused cases and the final full gate;
  all four alternatives plus the exact saved revision passed final-doorway-proof.json.

No hosted AI, Supabase mutation, payment gateway, Git staging/history operation,
or deletion of operator evidence occurred. All local evidence is under
`.local/phase29f-evidence/`; fixture databases and archives remain intact.


### Exact Phase 29F changed source/evidence files

This includes the earlier working-tree fixes preserved during continuation;
pre-existing untracked archives/backups and generated local evidence are excluded.

```text
apps/api/app/editor_command_routes.py
apps/api/app/main.py
apps/api/app/revision_chat_routes.py
apps/api/tests/test_projects.py
apps/api/tests/test_revision_chat.py
apps/api/tests/test_saved_editor_commands.py
apps/web/next-env.d.ts
apps/web/src/api/client.test.ts
apps/web/src/api/client.ts
apps/web/src/app/globals.css
apps/web/src/components/editor/ProjectEditorPage.tsx
apps/web/src/components/editor/RevisionChatPanel.tsx
apps/web/src/components/editor/RevisionExportPanel.tsx
apps/web/src/components/editor/RevisionHistoryPanel.tsx
apps/web/src/components/generation/Phase26CCandidateWorkspace.tsx
apps/web/src/components/generation/phase26c.css
docs/CURRENT_HANDOFF.md
docs/exec-plans/active/phase29f-local-acceptance.md
docs/phase29f-local-acceptance.md
docs/phase29f-revision-access.md
python/ai_vastu/architectural_brain/candidate_engine.py
python/ai_vastu/architectural_brain/ollama_local_provider.py
python/ai_vastu/architectural_brain/ollama_local_revision.py
python/ai_vastu/architectural_brain/site_accounting.py
python/ai_vastu/architectural_geometry/circulation.py
python/ai_vastu/generation/service.py
python/ai_vastu/geometry/__init__.py
python/ai_vastu/geometry/shapely_validator.py
python/ai_vastu/geometry/types.py
python/ai_vastu/ollama_local_http.py
python/ai_vastu/requirements/finalization.py
python/ai_vastu/requirements/generation_adapter.py
python/ai_vastu/requirements/saved_revision.py
python/ai_vastu/requirements/store.py
python/ai_vastu/solver/rectangular_cp_sat.py
python/ai_vastu/validation/revision_access.py
python/ai_vastu/validation/validator.py
python/ai_vastu/validation/vehicle_access.py
python/ai_vastu/vastu_reasoning/providers/ollama_local.py
scripts/check-phase26c.py
scripts/phase29f-billing-acceptance.py
scripts/phase29f-browser-acceptance.py
scripts/phase29f-local-acceptance.py
scripts/start-phase29f-api.ps1
tests/architectural_brain/test_bounded_candidate_search.py
tests/architectural_brain/test_canonical_wall_site_accounting.py
tests/architectural_brain/test_site_accounting_critic.py
tests/architectural_geometry/test_circulation.py
tests/generation/test_vehicle_access.py
tests/ollama_local/test_ollama_local_adapters.py
tests/ollama_local/test_ollama_local_brain_contract.py
tests/ollama_local/test_ollama_local_http.py
tests/projects/test_editor_commands.py
tests/requirements/test_generation_adapter.py
tests/solver/test_circulation_repair.py
tests/solver/test_public_circulation_connectivity.py
tests/test_phase26c3_policy.py
tests/validation/test_revision_access.py
tests/validation/test_validator.py
```

The 59-path inventory contains 58 substantive Phase29F source/test/docs/script
files plus generated `apps/web/next-env.d.ts`. Development/build runs temporarily
change its type-import paths; qualified imports were restored. Git status still
flags that generated file while its normalized content diff is empty. Final
status: 35 tracked files flagged modified (34 with content diffs), 24 newly
untracked acceptance files, zero staged files. Operator archives/backups are
untouched. HEAD remains `1940b09fe729fb5d37ac007598c7e245d0fdacdf`.
