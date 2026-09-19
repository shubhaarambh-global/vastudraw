---
name: vastudraw-regression-baseline
description: >-
  Use whenever running broad/full Vastudraw validation, interpreting failing
  tests, release-readiness checks, or deciding whether a phase is green.
  Compares failures with the documented baseline in CURRENT_HANDOFF.md and
  prevents new regressions from being mislabeled as pre-existing.
---

# Vastudraw Regression Baseline

This repository may intentionally have a documented set of unrelated
pre-existing failures while a backend generation phase is otherwise green.

Never reason from failure count alone.

## Source of truth

Read:

`docs/CURRENT_HANDOFF.md`

before broad/full-suite validation.

The handoff must contain the latest reproduced baseline.

Do not rely on an old prompt or remembered count when the repository has a
newer reproduced baseline.

## Validation procedure

When the full suite fails:

1. Capture every failing test identifier.
2. Capture the first meaningful failure reason for each category.
3. Compare identifiers/categories with the documented baseline.
4. Classify each failure as:
   - known baseline;
   - changed baseline;
   - new regression;
   - unresolved/needs investigation.
5. Investigate all new or changed failures.
6. Do not finish the phase until phase-caused regressions are fixed.

## Reporting language

Use precise status distinctions.

Acceptable:

- "2D9G affected backend gate: GREEN"
- "Ruff: PASS"
- "mypy: PASS"
- "Full repository suite: 13 known baseline failures, no new failures"

Do not say:

- "everything passes"
- "full repository green"

while baseline failures still exist.

## Baseline changes

If the number of failing tests changes:

- compare exact test names;
- do not assume an increase is a regression;
- do not assume the same count means the same failures.

For example, one category can contain multiple distinct failing tests.

Update the handoff with the exact reproduced baseline after validation.

## Scope control

Do not repair unrelated baseline failures during a focused generation phase
unless:

- they were caused by the phase;
- they block validation of the phase;
- the user explicitly asks to resolve the baseline.

This prevents unrelated UI/schema/release-policy work from contaminating
generator milestones.
