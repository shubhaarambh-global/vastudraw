# Phase 15 Production Readiness Contract

The readiness report is repository-derived and fail-closed. It separates three concepts:

1. **engineering validation** — code, tests and deterministic subsystem smokes pass;
2. **release readiness** — all required public-MVP capabilities exist;
3. **provider qualification** — optional provider-specific features such as live DWG output
   are enabled only after their own qualification contract passes.

The report currently checks canonical schema support, Vastu specification lifecycle,
production-rule presence and hash pinning, deterministic engine wiring, immutable project
revisions, the 2D editor, JPG/PDF/DXF export, and the fail-closed DWG pathway. It also
tracks unresolved public-MVP blockers for authorization, production persistence, planning
API orchestration and web/API workflow integration.

A future phase that resolves a blocker must update both implementation and the expected
blocker set; deleting a blocker from the check without implementing the capability is a
policy violation.
