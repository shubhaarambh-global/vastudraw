---
name: vastudraw-orchestrator
description: Coordinate substantial Vastudraw development across planners, workers, testing, QA, security review, architecture review, and release review.
---
# Vastudraw Orchestrator

Use for substantial multi-step work.

1. Read root AGENTS.md.
2. Query relevant memory graph terms.
3. Read protected contracts.
4. For complex tasks, delegate two independent planning passes.
5. Ask Architecture Guardian to challenge the plans.
6. Synthesize one execution plan.
7. Delegate only independent/disjoint implementation work in parallel.
8. Run Fixture Engineer before broad QA for risky behavior.
9. Run Regression Tester and Adversarial Tester independently.
10. Send findings through a fix loop until material issues are resolved.
11. Run full qualification.
12. Update durable memory only after verification.

The coordinator owns Git and final qualification claims.
Do not ask subagents for private chain-of-thought; request concise findings, rationale and evidence.
