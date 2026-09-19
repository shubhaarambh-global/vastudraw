from .bridge import apply_architectural_concept
from .candidate_dedup import (
    SPATIAL_DEDUP_QUANTUM_MM,
    duplicate_reason_code,
    semantic_topology_signature,
    solved_spatial_signature,
    spatially_equivalent,
)
from .candidate_engine import run_architectural_brain_candidates
from .critic import critique_plan
from .models import (
    ArchitecturalConcept,
    ArchitecturalCritique,
    ArchitecturalQualityScore,
    ConceptRoom,
    CritiqueFinding,
    CritiqueSeverity,
    EvidenceStatus,
    LicenseClass,
    PrecedentFingerprint,
    PrecedentSource,
    QualityMetric,
    RetrievedPrecedent,
    RevisionDirective,
    RevisionOperation,
    SiteAccounting,
    SpaceAllocation,
    StructuredRevisionIntent,
    TopologyEdge,
)
from .precedent_store import JsonlPrecedentStore, PrecedentQuery
from .precedent_topology import (
    bind_precedent_topologies,
    precedent_topology_edges,
    topology_signature,
)
from .revisions import (
    apply_revision_intent,
    deterministic_revision_interpretation,
    interpret_revision,
    interpret_revision_with_gemini,
    interpret_revision_with_openrouter,
)
from .scoring import score_plan_document
from .service import ArchitecturalBrainRun, ArchitecturalBrainService
from .site_accounting import close_site_accounting, require_no_unexplained_residual
from .source_registry import default_source_registry, production_allowed_source_ids
from .topology import build_fallback_concept, default_residential_topology

__all__ = [
    "SPATIAL_DEDUP_QUANTUM_MM",
    "ArchitecturalBrainRun",
    "ArchitecturalBrainService",
    "ArchitecturalConcept",
    "ArchitecturalCritique",
    "ArchitecturalQualityScore",
    "ConceptRoom",
    "CritiqueFinding",
    "CritiqueSeverity",
    "EvidenceStatus",
    "JsonlPrecedentStore",
    "LicenseClass",
    "PrecedentFingerprint",
    "PrecedentQuery",
    "PrecedentSource",
    "QualityMetric",
    "RetrievedPrecedent",
    "RevisionDirective",
    "RevisionOperation",
    "SiteAccounting",
    "SpaceAllocation",
    "StructuredRevisionIntent",
    "TopologyEdge",
    "apply_architectural_concept",
    "apply_revision_intent",
    "bind_precedent_topologies",
    "build_fallback_concept",
    "close_site_accounting",
    "critique_plan",
    "default_residential_topology",
    "default_source_registry",
    "deterministic_revision_interpretation",
    "duplicate_reason_code",
    "interpret_revision",
    "interpret_revision_with_gemini",
    "interpret_revision_with_openrouter",
    "precedent_topology_edges",
    "production_allowed_source_ids",
    "require_no_unexplained_residual",
    "run_architectural_brain_candidates",
    "score_plan_document",
    "semantic_topology_signature",
    "solved_spatial_signature",
    "spatially_equivalent",
    "topology_signature",
]
