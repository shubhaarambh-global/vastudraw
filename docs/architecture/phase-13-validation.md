# Phase 13 validation gate

The authoritative Windows acceptance gate is:

```powershell
pnpm validate
ruff check python apps/api tests scripts
mypy
pytest
```

Phase 13 additionally requires:

- DrawingScene hash stability for identical canonical input;
- exact wall-opening gap derivation;
- deterministic JPG bytes within the pinned runtime;
- invariant repeated PDF bytes;
- deterministic DXF bytes with fixed metadata mode;
- DXF round-trip parse with millimetre units;
- DXF architectural layer presence;
- native DXF DIMENSION entity presence;
- no export vendor dependency outside the three exporter adapters;
- no DWG backend claim.
