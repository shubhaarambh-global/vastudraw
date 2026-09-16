# Phase 19.5 — Dashboard / Editor Integration & UX Cleanup

Phase 19.5 closes the visual correctness gap exposed during live dashboard testing.

## Primary invariant

A project editor route is bound to the project UUID in the URL and may render CAD geometry only from that project's current persisted canonical `PlanDocument` revision.

It must never substitute the historical Phase 12 demo fixture when the project has no canonical revision.

## Behavior

- `/editor?project=<uuid>` loads the authorized project record.
- If the project has a current revision, the exact revision is fetched and identity-checked before rendering.
- `project_id` and `revision_id` must agree across project metadata, revision metadata, and the persisted `PlanDocument`.
- If the project has no revision, the editor renders an explicit empty project state and refuses to invent plot or room geometry.
- The project header shows the real project name and current revision.
- A direct navigation path back to the dashboard is always available.
- The engineering-heavy create/load project form is removed from the primary editor experience.
- Staged editor commands remain visibly non-persisted until a dedicated server-side command application flow exists.
- The browser `fetch` implementation is bound to `globalThis`, preventing the `Illegal invocation` failure observed in live Phase 19 testing.

## Release-gate impact

None. Phase 19.5 is a product-correctness and UX integration phase. The three remaining release blockers remain Vastu specification blockers and are not relaxed here.
