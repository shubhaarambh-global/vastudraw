from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from math import isqrt
from uuid import UUID, uuid5

from ai_vastu.plan_schema import (
    ClosureReport,
    DeclaredMeasurement,
    IntPoint,
    IntPolygon,
    LengthUnit,
    Plot,
    PlotGeometryType,
    PlotInputSource,
    Road,
    VerificationStatus,
    quantize_length_mm,
)

from .errors import (
    InvalidRoadDefinitionError,
    PlotDefinitionError,
    UnderdeterminedPlotError,
    UnknownPlotEdgeError,
    UnsupportedSurveyDefinitionError,
)

LengthInput = Decimal | int | str


@dataclass(frozen=True, slots=True)
class PlotEdge:
    id: UUID
    index: int
    start: IntPoint
    end: IntPoint


@dataclass(frozen=True, slots=True)
class SurveyQuadrilateralDefinition:
    """Phase-2 survey evidence for a four-sided plot.

    Four side lengths alone do not determine a unique quadrilateral. Phase 2 accepts
    verified corner coordinates as authoritative geometry. Diagonal/angle/bearing
    evidence is represented so later survey solvers can be added without changing the
    fail-closed API, but Phase 2 does not infer coordinates from that evidence.
    """

    side_lengths_mm: tuple[int, int, int, int]
    diagonal_mm: int | None = None
    interior_angle_udeg: int | None = None
    bearings_udeg: tuple[int, int, int, int] | None = None
    corner_coordinates: tuple[IntPoint, IntPoint, IntPoint, IntPoint] | None = None

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or value <= 0 for value in self.side_lengths_mm):
            raise PlotDefinitionError("Survey side lengths must be positive integer millimetres.")
        if self.diagonal_mm is not None and self.diagonal_mm <= 0:
            raise PlotDefinitionError("Survey diagonal must be positive when supplied.")


@dataclass(frozen=True, slots=True)
class RoadSetValidation:
    road_count: int
    referenced_edge_count: int
    primary_access_road_id: UUID | None


def derive_edge_ids(plot_id: UUID, edge_count: int) -> tuple[UUID, ...]:
    """Derive stable edge IDs from the plot ID; never generate hidden random IDs."""

    if edge_count < 3:
        raise PlotDefinitionError("A plot must have at least three edges.")
    return tuple(uuid5(plot_id, f"plot-edge:{index}") for index in range(edge_count))


def _declared_length(
    label: str, value: LengthInput, unit: LengthUnit
) -> tuple[DeclaredMeasurement, int]:
    quantized = quantize_length_mm(value, unit)
    declared = DeclaredMeasurement(
        label=label,
        input_value=quantized.input_value,
        input_unit=quantized.input_unit,
        exact_mm_decimal=quantized.exact_mm,
        quantized_mm=quantized.mm,
        rounding_delta_mm_decimal=quantized.rounding_delta_mm,
    )
    return declared, quantized.mm


def _measurement_from_mm(label: str, value_mm: int) -> DeclaredMeasurement:
    if isinstance(value_mm, bool) or value_mm <= 0:
        raise PlotDefinitionError("Survey side lengths must be positive integer millimetres.")
    text = str(value_mm)
    return DeclaredMeasurement(
        label=label,
        input_value=text,
        input_unit=LengthUnit.MM,
        exact_mm_decimal=text,
        quantized_mm=value_mm,
        rounding_delta_mm_decimal="0",
    )


def create_rectangular_plot(
    *,
    plot_id: UUID,
    width_value: LengthInput,
    width_unit: LengthUnit,
    depth_value: LengthInput,
    depth_unit: LengthUnit,
    origin: IntPoint | None = None,
    input_source: PlotInputSource = PlotInputSource.MANUAL,
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED,
) -> Plot:
    """Create an axis-aligned rectangular canonical plot in integer millimetres."""

    width_declared, width_mm = _declared_length("plot_width", width_value, width_unit)
    depth_declared, depth_mm = _declared_length("plot_depth", depth_value, depth_unit)
    if width_mm <= 0 or depth_mm <= 0:
        raise PlotDefinitionError(
            "Plot width and depth must remain positive after mm quantization."
        )

    origin_point = origin or IntPoint(x_mm=0, y_mm=0)
    x0 = origin_point.x_mm
    y0 = origin_point.y_mm
    boundary = IntPolygon(
        outer=(
            origin_point,
            IntPoint(x_mm=x0 + width_mm, y_mm=y0),
            IntPoint(x_mm=x0 + width_mm, y_mm=y0 + depth_mm),
            IntPoint(x_mm=x0, y_mm=y0 + depth_mm),
        )
    )
    return Plot(
        id=plot_id,
        geometry_type=PlotGeometryType.RECTANGLE,
        boundary=boundary,
        edge_ids=derive_edge_ids(plot_id, 4),
        input_source=input_source,
        verification_status=verification_status,
        declared_measurements=(width_declared, depth_declared),
    )


def signed_double_area(vertices: Sequence[IntPoint]) -> int:
    """Return twice the signed area using exact integer arithmetic."""

    if len(vertices) < 3:
        raise PlotDefinitionError("A polygon requires at least three vertices.")
    total = 0
    for index, point in enumerate(vertices):
        following = vertices[(index + 1) % len(vertices)]
        total += point.x_mm * following.y_mm - following.x_mm * point.y_mm
    return total


def _validate_polygon_vertices(vertices: Sequence[IntPoint]) -> None:
    if len(vertices) < 3:
        raise PlotDefinitionError("A polygon requires at least three vertices.")
    if vertices[0] == vertices[-1]:
        raise PlotDefinitionError("Polygon rings are open; do not repeat the first vertex.")
    for index, point in enumerate(vertices):
        following = vertices[(index + 1) % len(vertices)]
        if point == following:
            raise PlotDefinitionError("Plot boundary cannot contain a zero-length edge.")
    if signed_double_area(vertices) == 0:
        raise PlotDefinitionError("Plot boundary has zero signed area.")


def create_polygon_plot(
    *,
    plot_id: UUID,
    vertices: Sequence[IntPoint],
    input_source: PlotInputSource,
    verification_status: VerificationStatus,
    declared_measurements: Sequence[DeclaredMeasurement] = (),
    closure_report: ClosureReport | None = None,
) -> Plot:
    """Create polygon storage from already established coordinates.

    Self-intersection/topology validation intentionally belongs to Phase 3. Phase 2
    checks only basic determinism/degeneracy and never invents missing coordinates.
    """

    _validate_polygon_vertices(vertices)
    boundary = IntPolygon(outer=tuple(vertices))
    return Plot(
        id=plot_id,
        geometry_type=PlotGeometryType.POLYGON,
        boundary=boundary,
        edge_ids=derive_edge_ids(plot_id, len(vertices)),
        input_source=input_source,
        verification_status=verification_status,
        declared_measurements=tuple(declared_measurements),
        closure_report=closure_report,
    )


def create_survey_quadrilateral(
    *,
    plot_id: UUID,
    definition: SurveyQuadrilateralDefinition,
    verification_status: VerificationStatus = VerificationStatus.SURVEY_VERIFIED,
    closure_report: ClosureReport | None = None,
) -> Plot:
    """Create a survey quadrilateral only when authoritative corner coordinates exist."""

    if definition.corner_coordinates is None:
        has_extra_evidence = any(
            (
                definition.diagonal_mm is not None,
                definition.interior_angle_udeg is not None,
                definition.bearings_udeg is not None,
            )
        )
        if not has_extra_evidence:
            raise UnderdeterminedPlotError(
                "Four side lengths alone do not uniquely determine a quadrilateral. "
                "Supply a diagonal, angle, bearings, or verified corner coordinates."
            )
        raise UnsupportedSurveyDefinitionError(
            "Phase 2 records diagonal/angle/bearing evidence but does not yet solve "
            "coordinates from it. Supply verified corner coordinates for authoritative geometry."
        )

    declared = tuple(
        _measurement_from_mm(f"side_{index + 1}", value)
        for index, value in enumerate(definition.side_lengths_mm)
    )
    return create_polygon_plot(
        plot_id=plot_id,
        vertices=definition.corner_coordinates,
        input_source=PlotInputSource.SURVEY,
        verification_status=verification_status,
        declared_measurements=declared,
        closure_report=closure_report,
    )


def _rounded_hypot_mm(dx: int, dy: int) -> int:
    """Nearest integer Euclidean length using exact integer arithmetic, half-up."""

    squared = dx * dx + dy * dy
    lower = isqrt(squared)
    if 4 * squared >= (2 * lower + 1) ** 2:
        return lower + 1
    return lower


def make_closure_report(
    *, expected_close: IntPoint, observed_close: IntPoint, tolerance_mm: int
) -> ClosureReport:
    if isinstance(tolerance_mm, bool) or tolerance_mm < 0:
        raise PlotDefinitionError(
            "Closure tolerance must be a non-negative integer millimetre value."
        )
    error_mm = _rounded_hypot_mm(
        observed_close.x_mm - expected_close.x_mm,
        observed_close.y_mm - expected_close.y_mm,
    )
    return ClosureReport(
        closure_error_mm=error_mm,
        tolerance_mm=tolerance_mm,
        accepted=error_mm <= tolerance_mm,
    )


def plot_edges(plot: Plot) -> tuple[PlotEdge, ...]:
    points = plot.boundary.outer
    return tuple(
        PlotEdge(
            id=plot.edge_ids[index],
            index=index,
            start=point,
            end=points[(index + 1) % len(points)],
        )
        for index, point in enumerate(points)
    )


def get_plot_edge(plot: Plot, edge_id: UUID) -> PlotEdge:
    for edge in plot_edges(plot):
        if edge.id == edge_id:
            return edge
    raise UnknownPlotEdgeError(f"Unknown plot edge ID: {edge_id}")


def create_road(
    *,
    plot: Plot,
    road_id: UUID,
    plot_edge_ids: Sequence[UUID],
    name: str | None = None,
    width_mm: int | None = None,
    primary_access: bool = False,
) -> Road:
    edge_ids = tuple(plot_edge_ids)
    if not edge_ids:
        raise InvalidRoadDefinitionError("A road must reference at least one plot boundary edge.")
    if len(set(edge_ids)) != len(edge_ids):
        raise InvalidRoadDefinitionError(
            "A road cannot reference the same plot edge more than once."
        )
    known = set(plot.edge_ids)
    unknown = set(edge_ids) - known
    if unknown:
        raise UnknownPlotEdgeError(
            f"Road references unknown plot edge IDs: {sorted(map(str, unknown))}"
        )
    if width_mm is not None and (isinstance(width_mm, bool) or width_mm <= 0):
        raise InvalidRoadDefinitionError("Road width must be positive integer millimetres.")
    return Road(
        id=road_id,
        name=name,
        plot_edge_ids=edge_ids,
        width_mm=width_mm,
        primary_access=primary_access,
    )


def validate_road_set(plot: Plot, roads: Sequence[Road]) -> RoadSetValidation:
    road_tuple = tuple(roads)
    road_ids = [road.id for road in road_tuple]
    if len(set(road_ids)) != len(road_ids):
        raise InvalidRoadDefinitionError("Road IDs must be unique.")

    known = set(plot.edge_ids)
    referenced: set[UUID] = set()
    primary_ids: list[UUID] = []
    for road in road_tuple:
        if not road.plot_edge_ids:
            raise InvalidRoadDefinitionError(
                "A road must reference at least one plot boundary edge."
            )
        if len(set(road.plot_edge_ids)) != len(road.plot_edge_ids):
            raise InvalidRoadDefinitionError("A road cannot repeat a plot edge reference.")
        road_edges = set(road.plot_edge_ids)
        unknown = road_edges - known
        if unknown:
            raise UnknownPlotEdgeError(
                f"Road references unknown plot edge IDs: {sorted(map(str, unknown))}"
            )
        overlap = referenced & road_edges
        if overlap:
            raise InvalidRoadDefinitionError(
                "Whole-edge road model cannot assign a plot edge to multiple roads."
            )
        referenced.update(road_edges)
        if road.primary_access:
            primary_ids.append(road.id)

    if len(primary_ids) > 1:
        raise InvalidRoadDefinitionError("At most one road may be marked primary_access.")

    return RoadSetValidation(
        road_count=len(road_tuple),
        referenced_edge_count=len(referenced),
        primary_access_road_id=primary_ids[0] if primary_ids else None,
    )
