# ADR-006 — Solver resolution

Status: Accepted for current architecture baseline

## Context

AI Vastu Architect requires deterministic, reproducible, CAD-grade architectural geometry and source-backed Vastu evaluation.

## Decision

Canonical storage remains 1 mm while solver search granularity may be coarser and explicitly recorded, followed by deterministic exact-mm refinement/validation.

## Consequences

This decision is treated as frozen until superseded by a later ADR with explicit migration impact and test coverage.
