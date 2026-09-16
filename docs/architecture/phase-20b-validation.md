# Phase 20B validation

Phase 20B is valid only when all of the following are true:

- the human reviewer explicitly executes the approval command with the `I_APPROVE_PHASE20B_V1` token;
- all four rule records are `APPROVED` and contain a real `VASTU_EXPERT` approval attestation;
- all four rules are `FROZEN` and remain `SOFT`;
- source validation and geometry-semantics review are both true;
- the spec lifecycle is `FROZEN`;
- `production_rule_count` is exactly four;
- the production RuleBundle is deterministically compiled and its SHA-256 is pinned in the manifest;
- stored `production/rule-bundle.json` and `production/release.json` exactly match deterministic recompilation;
- review packets match the final approved records;
- the public-MVP readiness report is `READY` with zero blockers;
- `pnpm mvp:release` exits successfully;
- all repository validation gates remain green.
