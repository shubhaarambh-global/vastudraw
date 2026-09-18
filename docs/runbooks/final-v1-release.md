# Final V1 Release Runbook

## Required validated baseline

- Git checkpoint: `40127c3`
- Tag: `phase26-openrouter-validated`
- Primary: `deepseek/deepseek-v4-flash-0731:free`
- Vision: `inclusionai/ling-3.0-flash-vl:free`
- Fallback: `nvidia/nemotron-3-ultra-550b-a55b:free`

## 1. Offline release qualification

Run:

```powershell
pnpm phase27:check
pnpm validate
```

The offline gate verifies the product contract without requiring live secrets:
authentication/ownership, PostgreSQL persistence, billing, confirmed-requirements
generation, deterministic candidate generation, canonical PlanDocument revision
persistence, OpenRouter free-only policy, Vastu production bundle, editor/export
surfaces, production hardening, and V1 scope guards.

## 2. Configure production environment

Use the repository's production environment template and your secret manager.
Do not commit keys.

The six AI provider switches must be:

```text
AI_VASTU_REQUIREMENTS_PROVIDER=openrouter
AI_VASTU_ARCHITECT_PROVIDER=openrouter
AI_VASTU_VASTU_PROVIDER=openrouter
AI_VASTU_PLAN_RECOGNITION_PROVIDER=openrouter
AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER=openrouter
AI_VASTU_REVISION_PROVIDER=openrouter
```

The OpenRouter model variables remain pinned to the validated free-only stack.

## 3. Live qualification

With real production Supabase/PostgreSQL/payment/OpenRouter configuration loaded:

```powershell
pnpm phase27:live
```

This command deliberately fails closed. It first qualifies OpenRouter against the
live provider and then executes the existing production launch gate.

## 4. Deployment

Deploy the API and web containers using the repository production examples. Apply
all PostgreSQL/Supabase migrations before traffic is enabled. Use durable encrypted
storage for any configured persistent file stores. Configure TLS, explicit origins,
trusted hosts, provider/edge abuse controls, Supabase Auth rate limiting/CAPTCHA,
backup scheduling, and external monitoring.

## 5. Post-deploy smoke path

Exercise the product with a dedicated test account:

1. Sign in.
2. Create a project.
3. Submit a text brief and generate interpreted requirements.
4. Confirm the structured requirements.
5. Generate alternatives.
6. Select one hard-valid plan.
7. Verify immutable project revision persistence.
8. Open the canonical plan in the editor.
9. Apply a natural-language revision and regenerate.
10. Export PDF/JPG/DXF.
11. Verify billing transition occurs only after successful durable generation.
12. Verify another user cannot read the project.
13. Verify rate limits and security headers.
14. Verify backup/restore on a disposable environment.

## V1 scope

V1 is a single-floor residential architectural planning product. Structural
engineering and true multi-floor generation remain V2. DWG output is production
eligible only when a separately licensed/installed backend passes repository and
external CAD qualification.
