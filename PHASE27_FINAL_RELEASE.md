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
