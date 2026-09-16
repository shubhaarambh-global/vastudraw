# ADR-012 — Generation reproducibility

Status: Accepted for current architecture baseline

## Context

AI Vastu Architect requires deterministic, reproducible, CAD-grade architectural geometry and source-backed Vastu evaluation.

## Decision

Each generation records schema/rule/solver versions, parameters, input hash, assumptions, and seed so accepted plans can be reproduced.

## Consequences

This decision is treated as frozen until superseded by a later ADR with explicit migration impact and test coverage.
