# Phase 26 OpenRouter — Free-Only Provider Stack

Baseline: validated Phase 26 commit `88a37827e9a849ecc8205ed54970551b1a3714df`.

## Pinned runtime models

- Primary Architectural Brain: `deepseek/deepseek-v4-flash-0731:free`
- Vision architectural-plan reader: `inclusionai/ling-3.0-flash-vl:free`
- Fallback reasoning: `nvidia/nemotron-3-ultra-550b-a55b:free`

The runtime accepts only these explicit `:free` model IDs. It never uses
`openrouter/free`, provider-selected model substitution, or a paid fallback.

## Provider roles

OpenRouter can serve:
- requirements interpretation;
- Phase 26A architectural design intent;
- Phase 26B contextual soft-Vastu reasoning;
- Phase 26 Architectural Brain topology and room-sizing concepts;
- Phase 26B.5 plan/image/PDF recognition;
- Phase 26D natural-language revision interpretation.

The exact CAD authority is unchanged:

OpenRouter reasoning -> structured intent -> deterministic constraints ->
OR-Tools planning -> canonical integer-mm geometry -> hard validation.

AI output never becomes authoritative PlanDocument geometry directly.

## Architectural Brain correction

The previous provider call received room types and retrieved precedents but did
not receive all already-confirmed site facts. This overlay forwards:
- exact confirmed plot width/depth;
- bedroom/toilet/parking counts;
- road side;
- entrance side;
- room program;
- retrieved licensed precedent fingerprints.

The model is explicitly instructed to account for the full valuable site while
not assuming that all land may legally be roofed. Regulation/setback rules remain
a separate hard-rule layer.

## Vision and PDF handling

JPG/PNG plan references are sent to the pinned Ling vision model.

PDFs use OpenRouter file input with the PDF parser explicitly pinned to
`cloudflare-ai`. The application does not permit an unspecified/default paid OCR
fallback. A scanned/image-only PDF may therefore be less visually reliable than
an exported JPG/PNG sheet; the recognition result remains non-authoritative and
requires user confirmation.

DXF/DWG handling retains the existing deterministic CAD summary/conversion path.

## Structured output

The free model routes are not trusted to enforce the application's JSON schema.
Every prompt carries the schema, then application code:
1. extracts one JSON object;
2. validates it with existing Pydantic contracts;
3. restores application-owned identity fields;
4. falls back only to the pinned free reasoning model when appropriate.

Invalid JSON is treated as provider failure, never as trusted geometry.

## Configuration

Load `OPENROUTER_API_KEY` securely at runtime. Do not commit it.

Recommended live stack:

```text
AI_VASTU_REQUIREMENTS_PROVIDER=openrouter
AI_VASTU_ARCHITECT_PROVIDER=openrouter
AI_VASTU_VASTU_PROVIDER=openrouter
AI_VASTU_PLAN_RECOGNITION_PROVIDER=openrouter
AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER=openrouter
AI_VASTU_REVISION_PROVIDER=openrouter
```

The three model environment variables are pinned and validated against the
free-only allowlist.

## Validation

Static/offline:

```text
pnpm phase26:openrouter-check
pnpm validate
```

Live provider qualification, after loading the API key securely:

```text
pnpm phase26:openrouter-live
```

The live check calls the primary reasoning model, fallback reasoning model, and
vision model separately. It is intentionally excluded from ordinary offline CI.
