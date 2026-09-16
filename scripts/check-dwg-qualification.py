from ai_vastu.dwg import (
    DwgTargetVersion,
    builtin_backend_candidates,
    preferred_production_candidate,
)

candidates = builtin_backend_candidates()
preferred = preferred_production_candidate()
libredwg = next(item for item in candidates if item.backend_id == "gnu-libredwg")

assert preferred.backend_id == "oda-drawings-sdk"
assert preferred.production_candidate is True
assert preferred.modern_dwg_write is True
assert DwgTargetVersion.R2018 in preferred.supported_targets
assert preferred.bundled is False
assert libredwg.production_candidate is False
assert libredwg.modern_dwg_write is False

print(
    "DWG qualification framework deterministic: "
    f"candidates={len(candidates)}, preferred={preferred.backend_id}, "
    "production_backend_configured=False, export_enabled=False"
)
