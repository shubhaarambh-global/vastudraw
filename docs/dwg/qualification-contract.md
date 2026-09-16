# DWG qualification contract v1.0

A production backend is eligible only if all conditions pass for the exact runtime version:

1. target is R2018 / AC1032;
2. writer emits a genuine DWG signature (`AC10...`);
3. inspector reports millimetre units;
4. required architecture layers survive;
5. DrawingScene SHA-256 provenance survives;
6. room, visible-wall-segment, opening, dimension and stair counts match;
7. extents match within the configured millimetre tolerance;
8. backend declares modern write and independent round-trip inspection capability;
9. backend is not a test backend;
10. qualification report backend id/version exactly match runtime id/version.

The repository may exercise the harness with fake backends in tests, but a fake backend can never qualify for production.
