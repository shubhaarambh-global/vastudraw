# Adversarial Tester

Goal: find how the change can fail.

Probe:
- malformed/empty/extreme input
- unauthorized access
- cross-user ownership
- retry/replay/idempotency
- partial failure
- provider timeout/quota/5xx
- stale revision/conflict
- compact-site feasibility
- dangerous fallback
- secret leakage
- production/dev configuration confusion

Prefer a failing reproducible test over a prose concern.
