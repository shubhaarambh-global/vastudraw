# ADR-036 — Konva/react-konva for the Phase 12 renderer

## Status
Accepted for Phase 12.

## Options evaluated

### SVG
Strong DOM semantics and simple inspection, but large architectural scenes can create very large DOM trees and interaction bookkeeping as wall/opening/annotation counts grow.

### Canvas via Konva/react-konva
Provides a scene graph, hit testing, events, transforms and layered rendering while keeping the canonical geometry outside the renderer. Konva 10+ is documented to work with modern Next.js client components without the historic server-side `canvas` workaround.

## Decision
Use Konva 10 / react-konva 19 behind editor components, with Zustand for transient editor state. Do not use Konva serialization as a project file format.

## Reversibility
The world/screen transform, edit-command protocol and canonical contracts do not depend on Konva types, so another renderer can replace it without changing PlanDocument.
