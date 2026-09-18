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
- OpenRouter shared vision pools are not used

## Responsibilities

DeepSeek handles requirements interpretation, architectural reasoning, soft-Vastu reasoning, Architectural Brain intent/topology and natural-language revisions.

Gemini handles JPG, PNG and PDF existing-plan recognition as non-authoritative observations.

## Authority

AI output never becomes authoritative CAD geometry. Plan-recognition observations preserve uncertainty and require confirmation where appropriate. Exact integer-mm geometry, deterministic solving, hard validation and canonical PlanDocument generation remain application authority.

## Validation

Offline:

```powershell
pnpm phase28:check
pnpm validate
```

Live development provider qualification:

```powershell
pnpm phase28:live
```

Commercial production may replace the development AI models without changing the deterministic geometry authority.
