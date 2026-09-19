"""Phase 8 deterministic architectural geometry builder."""

from .builder import build_architectural_geometry
from .circulation import (
    CirculationDoor,
    CirculationGraph,
    CirculationValidation,
    build_circulation_graph,
    validate_circulation,
)
from .errors import (
    ArchitecturalGeometryError,
    ArchitecturalGeometryInputError,
    OpeningPlacementError,
    StairConstructionError,
)
from .models import (
    ARCHITECTURAL_GEOMETRY_VERSION,
    ArchitecturalGeometryRequest,
    ArchitecturalGeometryResult,
    GeometryNotice,
    GeometryNoticeSeverity,
    OpeningBuildRequest,
    StairBuildRequest,
    WallBuildConfig,
)
from .site_spaces import derive_purposeful_site_spaces
from .vertical import (
    BuildingDiagnostic,
    BuildingDiagnosticSeverity,
    BuildingRoomNode,
    VerticalArchitecturePlanningError,
    VerticalCorePlan,
    VerticalTransfer,
    WetStackEvaluation,
    WetStackPair,
    WetStackRelationship,
    WholeBuildingCirculationGraph,
    WholeBuildingValidation,
    evaluate_wet_stacks,
    plan_vertical_architecture,
    validate_whole_building,
)

__all__ = [
    "ARCHITECTURAL_GEOMETRY_VERSION",
    "ArchitecturalGeometryError",
    "ArchitecturalGeometryInputError",
    "ArchitecturalGeometryRequest",
    "ArchitecturalGeometryResult",
    "BuildingDiagnostic",
    "BuildingDiagnosticSeverity",
    "BuildingRoomNode",
    "CirculationDoor",
    "CirculationGraph",
    "CirculationValidation",
    "GeometryNotice",
    "GeometryNoticeSeverity",
    "OpeningBuildRequest",
    "OpeningPlacementError",
    "StairBuildRequest",
    "StairConstructionError",
    "VerticalArchitecturePlanningError",
    "VerticalCorePlan",
    "VerticalTransfer",
    "WallBuildConfig",
    "WetStackEvaluation",
    "WetStackPair",
    "WetStackRelationship",
    "WholeBuildingCirculationGraph",
    "WholeBuildingValidation",
    "build_architectural_geometry",
    "build_circulation_graph",
    "derive_purposeful_site_spaces",
    "evaluate_wet_stacks",
    "plan_vertical_architecture",
    "validate_circulation",
    "validate_whole_building",
]
