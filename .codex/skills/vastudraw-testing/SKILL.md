---
name: vastudraw-testing
description: Design and run Vastudraw regression and adversarial tests, reproduce defects, protect qualified behavior, and report exact executable evidence.
---
# Vastudraw Testing

Use two independent perspectives for high-risk changes.

Regression Tester:
- expected behavior
- known bug regression
- deterministic behavior
- subsystem gates

Adversarial Tester:
- malformed/extreme inputs
- auth bypass
- cross-user access
- replay/idempotency
- provider failure
- stale revisions
- production/dev confusion
- secret leakage

Prefer reproducible tests over prose findings.
Report exact commands and counts.
