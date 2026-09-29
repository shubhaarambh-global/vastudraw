# Orchestration Protocol

## Stage -1 — Model routing
Before delegation, Model Router assigns roles, sequencing/parallelism, context,
skills, tests, reviewers, and human-review conditions. Every role uses GPT-5.6
Sol Medium. Model or reasoning-effort changes require explicit user approval;
temporary unavailability means pause and retry, not silent substitution.


## Stage 0 — Memory retrieval
Coordinator reads:
- root `AGENTS.md`
- protected contracts
- relevant knowledge-graph nodes/edges
- current handoff/spec
- current Git state

## Stage 1 — Plan tournament
For complex work, spawn two independent planner subagents with the same task but bounded output.

Each planner returns:
- scope
- files likely affected
- invariants
- risks
- proposed sequence
- validation matrix
- unknowns

Do not ask for hidden chain-of-thought. Require concise rationale and evidence.

## Stage 2 — Guardian challenge
Architecture Guardian challenges both plans:
- protected-contract conflicts
- authority inversion
- unsafe migrations
- live-service risk
- unnecessary rewrites

## Stage 3 — Coordinator synthesis
Coordinator chooses/synthesizes one execution plan and records it in `docs/exec-plans/active/` when the task is large.

## Stage 4 — Implementation
Parallel implementation is allowed only when file ownership is disjoint or agents use isolated worktrees.

Recommended roles:
- backend worker
- frontend worker
- integration worker

No two agents should casually edit the same mutable file.

## Stage 5 — Fixtures
Fixture Engineer creates realistic positive, boundary and failure cases before broad QA.

## Stage 6 — Independent testing
Run two independent test perspectives when risk is high:
- Regression Tester: proves intended behavior and no known regression.
- Adversarial Tester: searches for bypasses, malformed inputs, race/idempotency issues and edge cases.

## Stage 7 — QA challenge
QA Reviewer reviews:
- diff
- tests
- logs/build results
- product behavior
- release claims

QA should try to reject the change, not merely confirm it.

## Stage 8 — Fix loop
Coordinator sends concrete QA findings back to implementation worker(s), reruns focused tests, then full gates.

Repeat until no material unresolved findings remain.

## Stage 9 — Release evidence
Release agent records:
- exact HEAD
- commands
- counts
- live services actually exercised
- blocked checks
- migration/deployment actions
- rollback point

## Stage 10 — Memory update
Memory Curator writes only durable facts to the knowledge graph:
- qualified baselines
- architecture decisions
- stable provider/gateway choices
- discovered invariants
- recurring failure modes
- verified commands/gates

Never store secrets or transient noise.
