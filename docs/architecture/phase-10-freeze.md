# Phase 10 freeze — deterministic scoring and diverse alternatives

Phase 10 ranks already-generated, already-validated architectural candidates. It is not permitted to
repair invalid geometry, bypass Phase 9, invent user preferences, or fabricate Vastu doctrine.

Frozen scope:
- require a common compiled problem hash across the candidate pool;
- require feasible hashed planner results;
- require geometry hashes to chain to the exact planner result;
- require Phase 9 validation hashes to chain to the exact geometry result;
- reject any candidate with an invalid Phase 9 report;
- optionally reject candidates containing Phase 9 warnings through explicit configuration;
- score preferred dimensions and preferred area using deterministic relative-deviation basis points;
- score preferred floor membership as an explicit binary preference;
- score adjacency requirements using exact integer-mm gap/shared-boundary facts;
- never invent a numeric weight for unweighted adjacency avoidance;
- retain privacy/daylight/ventilation priorities without scoring them until measurable facts exist;
- produce deterministic candidate placement signatures;
- remove exact duplicate placement signatures;
- greedily select ranked alternatives subject to explicit geometric-diversity thresholds;
- tie-break deterministically using score, solver objective penalty, content hash, and candidate ID;
- emit canonical SHA-256 provenance for all scoring outputs.

No Vastu score is produced because the Vastu Specification remains DRAFT with zero frozen production
rules.

Not in Phase 10:
- generation of new solver candidates;
- stochastic exploration;
- AI-authored scoring weights;
- daylight simulation;
- privacy sightline analysis;
- energy/environmental simulation;
- final Vastu scoring;
- CAD/PDF/DWG export.
