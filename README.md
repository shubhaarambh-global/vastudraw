# AI Vastu Architect — Phase 19

Current baseline: authenticated project dashboard, project-level authorization, deterministic generation, immutable revision persistence, and fail-closed production readiness.

## Scope

- explicit R2018/AC1032 DWG target
- evidence-backed provider registry
- ODA Drawings SDK preferred production candidate (runtime not bundled)
- GNU LibreDWG explicitly rejected as modern production writer
- version-bound qualification reports
- DWG signature, units, layer, scene-hash, semantic-count and extents checks
- generic `shell=False` external converter/inspector adapter
- production DWG export remains disabled until a real backend passes qualification

This phase deliberately does not claim that the repository alone can emit a production DWG without an installed qualified provider runtime.

## Validation

```powershell
pnpm validate
ruff check python apps/api tests scripts
mypy
pytest
```

## Local editor

```powershell
pnpm --filter @ai-vastu/web dev
```

## Phase 15 — Production MVP release gate

Phase 15 adds a deterministic, fail-closed public-MVP release-readiness report. The
engineering CI gate verifies that the readiness mechanism is stable; the separate
`pnpm mvp:release` promotion command exits non-zero while blockers remain.

The current repository is intentionally **BLOCKED** for public production release.
The principal blockers are the still-DRAFT/empty Vastu Specification v1, missing
project authorization, absence of the planned production persistence adapter, and
missing end-to-end generation/API/editor wiring. This is a truthful release gate,
not a claim that those capabilities already exist.


## Phase 16 — Deterministic architectural generation API

Phase 16 exposes constraint compilation, CP-SAT planning, canonical architectural
geometry and independent validation through `POST /generation/architectural`.
It removes the generation-API production blocker without inventing Vastu doctrine;
Vastu Specification v1 remains DRAFT and therefore production promotion remains blocked.

# Phase 17 — Web/API project workflow

Phase 17 binds the Next.js editor surface to the existing FastAPI project and generation
contracts without moving authoritative geometry into browser pixels.

Implemented workflow:

- create a project with an explicit project UUID;
- load the current immutable project revision;
- save the current canonical PlanDocument as a new immutable revision using optimistic
  parent-revision concurrency;
- submit a complete explicit `ArchitecturalGenerationRequest` to the deterministic
  Phase 16 generation API;
- local browser-to-API CORS configuration via `AI_VASTU_WEB_ORIGINS`;
- browser API base URL via `NEXT_PUBLIC_AI_VASTU_API_BASE_URL`.

The editor still stages exact edit commands separately. Phase 17 does not silently apply
staged commands to canonical geometry and does not invent generation inputs. Those
boundaries remain explicit.

# Phase 18 — PostgreSQL/Supabase production persistence

Phase 18 removes `PRODUCTION_PERSISTENCE_NOT_IMPLEMENTED` without changing canonical geometry,
solver behavior, Vastu doctrine, or project revision semantics.

## Adds

- Psycopg 3 production PostgreSQL adapter with connection pooling.
- Supabase-compatible prepared-statement configuration.
- PostgreSQL migration for projects + immutable revisions.
- Transactional `FOR UPDATE` project-head concurrency control.
- Environment-driven repository factory.
- Fail-closed production/staging startup without `AI_VASTU_DATABASE_URL`.
- FastAPI repository lifetime ownership.
- Deterministic persistence gate and policy tests.

## Release-gate delta

Phase 17 blockers: 5.

Phase 18 blockers: 4.

Removed only:

- `PRODUCTION_PERSISTENCE_NOT_IMPLEMENTED`

Remaining:

- `VASTU_SPEC_NOT_FROZEN`
- `VASTU_RULESET_EMPTY`
- `VASTU_RULE_BUNDLE_NOT_PINNED`
- `AUTHORIZATION_NOT_IMPLEMENTED`


# Phase 19 — Authentication, authorization, and first dashboard

Phase 19 removes the authorization release blocker. Production identity uses Supabase Auth
with asymmetric JWKS verification at the FastAPI boundary. Project ownership is persisted
separately from canonical PlanDocument content, and all project/revision APIs enforce owner
isolation.

The Next.js root route is now the first real product dashboard with sign-in, project listing,
project creation, revision status, and navigation to the deterministic editor at `/editor`.
The dashboard supplies identity; it is never the authorization authority.

Phase 19 leaves exactly three release blockers, all belonging to Vastu Specification v1:

- `VASTU_SPEC_NOT_FROZEN`
- `VASTU_RULESET_EMPTY`
- `VASTU_RULE_BUNDLE_NOT_PINNED`

# Phase 27 — Final V1 Release Qualification

Phase 27 is the final V1 completion gate built on the validated Phase 26 OpenRouter
checkpoint `40127c3` / `phase26-openrouter-validated`.

It does not replace or weaken any authoritative subsystem.

## V1 authority boundaries

- OpenRouter models interpret requirements, recognize uploaded plans, propose
  architectural intent/topology, and interpret revisions.
- AI output is non-authoritative for exact CAD geometry.
- OR-Tools / deterministic generation remains the exact geometry authority.
- Hard validation must pass before a candidate can be selected.
- The frozen production Vastu v1 bundle remains the Vastu runtime authority.
- Project persistence remains append-only / immutable revision based.
- Billing success is recorded only after durable selected-revision persistence.
- Supabase authentication and server-side ownership checks remain authoritative.
- PDF/JPG/DXF outputs remain presentation/export artifacts derived from canonical
  PlanDocument geometry.
- Production DWG remains dependent on a separately installed, qualified backend.
- Structural engineering and multi-floor generation remain V2 scope and are not
  silently claimed by V1.

## Added by Phase 27

- one whole-product offline release contract check;
- one fail-closed live release qualification command;
- final V1 launch runbook;
- repository validation integration.

## Commands

Offline repository qualification:

```powershell
pnpm phase27:check
pnpm validate
```

Live launch qualification after loading real production secrets:

```powershell
pnpm phase27:live
```

`phase27:live` requires the six OpenRouter provider switches to be explicitly set
to `openrouter`, requires `OPENROUTER_API_KEY`, runs the existing live OpenRouter
qualification, and then runs the existing Phase 25 production-launch gate.

No secret is written to disk by Phase 27.
