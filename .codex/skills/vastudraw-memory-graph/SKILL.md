---
name: vastudraw-memory-graph
description: Read, validate, query, and carefully update Vastudraw durable project knowledge with verified facts and provenance.
---
# Vastudraw Memory Graph

Use when starting a large task, resolving project history, or closing a qualified milestone.

Read:
- `docs/agent-memory/README.md`
- `docs/agent-memory/knowledge-graph.json`

Query:
`python scripts/agent_memory.py query <term>`

Validate:
`python scripts/agent_memory.py validate`

On milestone completion, add only durable verified facts with provenance.
Keep the graph compact.
Never store secrets, PII, transient logs or speculation.
