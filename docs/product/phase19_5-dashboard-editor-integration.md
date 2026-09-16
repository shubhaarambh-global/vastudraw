# Phase 19.5 dashboard/editor integration contract

The dashboard may create an empty project record without inventing a `PlanDocument`.

When an editor route is opened:

1. Read the explicit project UUID from the route.
2. Load the authorized project record.
3. If there is no current revision, stop and show the empty-project state.
4. If there is a current revision, load that exact revision.
5. Verify project/revision identity across metadata and the canonical `PlanDocument`.
6. Render the canonical document through the existing non-authoritative Konva editor.

The editor must not use demo geometry as a project fallback.
