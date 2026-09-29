---
name: vastudraw-fixtures
description: Create deterministic, realistic, reusable fixtures for Vastudraw planning, authentication, persistence, providers, payments, uploads, and regressions.
---
# Vastudraw Fixtures

Use before broad QA for solver, provider, auth, persistence or payment changes.

Read `docs/agent-system/fixture-strategy.md`.

Build:
- happy path
- boundary
- invalid
- provider failure
- auth ownership failure
- retry/replay/idempotency
- regression case

Fixtures must be deterministic, minimal, realistic, reusable and secret-free.
