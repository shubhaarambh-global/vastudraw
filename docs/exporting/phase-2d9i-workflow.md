# Stage 2D9I production export workflow

## Authority and identity

Exports are rendered only from an immutable persisted `RevisionRecord`. The API
requires the project ID, revision ID, and selected candidate ID, then verifies:

1. the authenticated user owns the project;
2. the revision belongs to that project;
3. `RevisionRecord.source_candidate_id` matches the requested candidate;
4. the persisted PlanDocument hash matches canonical content.

Export never invokes generation, the Architectural Brain, or CP-SAT.

## Endpoint

`POST /projects/{project_id}/exports`

The request contains `revision_id`, `candidate_id`, an allowlisted `format`
(`SVG`, `JPEG`, `PDF`, or `DXF`), `scope` (`FLOOR` or `ALL_FLOORS`), and a
canonical `floor_index` for an individual floor. `ALL_FLOORS` is accepted only
for PDF and produces one genuine multi-page PDF in floor-index order.

The response is the artifact bytes with a safe `Content-Disposition` filename
and source/candidate/hash headers. Rendering is in memory; the endpoint exposes
no filesystem path and persists no temporary file.

## Manifest and filenames

`ExportManifest` is operational metadata, separate from PlanDocument. It binds
the renderer version, project, revision, candidate, source PlanDocument hash,
format, floor identity, sanitized filename, media type, byte size, artifact
SHA-256, and combined/single-floor status.

Filename components are normalized to lowercase ASCII slugs, bounded to 64
characters, and stripped of path separators and unsafe characters. Examples:

- `vastudraw-sharma-residence-ground-floor.svg`
- `vastudraw-sharma-residence-first-floor.dxf`
- `vastudraw-sharma-residence-all-floors.pdf`

## Failure semantics

Each request produces exactly one in-memory response. Combined PDF rendering is
atomic: if any page fails, no partial PDF is returned. Renderer failures use
bounded export reason codes and do not expose stack traces or local paths.

Exports do not consume another generation entitlement and introduce no billing
bypass. They are available only for an already-persisted selected revision,
which is created through the existing entitlement-controlled selection flow.
