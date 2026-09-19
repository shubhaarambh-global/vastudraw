---
name: vastudraw-phase-gate
description: >-
  Use when implementing, completing, validating, or handing off any Vastudraw
  development phase or milestone. Enforces inspect-first work, targeted tests,
  affected regression suites, Ruff, mypy, full-suite baseline comparison, and
  CURRENT_HANDOFF.md updates. Do not use for trivial read-only questions.
---

# Vastudraw Phase Gate

Use this skill whenever a task is framed as a phase, stage, milestone,
implementation checkpoint, or substantial cross-cutting change.

## Required workflow

Before editing:

1. Read `AGENTS.md`.
2. Read `docs/CURRENT_HANDOFF.md`.
3. Run `git status --short`.
4. Inspect the exact subsystem being changed.
5. Inspect nearby tests before designing the patch.
6. Preserve unrelated working-tree changes.

During implementation:

1. Make the smallest coherent architectural change.
2. Add regression tests for the behavior being introduced.
3. Run the narrowest relevant tests first.
4. Fix the first meaningful failure.
5. Rerun until targeted tests are green.
6. Run affected integration suites.
7. Run Ruff.
8. Run mypy.
9. Run frontend/type/build checks only when affected.
10. Run the broad/full validation gate when the phase requires it.

Do not:
- declare success because code compiles;
- weaken legitimate regression tests;
- skip validation because a change looks small;
- hide new failures among known baseline failures;
- rewrite working subsystems unnecessarily.

## Baseline comparison

When a full repository suite has known pre-existing failures:

- read the current baseline from `docs/CURRENT_HANDOFF.md`;
- record exact current failures;
- compare current failures with the baseline;
- treat any new failure as a regression until proven otherwise;
- do not call the entire repository green if known failures still remain;
- distinguish "phase affected gate green" from "full repository green".

## Completion report

Before declaring a phase complete, update:

`docs/CURRENT_HANDOFF.md`

Record:

- phase/status;
- implementation summary;
- architectural decisions;
- files changed;
- tests added;
- exact validation commands;
- exact pass/fail counts;
- known baseline failures;
- new limitations;
- git status;
- next phase;
- first recommended action for the next agent.

A phase is complete only when the affected implementation and regression
surface are green and no unexplained new failures remain.
