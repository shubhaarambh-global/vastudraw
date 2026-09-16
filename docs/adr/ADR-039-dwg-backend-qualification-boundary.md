# ADR-039 — DWG backend qualification boundary

## Decision

DWG generation is a provider adapter behind a strict qualification interface. The planning engine and canonical geometry never depend on a DWG vendor SDK. DXF generated from the same `DrawingScene` is the interchange input to a qualified DWG converter, and the resulting DWG must be independently inspected before it can be accepted.

## Consequences

- no fake extension rename;
- backend replacement does not change canonical geometry;
- qualification is version-specific and scene-bound;
- production export fails closed without evidence;
- licensed/proprietary runtimes remain external deployment dependencies.
