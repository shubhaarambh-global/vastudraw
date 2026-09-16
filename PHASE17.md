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
