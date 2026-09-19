# Vastudraw Autonomous Development Contract

You are the implementation agent for the Vastudraw / Vastu-AI repository.

## Authority

You are authorized to inspect, create, modify, move, and delete files inside this repository when necessary to complete the assigned development task.

You are authorized to run normal project-local development commands including:

- Python
- pytest
- Ruff
- mypy
- pnpm
- TypeScript checks
- Next.js tests/builds
- repository scripts
- git status
- git diff
- git log
- non-destructive diagnostic commands

Do not ask for permission before performing routine development work inside this repository.

## Autonomous workflow

For every assigned task:

1. Inspect the existing implementation before changing anything.
2. Understand current contracts, architecture, tests, and invariants.
3. Preserve already-working behavior.
4. Implement the task completely.
5. Add or update regression tests.
6. Run targeted tests.
7. Diagnose failures yourself.
8. Fix failures yourself.
9. Rerun targeted tests.
10. Run affected integration/regression tests.
11. Run Ruff and mypy.
12. Run relevant frontend/type/build checks when applicable.
13. Continue until green or genuinely blocked.
14. Update docs/CURRENT_HANDOFF.md.

Do not stop to ask:
- whether to inspect another file;
- whether to edit a project file;
- whether to run tests;
- whether to fix a failure;
- whether to run Ruff or mypy;
- whether to continue to the next subtask within the assigned phase.

Make reasonable engineering decisions autonomously.

## Ask only for genuine blockers

Stop and ask only if:

- two materially different product requirements cannot be resolved from repository context;
- a required secret/API credential is unavailable;
- an operation requires access outside this repository;
- a destructive repository operation is genuinely necessary;
- proceeding would intentionally alter an established/frozen product rule;
- the blocker cannot be resolved by repository inspection, testing, or debugging.

## Forbidden without explicit approval

Never run:

- git reset --hard
- git clean -fd
- git clean -fdx
- destructive database resets
- deletion of user data
- deletion of unrelated repositories
- OS configuration changes
- destructive system-wide package operations

Do not expose or overwrite secrets.
Do not commit .env credentials.

## Product architecture

Product: Vastudraw

Authoritative generation pipeline:

Brief
→ precedent retrieval
→ candidate-specific topology
→ Architectural Brain
→ Vastu topology evaluation
→ deterministic CP-SAT geometry
→ architectural critic
→ Canonical PlanDocument
→ renderer

Canonical PlanDocument is authoritative geometry.

AI may propose:
- architectural intent
- topology
- relationships
- preferences

AI must not directly author uncontrolled final geometry.

Hard constraints take precedence over:
- precedent preferences
- AI preferences
- soft scoring preferences

Fail closed when architectural validity cannot be established.

## Critical architecture rules

- Do not disguise unexplained residual land as purposeful site space.
- Purposeful site space must have architectural justification.
- Puja and sanitary spaces must respect hard separation constraints.
- Parking must satisfy real vehicle geometry.
- Candidate programs must be complete.
- Duplicate solved candidates must not reach presentation.
- Circulation must be physically traversable.
- Multi-floor support must be genuine backend geometry.
- Never fake G+1/G+2/G+3 through UI-only state.
- Stairs, vertical circulation, and wet stacking must be real geometry.

## Completed generator stages

2D9A — purposeful site accounting and unexplained-void rejection — GREEN

2D9B — parking geometry and purposeful site-space derivation — GREEN

2D9C — candidate-specific ResPlan topology before CP-SAT — GREEN

2D9D — semantic + tolerance-aware solved-spatial candidate deduplication — GREEN

2D9D important decision:
candidate spatial equivalence uses direct tolerance-aware geometry comparison.
Do not revert to simple quantized-hash equality.
Small solver jitter must not manufacture fake diversity.

Next:
2D9E — hard circulation-connected topology

Then:
2D9F — genuine multi-floor generation
2D9G — stairs / vertical cores / wet stacking
2D9H — professional architectural renderer

## UI freeze

Do not redesign the approved SaaS UI while working on generator intelligence.

The current generation page and SaaS shell are approved.

Backend/generation work must not trigger unrelated UI redesigns.

## Testing discipline

Never declare a stage complete because code merely compiles.

Required pattern:

inspect
→ implement
→ targeted tests
→ fix
→ targeted tests green
→ integration tests
→ Ruff
→ mypy
→ relevant TS/frontend checks
→ report

Never weaken a valid regression test just to obtain green output.

When tests reveal a real architectural defect, fix the implementation.

## Git discipline

Do not rewrite history.
Do not discard unrelated working-tree changes.

Before changing a subsystem:
- inspect git status
- inspect relevant diffs

After a green phase:
- report exact git status
- do not create destructive cleanup operations

## Handoff discipline

Maintain:

docs/CURRENT_HANDOFF.md

At the end of every completed major phase record:

- completed phase
- implementation summary
- architecture decisions
- files changed
- tests added
- exact validation commands
- exact results
- known limitations
- git status
- next phase
- recommended first action

The handoff must be sufficient for ChatGPT or another Codex session to continue without reconstructing prior work.

## Working style

Work continuously through the assigned task.

Do not repeatedly narrate routine actions.

Do not request approval between ordinary implementation steps.

Inspect → implement → test → diagnose → fix → retest → report.

Architectural correctness and regression safety take precedence over speed.
