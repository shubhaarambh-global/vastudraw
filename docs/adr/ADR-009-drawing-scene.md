# ADR-009 — DrawingScene abstraction

Status: Accepted for current architecture baseline

## Context

AI Vastu Architect requires deterministic, reproducible, CAD-grade architectural geometry and source-backed Vastu evaluation.

## Decision

All visual/export formats derive from one deterministic exporter-independent DrawingScene generated from PlanDocument.

## Consequences

This decision is treated as frozen until superseded by a later ADR with explicit migration impact and test coverage.
