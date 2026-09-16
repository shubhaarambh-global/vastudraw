# ADR-013 — Fixed-Point Angular Unit

Status: Accepted in Phase 1

## Decision

Store canonical orientation angles as integer microdegrees (`1 degree = 1,000,000 µdeg`) normalized to `[0, 360°)`.

## Rationale

It avoids making binary floating-point values authoritative while providing substantially finer resolution than required for plot orientation input. Trigonometric calculations may use floating point as derived computation, but may not silently rewrite canonical angle values.
