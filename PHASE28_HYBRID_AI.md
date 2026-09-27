# Phase 28 â€” Hybrid AI Development Qualification

Phase 28 records the live-qualified zero-cost development AI profile on top of the validated Phase 27 V1 codebase.

## Development providers

Text and architectural reasoning:

- provider: OpenRouter
- model: `deepseek/deepseek-v4-flash-0731:free`
- Phase 26 legacy free fallback remains pinned to `nvidia/nemotron-3-ultra-550b-a55b:free`
- Phase 28 does not qualify or depend on that fallback; it qualifies the DeepSeek primary directly
- no random routing

Existing-plan recognition:

- provider: Google Gemini API directly
- model: `gemini-3.1-flash-lite`
- credential: `GEMINI_API_KEY`
- the persisted Analyze Plan route uses direct Gemini

The retained `/requirements/interpret` compatibility path is separate from
persisted Analyze Plan. When a requirements request includes an image or PDF,
that path uses the pinned OpenRouter vision model. Phase 29C keeps that behavior
for compatibility; whether visual requirements should remain on OpenRouter is a
launch decision that is not resolved by the hybrid profile.

## Responsibilities

DeepSeek handles requirements interpretation, architectural reasoning, soft-Vastu reasoning, Architectural Brain intent/topology and natural-language revisions.

Gemini handles JPG, PNG and PDF existing-plan recognition for persisted Analyze
Plan as non-authoritative observations. OpenRouter continues to handle visual
requirements attachments on the compatibility route described above.

## Authority

AI output never becomes authoritative CAD geometry. Plan-recognition observations preserve uncertainty and require confirmation where appropriate. Exact integer-mm geometry, deterministic solving, hard validation and canonical PlanDocument generation remain application authority.

## Validation

Offline:

```powershell
pnpm phase28:check
pnpm phase29c:check
pnpm validate
```

Live development provider qualification:

```powershell
pnpm phase28:live
pnpm phase29c:live
```

The live commands require explicit credentials and make provider calls with
synthetic inputs. They report provider status without printing credentials,
prompts, uploaded bytes or raw provider response bodies. Provider attempt
counts are code-owned; operators configure only the bounded per-attempt, total,
retry-delay and Retry-After timing budgets shown in the environment template.
