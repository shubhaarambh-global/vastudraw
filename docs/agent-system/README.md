# Vastudraw Agent Operating System

This layer improves Codex performance by separating **durable repository knowledge** from **task-specific agent context**.

The system has five parts:

1. **Coordinator** — owns scope, plan, integration and Git.
2. **Specialist subagents** — bounded planning, implementation, fixture, testing, security and QA tasks.
3. **Knowledge graph** — durable, provenance-backed project memory.
4. **Skills** — repeatable workflows loaded only when relevant.
5. **Quality loop** — independent review and evidence before qualification.

Do not create a swarm for every task. Parallelize only independent work. Dependent edits stay under one coordinator.

Recommended concurrency for a large Phase 29 task: 3-4 specialists plus the coordinator.

The quality target is not "more agents." The target is:
- smaller contexts,
- independent challenge,
- less architectural drift,
- stronger fixtures,
- explicit evidence,
- reproducible release claims.
