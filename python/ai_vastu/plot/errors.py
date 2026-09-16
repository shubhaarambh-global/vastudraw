class PlotDefinitionError(ValueError):
    """Base error for deterministic plot-definition failures."""


class UnderdeterminedPlotError(PlotDefinitionError):
    """Raised when supplied measurements do not uniquely determine plot geometry."""


class UnsupportedSurveyDefinitionError(PlotDefinitionError):
    """Raised when survey evidence is sufficient in principle but not solved in this phase."""


class UnknownPlotEdgeError(PlotDefinitionError):
    """Raised when an operation references an edge that is not part of the plot."""


class InvalidRoadDefinitionError(PlotDefinitionError):
    """Raised when roads conflict with the whole-edge road model."""
