# Protected Vastudraw Contracts

## Qualified references
Frozen V1:
- tag `phase2d9k-v1-qualified`
- commit `17bd86da29c50c8f73b8a47f5a4c186cf2bd7c26`

Qualified post-V1:
- tag `post-v1-development-qualified`
- commit `cbd295f5e9028186acbfb14f40c1142e3a003b27`

## Authority order
1. canonical/domain safety
2. deterministic geometry and feasibility
3. confirmed user requirements
4. frozen Vastu rules where applicable
5. architectural-brain topology/preferences
6. precedent/heuristic intent
7. presentation/UI hints

Lower authority must not silently override higher authority.

## Planning
- AI is not authoritative geometry.
- AI maximum areas remain preferences unless another authoritative rule defines a hard cap.
- Wet-stack coordination remains soft.
- Compact sites must not fail merely because AI concepts prefer larger rooms.
- Canonical storage uses integer millimetres.
- Deterministic repeatability must be preserved.

## Vastu
Do not change frozen production Vastu semantics without explicit expert-review workflow and regression evidence.

## Project/revisions
- immutable revision semantics
- correct ancestry
- ownership isolation
- deterministic hashes
- export tied to the exact canonical revision

## Product scope
Structural engineering is not a V1 capability.

## Production
- PostgreSQL only in production
- no dev billing bypass in production
- explicit CORS/trusted hosts
- secrets remain server-side
- payment/entitlement is server-authoritative
