# ADR-032 — Diversity-aware alternative selection

## Status
Accepted for Phase 10.

## Decision
Alternative selection is deterministic and post-scoring. Exact duplicate placement signatures are
removed first. Remaining candidates are considered in stable rank order and accepted only when they
change at least the configured number of rooms by at least the configured integer-mm threshold relative
to every already-selected alternative.

The diversity thresholds are mandatory caller input. Phase 10 defines no hidden default.

## Consequences
- alternative cards are materially different rather than duplicate solver outputs;
- diversity remains measurable and testable;
- candidate generation stays decoupled from ranking/selection;
- later solver enumeration strategies can feed the same scoring contract without changing selection
  semantics.
