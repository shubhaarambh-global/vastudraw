# Phase 14 freeze — DWG backend qualification and interoperability

Phase 14 freezes the provider-neutral DWG qualification boundary.

Frozen behavior:

- DWG is never produced by renaming DXF bytes;
- R2018/AC1032 is the only accepted initial production target;
- a backend must declare modern write and round-trip inspection capability;
- qualification is bound to backend id, backend version and DrawingScene hash;
- output must have a DWG signature, millimetre units, required architectural layers, matching scene provenance, semantic entity counts and extents within tolerance;
- production export fails closed unless the exact backend/version has a passing qualification report;
- proprietary/provider runtimes are never bundled in the repository;
- a generic external-command adapter uses argv arrays with `shell=False`;
- ODA Drawings SDK is the preferred production candidate but is not considered qualified until an installed licensed runtime passes the real CAD round-trip gate;
- GNU LibreDWG is not accepted for the R2018 production target because current useful write support is limited to older DWG generations.

Not frozen yet:

- a licensed ODA runtime installation;
- AutoCAD/BricsCAD/DraftSight interoperability evidence produced on CI/lab machines;
- cloud DWG conversion service deployment;
- user-facing DWG download enablement.
