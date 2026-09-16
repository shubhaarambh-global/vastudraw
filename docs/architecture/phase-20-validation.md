# Phase 20 validation

Phase 20A is valid when:

- the specification loads deterministically;
- lifecycle is `IN_REVIEW`;
- exactly four candidate rules are present;
- all source references resolve;
- all rules are `REVIEWED` and `SOFT`;
- all review records are `SOURCE_VERIFIED` with `source_validation_passed=true`;
- no candidate contains an approval/rejection attestation;
- geometry semantics remain explicitly unapproved;
- deterministic review packets match the typed authoring records;
- the production MVP remains blocked by exactly the three Vastu gates.

Phase 20B has a separate future gate and must not be declared complete from Phase 20A validation.
