# Third-party dependency register

Phase 0 records intended and bootstrap dependencies. Exact production versions are pinned in the phase that introduces each dependency.

| Dependency | Purpose | License | Phase 0 status | Commercial-use review |
|---|---|---|---|---|
| FastAPI | API framework | MIT | bootstrap dependency | acceptable; verify exact release notices when pinned |
| Pydantic | schema/runtime validation | MIT | bootstrap dependency | acceptable; verify exact release notices when pinned |
| Uvicorn | local ASGI server | BSD-3-Clause | bootstrap dependency | acceptable; verify exact release notices when pinned |
| pytest | Python tests | MIT | development dependency | acceptable |
| Ruff | Python lint/format policy | MIT | development dependency | acceptable |
| mypy | Python static typing | MIT | development dependency | acceptable |
| TypeScript | frontend/contracts typing | Apache-2.0 | development dependency | acceptable |
| ESLint | TypeScript linting | MIT | development dependency | acceptable |
| Prettier | formatting | MIT | development dependency | acceptable |
| Google OR-Tools | CP-SAT optimization | Apache-2.0 | Phase 7: 9.15.6755 | accepted behind solver adapter |
| NetworkX | circulation/access graph analysis | BSD-3-Clause | 2D9L: 3.6.1 | accepted as non-authoritative graph-analysis layer |
| Clipper2 | integer polygon geometry | BSL-1.0 | Phase 3 via pyclipr 0.1.8 | accepted behind adapter |
| Shapely / GEOS | independent topology validation | BSD-3-Clause / LGPL-2.1-or-later | Phase 3: Shapely 2.1.2 | accepted as verification layer; retain license obligations |
| Konva / react-konva | browser CAD-like interaction | MIT | Phase 12: Konva 10.5.0 / react-konva 19.2.7 | accepted behind non-authoritative renderer boundary |
| ezdxf | DXF export/import validation | MIT | planned Phase 13 | review/pin before integration |
| LibreDWG | experimental DWG backend | GPL-3.0-or-later | experimental only | legal/product review required before distribution/integration |
| ODA Drawings SDK | production DWG candidate | commercial | evaluation only | commercial license required |

## Policy

Every direct production dependency added later must record exact version, upstream repository, license, purpose, security review date, and upgrade policy before its phase can pass.

## json-schema-to-typescript

- Repository: https://github.com/bcherny/json-schema-to-typescript
- License: MIT
- Phase 1 role: development-only generation of TypeScript declarations from the authoritative Pydantic-generated JSON Schema.
- Reviewed version line: 16.x (16.0.0 current during Phase 1 design review, September 2026).
- Runtime dependency: No.


## Phase 3 additions

### pyclipr 0.1.8
- Purpose: Python adapter for the Clipper2 primary polygon kernel.
- License: Boost Software License 1.0.
- Commercial use: compatible with project use; retain required notices.
- Boundary: imported only by `python/ai_vastu/geometry/clipper_kernel.py`.
- Risk: smaller wrapper project than upstream Clipper2; kept behind replaceable adapter.

### Clipper2
- Purpose: underlying integer polygon Boolean/offset engine used through pyclipr.
- License: Boost Software License 1.0.
- Architecture role: primary deterministic polygon engine.

### Shapely 2.1.2 / GEOS
- Purpose: independent geometry/topology validation and cross-checking.
- Shapely license: BSD-3-Clause. GEOS: LGPL-2.1-or-later.
- Architecture role: verifier only; never canonical storage.

### Hypothesis 6.x (development only)
- Purpose: property-based geometry invariant tests.
- License: MPL-2.0.

### types-Shapely 2.1.0.20260728 (development only)
- Purpose: static type stubs required by strict MyPy for Shapely 2.1.x.
- Runtime dependency: No.
- Phase introduced: Phase 3 validation hardening.

## Phase 4 additions

Phase 4 introduces no new third-party runtime dependency. The Vastu rule framework is implemented with the existing Pydantic/domain stack and Phase 3 geometry kernel.


## Phase 7 additions

### Google OR-Tools 9.15.6755
- Purpose: CP-SAT integer constraint optimization for rectangular room placement.
- Upstream: https://github.com/google/or-tools
- Package: https://pypi.org/project/ortools/
- License: Apache License 2.0.
- Release reviewed: 9.15.6755 (January 14, 2026).
- Python 3.12 Windows wheel: available upstream.
- Architecture boundary: imported only by `python/ai_vastu/solver/rectangular_cp_sat.py`.
- Phase 7 usage: integer room variables, multiplication equality, interval variables, `NoOverlap2D`, bounded deterministic single-worker search.
- Upgrade policy: do not upgrade across solver versions without golden-plan and reproducibility regression tests.

## Phase 8 additions

Phase 8 introduces no new third-party dependency. Architectural geometry construction is implemented in the deterministic domain layer using the existing canonical PlanDocument, Phase 7 solver contracts, and Python standard library. CAD/PDF dependencies remain deferred.


## Phase 9 dependency note

Phase 9 adds no third-party runtime dependency. Architectural validation reuses the frozen
Clipper2 adapter (`pyclipr==0.1.8`) as the primary integer-mm polygon engine and
Shapely/GEOS (`shapely==2.1.2`) as the independent topology/operation verifier. Hypothesis is
reused only in the existing development/test dependency set for validation-property tests.

## Phase 10 dependency note

Phase 10 scoring and diversity selection add no third-party runtime dependency. They consume the
existing canonical constraints, solver, geometry, validation, and plan-schema contracts.

## Phase 11 dependency note

Phase 11 adds no third-party runtime dependency. Its reference persistence adapter uses Python's standard-library `sqlite3` module behind the `ProjectRepository` boundary. PostgreSQL/Supabase remains the production database target and is not claimed implemented by this phase.


## Phase 12 additions

### Next.js 16.3.3
- Purpose: web application framework and production build/runtime.
- License: MIT.
- Phase 12 pin: 16.3.3 (current patched Active LTS line at review time, September 2026).

### React / React DOM 19.3.0
- Purpose: editor UI component runtime.
- License: MIT.

### Konva 10.5.0 / react-konva 19.2.7
- Purpose: 2D scene graph, hit testing and Canvas interaction.
- License: MIT.
- Boundary: renderer/input only; Konva state is never canonical project geometry.

### Zustand 5.0.15
- Purpose: transient editor viewport, selection, layer and staged-command state.
- License: MIT.
- Boundary: no persistence authority; canonical revisions remain in the backend project repository.


## Phase 13 additions

### ezdxf 1.4.4
- Purpose: DXF R2018 generation, architectural layers and native dimensions.
- License: MIT.
- Python support: >=3.10.
- Architecture boundary: imported only by `python/ai_vastu/exporting/dxf_exporter.py`.
- Canonical units: document/modelspace configured as millimetres.

### ReportLab 5.0.1
- Purpose: programmatic vector PDF generation.
- License: BSD.
- Python support: >=3.9.
- Architecture boundary: imported only by `python/ai_vastu/exporting/pdf_exporter.py`.
- Determinism: Canvas invariant mode is enabled for reproducible repeated output within the pinned runtime.

### Pillow 12.3.0
- Purpose: JPG raster preview/export.
- License expression: MIT-CMU.
- Python support: >=3.10.
- Architecture boundary: imported only by `python/ai_vastu/exporting/jpeg_exporter.py`.
- Raster pixels are presentation output only and never canonical geometry.


### types-reportlab 5.0.0.20260911 (development only)
- Purpose: static typing stubs for ReportLab used by strict MyPy validation.
- License: Apache License 2.0.
- Runtime authority: none; development/test dependency only.
- Production PDF behavior remains provided exclusively by pinned ReportLab.


## Phase 14 DWG provider assessment

Phase 14 adds **no bundled DWG SDK or binary dependency**. Open Design Alliance Drawings SDK is recorded as the preferred external production candidate and GNU LibreDWG is recorded as unsuitable for the R2018 production write target. Any provider runtime must be licensed/installed separately and pass repository qualification plus external CAD round-trip tests.

## Phase 15 dependency note

Phase 15 introduces no new third-party runtime dependency. It composes existing
repository metadata and subsystem contracts into a deterministic release-readiness
gate.

## Phase 19 additions

- PyJWT — JWT signature/claim verification at the FastAPI authentication boundary.
- `@supabase/supabase-js` — browser-side Supabase Auth session management only; API
  authorization remains independent and server-enforced.

## Stage 2D9L additions

### NetworkX 3.6.1
- Purpose: deterministic circulation/access graph analysis, connected-component diagnostics and articulation-point analysis.
- License: BSD-3-Clause.
- Architecture boundary: graph computation only. NetworkX does not author room geometry, walls, doors or Canonical PlanDocument data.
- Authority: canonical wall/opening geometry and the existing circulation validators remain authoritative; graph edges are supplied only after deterministic geometry proves a door-capable relationship.
- Upgrade policy: retain deterministic topology regressions and rerun circulation/generation qualification before changing the pinned version.
