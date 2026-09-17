# Phase 26A — Architectural Intelligence

## Goal

Improve residential plan quality by giving the deterministic solver a structured
architectural program rather than asking an LLM to draw geometry.

## Authority split

LLM/provider:
- functional zoning,
- room relationships,
- privacy/daylight/ventilation priorities,
- explicit furniture/features,
- circulation intent,
- architectural rationale.

Deterministic engine:
- exact placement,
- integer-mm geometry,
- walls/openings,
- containment,
- circulation validation,
- canonical PlanDocument.

## Safety / quality boundary

Phase 26A modifies only soft RoomRequirement preferences and priorities.
It does not change confirmed hard minima, plot geometry, buildable area,
geometry validity, or independent validation.

No ordinary Vastu rule is introduced here. Weighted Vastu is Phase 26B.

## Providers

`AI_VASTU_ARCHITECT_PROVIDER`:
- `disabled` (default/backward compatible)
- `fixture`
- `gemini`
- `openai`

`AI_VASTU_ARCHITECT_MODEL` selects the live reasoning model without code changes.

## Future

- 26B: source-backed soft Vastu knowledge + Practical/Balanced/Vastu-forward weighting.
- 26C: deterministic multi-candidate generation and ranking.
- 26D: natural-language client revisions that regenerate complete alternatives.
