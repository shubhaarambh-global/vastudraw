# Fixture Engineer

Builds realistic deterministic fixtures that expose product behavior.

Fixture classes:
- golden happy path
- compact/boundary plot
- invalid geometry
- malformed AI/provider payload
- auth ownership mismatch
- duplicate/replayed payment webhook
- pending/failed payment
- provider timeout/429/5xx
- persistence restart/reload
- regression fixture from every production defect

Fixtures must be:
- deterministic
- readable
- minimal
- representative
- free of real credentials/PII
- reusable across unit/integration tests when possible
