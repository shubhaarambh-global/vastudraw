# Phase 29C/29E separately configured NVIDIA NIM hosted runtime

Status: **SEPARATE PARTIAL LIVE EVIDENCE; NOT QUALIFIED; PRODUCTION ENTITLEMENT
BLOCKED_HUMAN_ACTION**

## Scope

- Keep a separately configured hosted staging/production-shaped `nvidia_nim`
  profile for
  requirements, architecture, soft-Vastu reasoning, Architectural Brain,
  revisions, and plan recognition.
- Use only `https://integrate.api.nvidia.com/v1` and `NVIDIA_API_KEY`.
- Retain OpenRouter/Gemini adapters as legacy/inactive regression surfaces.
- Add deterministic local PDF page rendering and send only rendered images to
  the NVIDIA vision model.
- Keep production entitlement separately `BLOCKED_HUMAN_ACTION`.
- Keep `ollama_local` as the qualified local-development default. NVIDIA
  staging/production settings never silently fall back to Ollama or APINEX.

Non-goals: geometry/solver, frozen Vastu, canonical PlanDocument, revisions,
auth/ownership, billing/payments, Supabase, exports, deployment, backup, restore,
or CORS changes.

## Official NVIDIA Catalog verification (2026-10-01)

The public hosted model list at `https://integrate.api.nvidia.com/v1/models`
contained all three exact IDs. Current NVIDIA model cards:

- `https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b.md`
  - exact ID `nvidia/nemotron-3.5-lightning-30b-a3b`;
  - hosted chat-completions endpoint available;
  - text input, text output, 1,048,576-token context;
  - structured output and reasoning supported; trained for tool use.
- `https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b.md`
  - exact ID `nvidia/nemotron-3-ultra-550b-a55b`;
  - hosted chat-completions endpoint available;
  - text input, text output, 1,048,576-token context;
  - structured output not supported; reasoning and tool calling supported.
- `https://build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning.md`
  - exact ID `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`;
  - hosted chat-completions endpoint available;
  - image/text input (also audio/video), text output, 262,144-token context;
  - JSON output, reasoning, and tool calling supported; structured output not
    supported;
  - hosted API accepts images, not raw PDF; NVIDIA documents page-by-page local
    PDF rendering.

Catalog availability is not application compatibility and is not a production
entitlement claim.

## Protected invariants and guardian constraints

- AI stays advisory. App-owned identity always overwrites provider output.
- Every AI-derived requirements proposal and visual plan observation is forced
  confirmation-required; provider claims of `USER_CONFIRMED` are downgraded.
- Deterministic geometry/validators, frozen Vastu, canonical millimetres,
  revision ancestry, ownership, payments, and soft wet-stack remain unchanged.
- NVIDIA base URL is exact-pinned to prevent credential exfiltration.
- Ultra is the sole active text model; no cross-model fallback exists. One
  same-model retry is limited to unavailable/timeout within the total deadline.
- No Ollama, APINEX, OpenRouter, or Gemini credential or endpoint is reachable
  from the NVIDIA production profile.
- PDF rendering has strict page, pixel, dimension, encoded-byte, and timeout
  bounds; raw PDF bytes are never sent to NVIDIA.
- `NVIDIA_NIM_PRODUCTION_ENTITLEMENT = BLOCKED_HUMAN_ACTION` even if hosted
  trial/dev qualification passes.

## Execution sequence

1. Add the bounded NVIDIA HTTP/model-policy client and adversarial tests.
2. Add thin application-schema adapters and `nvidia_nim` factory branches.
3. Add bounded local PDF rendering and NVIDIA plan recognition.
4. Keep production settings, the hosted environment example, Phase 29E
   preflight, and evidence template explicitly NVIDIA-only.
5. Replace Phase 29C offline/live gates; prove no legacy-provider egress.
6. Run focused tests, Ruff, mypy, affected Phase 29C/29E gates, diff check, and
   broader relevant suites.
7. If `NVIDIA_API_KEY` becomes visible to an authorized human-run shell, run the
   canonical real-schema Ultra, PNG, JPEG, and PDF-path qualification sequence.
8. Run independent regression/adversarial/QA review, then update handoff and
   durable memory with verified facts only.

## Live stop conditions

- Missing credential: `BLOCKED_CREDENTIALS`, never request it in chat.
- Lightning schema/advisory failure: do not pin via model-specific hacks;
  research one current hosted NVIDIA text model before selection.
- Vision schema/image incompatibility: fail closed; do not reactivate legacy
  providers.
- Hosted development success never clears the production-entitlement gate.
