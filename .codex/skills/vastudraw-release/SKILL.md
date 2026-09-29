---
name: vastudraw-release
description: Audit Vastudraw release readiness, exact Git state, validation evidence, live-versus-local qualification, rollback points, and tag claims.
---
# Vastudraw Release

Before a qualification tag:
- verify branch and HEAD
- verify tracked-tree state
- run required focused and full gates
- record exact counts
- record live services actually exercised
- record blocked gates honestly
- record migrations/config actions
- record rollback point
- run `git diff --check`

Never use force push or rewrite qualified tags.
A tag is a claim; do not create it if evidence is incomplete.
