# Phase 24 Final — Canonical Generation Commit

This closes roadmap Phase 24 after validation.

Flow:

ConfirmedRequirements
→ project ownership
→ Phase 23 entitlement authorization
→ deterministic Phase 16 architectural generation
→ frozen Vastu v1 runtime evaluation
→ deterministic architectural scoring
→ canonical PlanDocument
→ immutable project revision commit
→ successful-generation billing transition
→ Editor handoff

## Authority boundaries

- AI interprets client material only.
- The existing deterministic generation pipeline remains geometry authority.
- The committed Phase 20B `production/rule-bundle.json` is Vastu authority.
- Existing scoring code remains architectural scoring authority.
- Existing project repository/service remains revision authority.
- Phase 23 billing remains entitlement authority.
- The free generation is recorded only after a durable revision exists.

## MVP scope guard

The inspected Phase 16 generator creates one floor. Phase 24 therefore rejects
`floor_count != 1` and any explicit upper-floor room preference instead of
silently dropping upper floors.

## Frozen Vastu v1

Expected production RuleBundle hash:

`b11b66be61d6436fcaa43c1c5b743c0090051154146d91caf904eb5108546667`

Phase 24 reads the committed production bundle directly and fails closed if its
hash, production flag, supported geometry semantic, or spec version differs.
