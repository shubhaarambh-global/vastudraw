# Current Handoff

## Completed phase

Stage 2D9G — genuine deterministic vertical residential architecture — GREEN on
the affected backend gate.

The full repository is not green. Its unchanged 13 UI/schema/release-policy
baseline failures remain. No new 2D9G failure exists.

## Preflight findings

- Stage 2D9F was green and already distributed the complete room program across
  Ground through G+3, solved floors independently, and exposed a reserved
  upper-floor circulation anchor.
- The current worktree contained an unintegrated 2D9G draft: vertical planner
  and validator models, solver reservation hooks, wet-stack objectives, and
  generation-result fields existed, but `generation/service.py` still returned
  `RESERVED_FOR_2D9G` and did not invoke them. The partial result-model change
  therefore made the reproduced 2D9F multi-floor tests fail before completion.
- Canonical `Floor.stairs` and `Stair` already provide authoritative footprint,
  stair type, width, riser, tread, riser count, floor height, landing depth,
  direction, and headroom. No canonical replacement or schema evolution was
  required.
- The frozen production Vastu bundle contains directional room rules but no
  authoritative above/below, inter-floor puja/sanitary, or other vertical Vastu
  rule. No new vertical Vastu belief was invented.
- Existing complete-building deduplication already includes staircase rooms in
  direct tolerance-aware room geometry comparison. Material core movement is
  distinct; UUID/metadata changes and small jitter remain equivalent.

## 2D9G architecture

### Building-level core planning

- Multi-floor generation calls `plan_vertical_architecture` before any floor is
  solved.
- The planner computes the rectangular common intersection of every configured
  floor/buildable footprint, snaps to the solver lattice, and chooses one of six
  bounded deterministic positions from the candidate search variant.
- The current V1 core uses a minimum 2300 x 3500 mm dog-legged stair envelope,
  snapped upward to the configured solver lattice, with a
  1000 mm flight width, 270 mm tread, 1000 mm landing, and 2100 mm planning
  headroom.
- Riser count and riser height are derived deterministically so
  `riser_mm * number_of_risers == floor_to_floor_mm` within the supported
  150–190 mm planning range. For the default 3000 mm floor height this is 20
  risers at 150 mm.
- The core serves every consecutive stable floor index from zero. Identical
  input, seed, solver step, and candidate strategy produce identical geometry
  and identity.
- Ground-only generation bypasses this path and receives no inter-floor stair.

### Solver reservation and canonical geometry

- `ResidentialPlanningConfig.vertical_core_footprint` carries the building core
  into every per-floor CP-SAT solve.
- `_apply_vertical_core_reservation` pins exactly one staircase room envelope to
  the reserved footprint before no-overlap, topology, circulation, and final
  geometry acceptance. Rooms are never solved first and then surgically moved.
- Hard residential topology makes the staircase share a door-capable wall with
  lobby, corridor, or foyer. Automatic opening construction creates real doors
  on canonical walls; upper-floor circulation is rooted at the staircase room,
  not a metadata-only anchor.
- `StairBuildRequest` is derived from the core after the floor-specific compiled
  staircase instance is known. The existing geometry builder emits one real
  canonical `Stair` whose footprint is the staircase room polygon.
- Floor elevations now close deterministically as
  `base_elevation + floor_index * floor_to_floor_mm`.

### Whole-building circulation

- Per-floor door graphs remain the Stage 2D9E canonical wall/opening graphs.
- Ground circulation requires a real exterior dwelling entry. Upper-floor
  circulation starts at the canonical staircase room.
- Consecutive aligned staircase rooms create explicit vertical transfer edges.
- A building-wide breadth-first traversal starts at the ground dwelling entry,
  follows real horizontal doors and aligned stair transfers, and must reach
  every required non-vehicle room.
- Sanitary rooms remain reachable leaves but are never traversal nodes. A
  toilet/bath cannot become the mandatory path from the stair to another room.
- Stair access must be a real door to a circulation-capable non-sanitary room;
  corner contact, proximity, and short/non-door-capable shared edges do not
  qualify.

### Independent vertical validation

`validate_whole_building` runs after all floor solves and independently checks:

- exact consecutive floor count and elevation closure;
- complete whole-building room program;
- unique canonical room/wall identity and valid opening references;
- exactly one staircase room and canonical stair on every served floor;
- core served-floor relationship and consecutive footprint alignment;
- stair/core dimensional agreement and floor-height closure;
- containment in each canonical floor/buildable footprint;
- no overlap with non-stair required rooms;
- valid horizontal circulation and direct stair access on every floor;
- ground-entry-to-upper-room complete-building reachability;
- wet-stack analysis completion.

Bounded diagnostics include `VERTICAL_CORE_MISSING`,
`VERTICAL_CORE_MULTIPLE`, `VERTICAL_CORE_MISALIGNED`,
`VERTICAL_CORE_FLOOR_RELATIONSHIP_INVALID`, `STAIR_ACCESS_INVALID`,
`STAIR_CANONICAL_GEOMETRY_INVALID`, `STAIR_DIMENSIONS_INCONSISTENT`,
`STAIR_ROOM_OVERLAP`, `STAIR_OUTSIDE_FLOOR_FOOTPRINT`,
`HORIZONTAL_CIRCULATION_INVALID`, `VERTICAL_CIRCULATION_DISCONNECTED`,
`BUILDING_PROGRAM_INCOMPLETE`, `WET_STACK_DISPERSED`, and
`WET_STACK_UNPAIRED`.

Accepted multi-floor results must carry `vertical_circulation_status=VALIDATED`
and an accepted whole-building validation. Per-floor plus building diagnostics
are bound into the canonical `ValidationReport` during finalization.

### Wet-stack intelligence

Explicit wet/service classification uses the repository `RoomType` taxonomy:

- sanitary: attached toilet, common toilet, powder room, bath, servant toilet;
- service/plumbing: kitchen, utility, laundry.

The same building-level plumbing-zone anchor is passed to every floor solver.
Distance from each wet/service room center to this anchor is a soft weighted
CP-SAT objective (`WET_STACK_PROXIMITY`); exact repeated bathroom or kitchen
geometry is not required.

Post-solve analysis pairs each upper wet/service room with the nearest compatible
sanitary or service room on the immediately lower floor and records center
distance plus `ALIGNED`, `PROXIMATE` (at most 3000 mm), or `DISPERSED`.
Aligned/proximate/dispersed score 10000/7000/2500 basis points; unpaired upper
rooms score zero. Dispersion and unpaired rooms are warnings, not hard failures.
The architectural critic reports suboptimal stacks and plan-quality scoring now
evaluates this whole-building service-planning evidence.

Hard/soft policy:

- hard: real core space, solver reservation, containment, no overlap, canonical
  stair dimensions, alignment, access, and complete-building reachability;
- strong deterministic preference: common wet/service-zone proximity in CP-SAT;
- soft quality evidence: aligned/proximate/dispersed/unpaired stack diagnostics.

### Candidate architecture and deduplication

- Candidate search variants select materially different bounded core zones.
  The regression path solves and retains both lower-left compact and upper-left
  daylight alternatives.
- The same candidate core is reserved on every served floor.
- Complete-building direct tolerance-aware deduplication remains authoritative.
  A 50 mm core shift is equivalent; a 700 mm shift is material in the regression
  coverage. No quantized-hash equality regression was introduced.

### Architectural critic and quality review

- The critic now evaluates stair-rooted horizontal circulation on every upper
  floor, canonical stair presence, consecutive core alignment, and wet-stack
  quality.
- Horizontal puja/sanitary shared-wall rejection runs on every floor and the
  existing hard compiler/solver separation remains intact.
- Ground/site accounting and parking checks remain ground-oriented. Upper floors
  are not treated as independent parcels and parking is not migrated upward.

## Schema and version impact

- PlanDocument schema remains `1.1.0`.
- No canonical model field changed.
- No JSON schema regeneration, migration, API consumer update, or schema-version
  bump was required.
- Generation, solver, and vertical-validation contracts gained internal
  backward-compatible planning/result fields only.
- Canonical serialization and content hashes include the existing per-floor
  `Stair` geometry and the aggregated validation evidence and pass regression
  coverage.

## Files changed for 2D9G

- `python/ai_vastu/architectural_geometry/vertical.py`
- `python/ai_vastu/architectural_geometry/__init__.py`
- `python/ai_vastu/generation/models.py`
- `python/ai_vastu/generation/service.py`
- `python/ai_vastu/requirements/generation_adapter.py`
- `python/ai_vastu/requirements/finalization.py`
- `python/ai_vastu/solver/models.py`
- `python/ai_vastu/solver/rectangular_cp_sat.py`
- `python/ai_vastu/architectural_brain/critic.py`
- `python/ai_vastu/architectural_brain/scoring.py`
- `tests/requirements/test_phase2d9g_vertical_architecture.py`

The worktree also retains the pre-existing uncommitted 2D9A–2D9F, UI, schema,
API, archive, and user/generated changes. None were discarded.

## Tests added

`tests/requirements/test_phase2d9g_vertical_architecture.py` contains 19 tests
covering:

- unchanged ground-only behavior;
- G+1/G+2/G+3 continuous canonical cores;
- stable elevations and exact stair rise closure;
- real stair-to-circulation doors on every floor;
- isolated upper core, missing intermediate core, and unreachable upper room;
- sanitary-room transit rejection;
- stair overlap and floor-footprint containment;
- wet-stack aligned/proximate/dispersed evidence and scoring;
- solver-level soft wet-stack coordination;
- deterministic candidate core planning;
- material core alternatives through the real multi-candidate path;
- tolerance-aware vertical-core deduplication;
- canonical serialization/content hashes with stairs;
- whole-building critic and service-quality evidence.

Existing 2D9F provides 8 adjacent multi-floor/program/dedup tests. Existing
2D9E circulation and architectural-invariant suites continue to cover corner
contact, insufficient door wall, sanitary transit, and puja/sanitary separation.

## Validation results

Focused gate:

- `.\.venv\Scripts\python.exe -m pytest tests/requirements/test_phase2d9g_vertical_architecture.py tests/requirements/test_phase2d9f_multifloor.py -q -p no:cacheprovider`
  — 27 passed (19 2D9G + 8 preserved 2D9F).

Affected backend gates:

- `.\.venv\Scripts\python.exe -m pytest tests/architectural_geometry tests/constraints tests/generation tests/solver tests/requirements --ignore=tests/requirements/test_generation_orchestrator.py --ignore=tests/requirements/test_store_and_confirmation.py -q -p no:cacheprovider`
  — 107 passed.
- The 3 excluded tests use pytest `tmp_path`; the managed Windows environment's
  default pytest temp root returned `WinError 5`. They were rerun with a temporary
  repository-local `tmp_path` fixture and all 3 passed. The fixture was removed
  after validation.
- `.\.venv\Scripts\python.exe -m pytest tests/architectural_brain tests/multi_candidate tests/plan_schema tests/exporting tests/vastu tests/vastu_reasoning -q -p no:cacheprovider`
  — 88 passed.
- Total affected gate: 198 passed; no failures.

Static validation:

- Ruff on all 2D9G implementation/test files — PASS.
- `.\.venv\Scripts\mypy.exe python` — PASS, 190 source files.
- `git diff --check` — PASS (line-ending conversion warnings only).
- No frontend source was changed by 2D9G, so no new frontend build gate was
  required.

Full-suite baseline comparison:

- Full run collected 448 tests: 435 passed, 13 failed.
- The full run used cache and built-in tmpdir plugins disabled plus the same
  temporary repository-local `tmp_path` fixture to avoid the managed Windows
  temp-directory ACL failure.
- Every failing identifier exactly matches the documented preflight baseline;
  no new or changed failure exists.

Exact remaining baseline failures:

- `tests/release/test_readiness.py::test_current_public_mvp_is_ready_after_phase20b_freeze`
  — existing `SCHEMA_UNSUPPORTED` release gate.
- `tests/test_phase19_policy.py::test_dashboard_is_real_root_route_and_editor_remains_available`
  — existing public landing root versus legacy dashboard policy.
- `tests/test_phase1_policy.py::test_phase1_schema_contract`
  — existing schema `1.1.0` versus legacy `1.0.0` expectation.
- `tests/test_phase20_policy.py::test_phase20b_release_gate_is_ready_with_zero_blockers`
  — same existing release-readiness blocker.
- `tests/test_phase21_policy.py::test_phase21_saas_navigation_has_real_routes_and_active_state`
  — existing navigation source versus legacy route declaration policy.
- `tests/test_phase2_policy.py::test_phase2_does_not_change_plan_document_schema_version`
  — existing schema-version expectation.
- `tests/test_phase3_policy.py::test_geometry_vendor_imports_are_confined_to_adapters`
  — existing Shapely import in `architectural_brain/site_accounting.py`.
- `tests/test_phase4_policy.py::test_phase4_keeps_plan_document_schema_version_stable`
  — existing schema-version expectation.
- `tests/test_phase5_policy.py::test_phase5_keeps_plan_document_schema_version_stable`
  — existing schema-version expectation.
- `tests/test_phase6_policy.py::test_phase7_keeps_phase6_and_plan_contract_versions_stable`
  — existing schema-version expectation.
- `tests/test_phase9_policy.py::test_phase9_contract_versions_are_explicit_and_plan_schema_stays_stable`
  — existing schema-version expectation.
- `apps/api/tests/test_health.py::test_health`
  — existing API exposes schema `1.1.0` versus legacy `1.0.0` expectation.
- `apps/api/tests/test_release_readiness.py::test_release_readiness_endpoint_reports_ready_after_phase20b`
  — existing API release-readiness disposition is `BLOCKED`.

## Known limitations and open risks

- Supported generation remains bounded to four floors (Ground through G+3).
- The V1 planner supports one continuous rectangular dog-legged stair core, not
  multiple stairs, split cores, lifts, fire egress analysis, or arbitrary core
  shapes.
- Core dimensions are an architectural planning profile, not a structural,
  fire-code, accessibility, or local building-code certification.
- Core search is deliberately bounded to six deterministic perimeter/side zones.
  Some candidate strategies can be infeasible where parking, entry, program,
  and core compete; infeasible candidates fail closed.
- Every served floor must share a common footprint large enough for the current
  2300 x 3500 mm core.
- Wet-stack coordination uses room-zone proximity. It does not yet model shafts,
  pipe routes, fixture discharge points, slab penetrations, or MEP engineering.
- Wet stacking is intentionally soft unless an actual hard project rule is
  introduced later.
- No frozen authoritative vertical Vastu rule exists; only existing horizontal
  Vastu/puja-sanitary rules are enforced.
- The canonical `Stair` model has no explicit from-floor/to-floor fields;
  continuity is inferred from stable floor order plus aligned per-floor canonical
  stair geometry and independently validated.
- The worktree is extensively dirty from prior phases and user/generated files.
  A failed pytest basetemp experiment also left an inaccessible untracked
  `pytest-temp/` directory that only causes a Git directory-scan warning; no
  tracked content or test result depends on it.

## Git status

The worktree remains dirty with the pre-existing UI/schema/API/archive and
2D9A–2D9F changes plus the 2D9G files listed above. `git status --short` reports
the same broad modified/untracked surface and warns that `pytest-temp/` cannot be
opened. No commit, branch, reset, history rewrite, or destructive cleanup was
performed.

## Next phase

Stage 2D9H — professional architectural renderer.

Readiness: the 2D9G affected backend gate is green and canonical floors now
contain real stair geometry suitable for rendering. The full repository still
has exactly the unchanged 13 documented baseline failures.

Recommended first action: inspect the current renderer/export scene conversion
for canonical `Floor.stairs`, walls, openings, fixtures, labels, dimensions, and
multi-floor sheet composition, then design 2D9H against canonical geometry
without changing the approved SaaS UI or inventing renderer-only architecture.
