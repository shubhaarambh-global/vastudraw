# Vastu Specification v1.0 — candidate rules

Phase 20A contains four source-verified, non-production candidate rules. Each file preserves source locators, normalized wording, implementation interpretation, classification and review state.

A rule can be promoted to production only when:

1. its geometry semantics have been explicitly reviewed;
2. its review record is `APPROVED`;
3. an actual `VASTU_EXPERT` approval attestation is present;
4. the rule lifecycle is promoted to `FROZEN`;
5. the compiled production bundle hash is written into the frozen manifest.

Do not fabricate reviewer identities or attestations.
