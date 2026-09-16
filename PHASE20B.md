# Phase 20B — Human VASTU_EXPERT approval and production freeze

## Objective

Convert the source-verified Phase 20A candidate set into the first production-frozen Vastu Specification v1.0 **only through an explicit human approval action**.

This phase does not fabricate an expert attestation. The reviewer must execute the approval command with the explicit `I_APPROVE_PHASE20B_V1` confirmation token. That action records a timezone-aware human `VASTU_EXPERT` attestation into each rule record.

## Frozen v1.0 decisions

The approval command attests to all of the following Phase 20A review decisions:

1. the four normalized directional statements are accepted for the v1.0 MVP;
2. the eight-sector direction model is accepted for these four rules;
3. room-centroid classification is accepted for these four rules;
4. kitchen SE is the only encoded primary v1.0 kitchen rule; NW is not silently added as a fallback;
5. the master-bedroom rule remains limited to `master_bedroom` and accepts S/SW;
6. bath and toilet rules remain separate; the v1.0 rule targets only `bath`;
7. all four rules remain `SOFT`, with the Phase 20A weights/severities accepted for the MVP scoring model.

## Deterministic freeze

After approval, the freeze command:

- requires every rule to be `APPROVED` and `FROZEN`;
- compiles the production `RuleBundle` from the typed rules and source registry;
- writes the exact SHA-256 bundle hash into `manifest.json`;
- moves the spec lifecycle to `FROZEN`;
- writes `production/rule-bundle.json` and `production/release.json`;
- regenerates the review packets so the recorded approval is auditable;
- verifies the repository release gate becomes `READY` with zero blockers.

The bundle hash is computed from canonical model content and is never hand-authored.
