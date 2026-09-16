# Phase 24A — Multimodal Requirements Interpretation + Human Confirmation

Phase 24 is intentionally split internally into 24A and 24B.

24A establishes the AI requirements boundary:

client prompt + JPG/PNG/PDF
→ multimodal interpretation
→ typed requirements draft
→ ambiguity/questions
→ human confirmation
→ immutable confirmed requirements

24B will bind confirmed requirements to the exact existing deterministic
generation contract after the repository contract inspection produced by
`scripts/inspect-generation-contract.py`.

This is still one roadmap phase: Phase 24.

## Non-negotiable boundary

The AI never owns authoritative geometry.

AI-extracted dimensions, directions, rooms, labels, or inferred values remain
proposals until a user confirms them. The deterministic plot/constraint/solver
pipeline remains the only owner of generated geometry.

## Providers

`AI_VASTU_REQUIREMENTS_PROVIDER=fixture`
- deterministic parser for tests/local development
- never sends uploads to an external provider

`AI_VASTU_REQUIREMENTS_PROVIDER=openai`
- uses the OpenAI Responses API
- accepts text + JPG/PNG/PDF
- requires Structured Outputs JSON Schema
- sends uploaded references to the configured provider
- requires:
  - `OPENAI_API_KEY`
  - `AI_VASTU_OPENAI_MODEL`

No default live model is guessed. Production fails closed without explicit model
configuration.

## Draft persistence

Development default:
`.local/requirement-drafts`

Production/staging:
`AI_VASTU_REQUIREMENTS_PATH` must be an explicit absolute persistent path.

## MVP interpretation fields

- rectangular plot width/depth
- north rotation
- road side
- entrance-facing preference
- floor count
- bedroom count
- requested room types/quantities
- parking count
- Vastu preference mode
- clarifying questions
- warnings/assumptions

Irregular survey reconstruction remains outside the automatic authority boundary.
