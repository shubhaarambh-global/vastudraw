# Phase 26B — Soft Vastu Reasoning

Phase 26B adds a source-backed, contextual Vastu reasoning layer without
turning Vastu into hard geometry.

## Core policy

- Architectural validity is mandatory.
- Vastu is advisory/optimization input.
- Ordinary Vastu rules never make a geometrically valid plan invalid.
- Rules may be negligible, low, moderate, high, or core.
- Rules may be flexible, preferred, strongly preferred, or traditionally fixed.
- "Traditionally fixed" means the reasoning model may not downgrade that rule
  inside Vastu interpretation. It does NOT mean a hard solver constraint.
- Source disagreement is retained and surfaced.
- The reasoning model may contextualize only catalogued rules. It may not
  invent rule IDs or directional rules.

## Influence modes

- Practical: architecture 70%, Vastu 30%.
- Balanced: architecture 50%, Vastu 50%.
- Vastu-forward: architecture 30%, Vastu 70%.

Legacy mapping:
- space_efficient → practical
- balanced → balanced
- strict → vastu_forward
- custom → balanced unless `AI_VASTU_VASTU_INFLUENCE_MODE` is explicitly set.

## Separation from the frozen V1 bundle

The existing four human-reviewed Phase 20 Vastu rules and their frozen
production bundle/hash are untouched. The Phase 26B catalog is deliberately a
`spec-v2-draft` soft-policy knowledge base.

The canonical PlanDocument continues to contain the existing frozen V1
VastuAnalysis. Phase 26B adds a richer contextual assessment to the confirmed
generation API response. Schema migration can happen only after the new policy
is reviewed.

## What is scored now

Room-centroid directional rules with geometry that the canonical document can
deterministically prove.

Unsupported concepts (for example exact Brahmasthan openness or entrance
semantics) are reported as NOT_EVALUATED rather than guessed.

## Phase 26C handoff

Phase 26B calculates the architecture/Vastu blend for one valid plan, but
`ranking_ready=false`. Phase 26C will generate multiple valid candidates and
rank them using exactly this policy. That is where 30/50/70 Vastu influence
begins affecting which geometry is selected.
