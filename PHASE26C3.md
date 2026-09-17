# Phase 26C.3 — End-to-End Candidate Workspace Binding

This phase binds the validated six-step project wizard to the existing project,
requirements, billing-entitlement, Phase 26A, Phase 26B and Phase 26C.2 stacks.

Flow:

1. Create project.
2. Interpret the wizard brief through the configured requirements provider.
3. Human-confirm the exact structured wizard values.
4. Authorize generation entitlement.
5. Run Phase 26A architectural reasoning.
6. Run Phase 26B soft-Vastu reasoning.
7. Run Phase 26C.2 deterministic multi-candidate generation.
8. Show ranked A/B/C/D candidate PlanDocuments in a comparison workspace.
9. Persist only the candidate explicitly selected by the user.
10. Record billing success only after the selected revision is durably appended.

Candidate preview does not consume a successful-generation quota. A quota is
recorded only after a selected hard-valid canonical PlanDocument is persisted.

Structural design remains outside V1 and is reserved for V2.
Natural-language revision chat remains Phase 26D.
