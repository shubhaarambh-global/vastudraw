# Current Handoff

## Completed phase

Stage 2D9H - professional architectural plan renderer - is GREEN on the
affected renderer, export, generation, and static-validation gates.

Canonical `PlanDocument` geometry remains authoritative and at version `1.1.0`.
The renderer now presents that geometry as a restrained architectural drawing
without changing layouts or inventing canonical rooms, walls, openings, stairs,
or site spaces.

The full backend repository gate is 444 passed and the same 13 documented
UI/schema/release-policy failures. There are no new 2D9H regressions.

## Preflight findings

- The browser candidate preview was a room-polygon diagram with flat category
  fills and labels. It did not render canonical walls, openings, stairs,
  dimensions, north, scale, furniture, fixtures, or purposeful site spaces.
- The Python JPEG/PDF exporters rendered some canonical geometry but lacked a
  shared professional presentation model, opening gaps and symbols, useful stair
  graphics, room-aware presentation symbols, automatic dimensions, and site
  annotations.
- DXF already preserved vector geometry and was the appropriate path to extend
  with stable architectural layers rather than replace.
- `DrawingScene` projected rooms, walls, openings, stairs, fixtures, furniture,
  dimensions, roads, and site boundary, but omitted canonical
  `Floor.site_spaces`. This was an export-scene projection gap, not a canonical
  schema gap.
- Existing `PlanDocument 1.1.0` models contain all authoritative information
  needed for this phase. No `PlanDocument`, API, or persisted schema evolution
  was necessary.
- The current generator produces valid canonical doors and stairs. Some plans
  contain few or no windows; the renderer deliberately does not invent them.

## Renderer architecture

### Authority boundary

- Canonical floor boundaries, room polygons, walls, openings, stairs, roads,
  purposeful site spaces, canonical furniture/fixtures, orientation, and floor
  identity are read-only renderer inputs.
- Presentation-only graphics include derived door leaf/swing orientation where
  hinge data is absent, stair tread/nosing and direction marks, schematic room
  furniture/fixtures, a vehicle symbol, labels, dimension strings, north arrow,
  scale bar, and sheet annotations.
- Derived symbols are deterministic, remain inside their owning canonical
  geometry, avoid door clearance zones, and never modify the source document or
  its content hash.
- Canonical furniture and fixtures take precedence over derived presentation
  symbols.

### Shared presentation semantics

- `python/ai_vastu/exporting/presentation.py` builds a deterministic,
  renderer-neutral presentation model for room labels, doors, windows, plain
  openings, stairs, symbols, dimensions, and site-space labels.
- `apps/web/src/components/generation/professional-plan-model.ts` applies the
  same policy in the browser from the canonical API document shape.
- Both paths use stable floor/object ordering and one centralized transform from
  canonical millimetres to viewport coordinates. Y-axis inversion occurs only
  in that transform.
- Export bounds include annotation padding so external dimensions, north, and
  scale graphics do not clip.

### Walls and openings

- Canonical wall axes and thickness are rendered as architectural wall bands.
  Exterior walls use a heavier hierarchy than interior partitions.
- Wall bands are split at canonical openings, so doors and windows read as real
  breaks rather than symbols painted over continuous walls.
- Doors use the canonical opening position and width. A deterministic hinge side
  and swing direction is derived only for presentation when canonical hinge
  metadata is absent; leaf and swing remain anchored to the opening.
- Windows use canonical window openings and conventional parallel glazing
  lines. No opening is generated from room type or facade preference.
- Plain non-door/non-window openings remain visible without being mislabeled.

### Stairs

- Canonical 2D9G `Stair.footprint`, direction, width, tread, landing depth, and
  floor association drive the drawing.
- The renderer shows the core outline, deterministic tread lines, landing
  division, direction arrow, and `UP` annotation.
- Multi-floor models preserve each floor's independent canonical stair and make
  aligned cores visually comparable between floor tabs/exports.

### Rooms, furniture, and fixtures

- Every canonical room receives a room-type title and dimension line. Rectangles
  use clear width x depth; non-rectangular rooms use an explicitly bounded `MAX`
  description rather than claiming exact clear dimensions.
- Fills are subtle neutral/pastel accents and the linework remains legible in
  monochrome.
- Deterministic room-aware symbols include beds, sofas, dining tables, desks,
  wardrobes, WC/basin/shower graphics, kitchen counters/sink/hob, and parking
  vehicles where the owning room is large enough.
- Symbols are fitted and clipped by canonical room/parking bounds, kept away
  from canonical door zones, offset from central labels, and omitted rather than
  forced into unsuitable geometry.

### Site, dimensions, north, scale, and sheets

- Canonical site boundary, road edges, parking, and purposeful site spaces are
  rendered with restrained differentiated graphics and canonical kind labels.
- Parking retains its real canonical geometry; the car is a fitted
  presentation-only symbol.
- Automatic overall site and building dimensions use millimetre geometry with
  metre labels, extension lines, witness marks, and consistent offsets.
- Room labels use metres with sensible precision and no false millimetre-level
  display precision.
- The north arrow is derived from document orientation. It is not hard-coded to
  north-up.
- Responsive/on-screen output uses a measured 5 m scale bar instead of claiming
  a paper ratio. JPEG/PDF output uses the same explicit scale indication.
- Floor names use stable identities (`Ground Floor`, `First Floor`, etc.). The
  web renderer presents one floor at a time with tabs; export service can emit a
  stable bundle for every floor.

## Export integration

- JPEG and PDF now apply the same professional hierarchy: site, subtle room/site
  fills, symbols, stairs, wall bands, openings, labels, dimensions, north, scale,
  and sheet title.
- DXF retains authoritative vectors and adds stable layers for site graphics,
  doors, windows, stair treads, and derived automatic dimensions.
- `export_all_floor_bundles` exports each canonical floor in stable floor-index
  order without overlaying floors or cloning ground-floor geometry.
- Browser candidate previews use each candidate's own `PlanDocument`; equivalent
  documents are not visually diversified by IDs or metadata.

## Schema and version impact

- Canonical `PlanDocument` stays at `1.1.0`.
- No canonical model field, JSON schema, migration, content-hash rule, or API
  contract changed.
- Transient export `DrawingScene` advanced from `1.0.0` to `1.1.0` to project
  canonical purposeful site spaces. It is an internal renderer scene, not the
  persisted canonical document. Existing documents are re-materialized through
  `build_drawing_scene`.
- Renderer execution is covered by a source-document hash non-mutation test.

## Files changed for 2D9H

Python/export:

- `python/ai_vastu/exporting/presentation.py` (new)
- `python/ai_vastu/exporting/models.py`
- `python/ai_vastu/exporting/scene.py`
- `python/ai_vastu/exporting/geometry.py`
- `python/ai_vastu/exporting/jpeg_exporter.py`
- `python/ai_vastu/exporting/pdf_exporter.py`
- `python/ai_vastu/exporting/dxf_exporter.py`
- `python/ai_vastu/exporting/service.py`
- `python/ai_vastu/exporting/__init__.py`
- `docs/exporting/phase-13-contract.md`

Browser renderer:

- `apps/web/src/components/generation/professional-plan-model.ts` (new)
- `apps/web/src/components/generation/ProfessionalPlanCanvas.tsx` (new)
- `apps/web/src/components/generation/professional-plan-model.test.ts` (new)
- `apps/web/src/components/generation/Phase26CCandidateWorkspace.tsx`
- `apps/web/src/components/generation/phase26c3.css`
- `apps/web/package.json`

Tests and repository hygiene:

- `tests/exporting/test_professional_renderer.py` (new)
- `.gitignore`
- `docs/CURRENT_HANDOFF.md`

The worktree also contains extensive pre-existing UI/API/billing/archive/script
and generated-package changes. They were preserved and not attributed to 2D9H.

## Tests added

Python professional-renderer coverage (9 tests) verifies:

- scene 1.1 site-space projection and source hash immutability;
- exterior/interior wall thickness and canonical opening gaps;
- deterministic canonical-only door and window rendering;
- stair footprint, treads, landing, and direction;
- room labels, room dimensions, site/building dimensions, north, and scale;
- parking, sanitary, kitchen, and furniture-symbol containment;
- every canonical floor exported separately with aligned core geometry;
- JPEG/PDF/DXF semantic consistency and deterministic output;
- candidate output follows candidate-specific canonical geometry.

Browser professional-plan-model coverage (7 tests) verifies:

- centralized orientation transform and wall line hierarchy;
- canonical-only openings plus deterministic door/window graphics;
- labels, dimensions, north, scale, purposeful site space, and parking graphics;
- derived furniture/fixture/vehicle containment;
- canonical fixture/furniture precedence;
- stable multi-floor ordering and visual stair alignment;
- determinism, source immutability, and candidate-specific models.

## Representative output inspection

Temporary SVG/JPEG render artifacts were generated and visually inspected, then
removed, for:

- the established approximately 30 x 50 ft east-facing residential brief;
- parking plus puja plus multiple sanitary spaces;
- a genuine G+1 plan with canonical 2D9G stairs on both floors;
- ground and upper floors independently.

The inspection confirmed recognizable entrances and door swings, kitchen,
bedrooms, sanitary spaces, parking/car, stair treads and `UP` direction, room and
overall dimensions, north, scale, and unclipped sheet composition. Furniture was
moved away from label centers after this review. No QA artifacts were committed.

## Validation results

Focused renderer/export gates:

- `pytest tests/exporting` - 19 passed.
- `pytest tests/exporting tests/plan_schema` - 39 passed.
- Browser professional renderer tests - 7 passed.

Affected backend gates:

- Focused 2D9F/2D9G multi-floor and vertical architecture tests - 27 passed.
- Architectural geometry, constraints, generation, solver, and requirements -
  107 passed, plus 3 Windows-ACL-sensitive `tmp_path` tests rerun with a
  repository-local fixture - 3 passed.
- Architectural brain, multi-candidate, exporting, plan-schema, Vastu, and
  Vastu-reasoning suites - 97 passed.
- Total affected backend gate - 207 passed.
- Combined affected backend plus focused browser renderer gate - 214 passed.

Static and frontend gates:

- Ruff on all 2D9H implementation and test files - PASS.
- `mypy python` - PASS across 191 source files.
- Web TypeScript typecheck - PASS.
- Web lint - PASS.
- Full web test command - 23 passed, 1 existing navigation-policy failure
  (`navigation.test.ts` expects `generation`, while the pre-existing dirty UI
  route is `new-plan`). This is the documented navigation/UI baseline, not a
  renderer regression.
- Next.js production source compilation completed successfully (18.3 s in the
  standard build and 1.843 s in compile-only mode). Both commands then hit the
  managed Windows environment's `spawn EPERM` while starting Next worker
  processes. Independent lint and TypeScript gates are green.
- Whole-repository Ruff additionally sees a pre-existing import-order issue in
  untracked `scripts/build_resplan_precedent_index.py`; 2D9H files remain green.

Full backend suite baseline comparison:

- 457 tests collected: 444 passed, 13 failed.
- All 13 failing identifiers exactly match the documented preflight baseline.
- No new, renamed, or unexplained 2D9H failure exists.

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

- Door swing/hinge graphics are deterministic presentation derivations when the
  canonical opening omits hinge metadata. They are not authoritative joinery
  decisions.
- The renderer exposes the current generator's limited window population; it
  intentionally does not add facade windows.
- Furniture, sanitary fixtures, kitchen counters, and vehicles are schematic
  communication aids, not detailed interior, cabinetry, MEP, accessibility, or
  product specifications.
- Collision avoidance is bounded and deterministic (fit checks, reserved door
  zones, label offsets, and text halos), not a general-purpose label optimizer.
- Stair graphics communicate the canonical architectural core but are not
  fabrication, structural, fire-code, or handrail details.
- JPEG/PDF and browser rendering share semantics and tests but use Python and
  TypeScript implementations respectively; future primitives should keep the
  parity tests current.
- PDF export remains one floor per artifact. `export_all_floor_bundles` supplies
  every floor, but there is not yet a combined multi-page sheet set.
- The managed Windows runner prevents a final Next.js worker-spawn phase despite
  successful compilation, typecheck, lint, and component tests.
- A failed pytest basetemp experiment left an inaccessible ignored
  `.pytest-2d9h-temp/` directory due Windows ACLs. It contains no tracked or
  required artifacts and no longer appears in Git status.

## Git status

The worktree remains intentionally dirty with the 2D9H files above plus
pre-existing UI/API/billing/archive/script and generated-package changes. No
reset, checkout, branch rewrite, commit, or destructive cleanup was performed.
Temporary QA output and temporary test-fixture source were removed. The
inaccessible pytest ACL directory is ignored as documented above.

## Recommended next stage

Stage 2D9H is ready to hand off. Stop here rather than beginning another major
generation phase.

Recommended next work: integrate the per-floor professional bundles into the
product's download/sheet workflow (including an optional combined multi-page
PDF), then deliberately reconcile the legacy schema/navigation/release-policy
baseline and run the production build in an environment that permits Next.js
worker processes.
