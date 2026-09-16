# ADR-011 — DWG qualification

Status: Accepted for current architecture baseline

## Context

AI Vastu Architect requires deterministic, reproducible, CAD-grade architectural geometry and source-backed Vastu evaluation.

## Decision

DWG is provided through a pluggable backend only after real round-trip compatibility qualification; renaming DXF is forbidden.

## Consequences

This decision is treated as frozen until superseded by a later ADR with explicit migration impact and test coverage.
