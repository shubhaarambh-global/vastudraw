# Vastu Specification v1.0 production artifacts

This directory is populated by `python scripts/freeze-vastu-spec.py` after explicit human `VASTU_EXPERT` approval.

- `rule-bundle.json` is the deterministic production `RuleBundle`.
- `release.json` binds the frozen authoring state to the production rule-bundle hash and release hash.

Do not hand-edit either generated JSON file. Recompile through the Phase 20B freeze command.
