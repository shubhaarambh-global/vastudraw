# Vastudraw Agent Memory / Knowledge Graph

`knowledge-graph.json` is durable repository memory for Codex.

It is intentionally small. It stores facts that future agents should not have to rediscover.

## Node types
- baseline
- branch
- contract
- provider
- payment
- architecture_decision
- qualification
- known_risk
- command
- subsystem

## Required node properties
- `id`
- `type`
- `title`
- `status`
- `provenance`

Optional:
- `value`
- `notes`

## Edge
- `from`
- `rel`
- `to`

## Rules
Only write verified durable facts.
Every fact must have provenance.
Do not store secrets, transient logs, speculative conclusions or private user data.

Use `python scripts/agent_memory.py validate` before committing memory changes.
Use `python scripts/agent_memory.py query <term>` to search titles/values/status/provenance.
