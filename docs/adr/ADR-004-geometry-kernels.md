# ADR-004 — Geometry kernels

Status: Accepted for current architecture baseline

## Context

AI Vastu Architect requires deterministic, reproducible, CAD-grade architectural geometry and source-backed Vastu evaluation.

## Decision

Use an internal GeometryKernel abstraction with Clipper2 intended as primary integer polygon kernel and Shapely/GEOS as an independent validation layer.

## Consequences

This decision is treated as frozen until superseded by a later ADR with explicit migration impact and test coverage.
