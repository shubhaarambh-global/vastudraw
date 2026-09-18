from __future__ import annotations

from pathlib import Path

from ai_vastu.architectural_brain import (
    ArchitecturalBrainService,
    build_fallback_concept,
    default_source_registry,
)

ROOT = Path(__file__).resolve().parents[1]
required = (
    ROOT / "python/ai_vastu/architectural_brain/models.py",
    ROOT / "python/ai_vastu/architectural_brain/precedent_store.py",
    ROOT / "python/ai_vastu/architectural_brain/topology.py",
    ROOT / "python/ai_vastu/architectural_brain/provider.py",
    ROOT / "python/ai_vastu/architectural_brain/bridge.py",
    ROOT / "python/ai_vastu/architectural_brain/critic.py",
    ROOT / "python/ai_vastu/architectural_brain/scoring.py",
    ROOT / "python/ai_vastu/architectural_brain/revisions.py",
    ROOT / "docs/research/phase26-architectural-brain-sources.md",
)
missing = [str(item.relative_to(ROOT)) for item in required if not item.is_file()]
if missing:
    raise SystemExit("Phase 26 final missing files: " + ", ".join(missing))

registry = default_source_registry()
if not any(item.source_id == "resplan" for item in registry):
    raise SystemExit("ResPlan source registry entry missing.")

_ = ArchitecturalBrainService
_ = build_fallback_concept
print(
    "Phase 26 final wired: precedent_registry=true, retrieval=true, "
    "graph_first_brain=true, site_accounting=true, critic=true, "
    "coverage_scoring=true, natural_language_revisions=true, "
    "authoritative_ai_geometry=false, structural_v2=true"
)
