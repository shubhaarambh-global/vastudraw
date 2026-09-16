# ADR-031 — Deterministic architectural scoring

## Status
Accepted for Phase 10.

## Decision
Phase 10 scores only explicit, compiled soft constraints for which the repository has a measurable
architectural fact. Scores are integer basis points. Phase 9 validity is a prerequisite, not a score
component that can be traded against preference satisfaction.

The initial measurable objectives are preferred dimensions, preferred area, preferred floor, and
adjacency. Privacy/daylight/ventilation priority records remain preserved but unscored until later
phases provide authoritative measurable facts. Unweighted adjacency avoidance is also unscored;
Phase 10 will not fabricate a missing weight.

## Consequences
- no invalid candidate can rank highly enough to become acceptable;
- scores are reproducible and explainable from objective-level evidence;
- the system can add future measurable components without changing historical score semantics;
- no Vastu score exists until frozen source-backed Vastu rules are available.
