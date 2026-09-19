from __future__ import annotations

import hashlib
import json

from ai_vastu.plan_schema import (
    IntPolygon,
    PlanDocument,
    PurposefulSiteSpace,
    RoomGeometry,
)

from .models import TopologyEdge

# Match the existing notion of a materially changed room used elsewhere
# in candidate scoring. Solver lattice jitter below this scale must not
# manufacture a fake alternative.
SPATIAL_DEDUP_QUANTUM_MM = 300


def _hash_payload(
    payload: object,
) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def semantic_topology_signature(
    edges: tuple[TopologyEdge, ...],
) -> str:
    """Topology identity independent of IDs, order and edge weights.

    Weight changes alone do not constitute a different architectural
    topology. Room relationship and relation kind do.
    """

    semantic_edges = tuple(
        sorted(
            {
                (
                    min(
                        edge.source_room_type,
                        edge.target_room_type,
                    ),
                    max(
                        edge.source_room_type,
                        edge.target_room_type,
                    ),
                    edge.relation,
                )
                for edge in edges
                if (edge.source_room_type != edge.target_room_type)
            }
        )
    )

    return _hash_payload(semantic_edges)


def _bbox(
    polygon: IntPolygon,
) -> tuple[int, int, int, int]:
    xs = tuple(point.x_mm for point in polygon.outer)
    ys = tuple(point.y_mm for point in polygon.outer)

    return (
        min(xs),
        min(ys),
        max(xs),
        max(ys),
    )


def _quantize(
    value: int,
    quantum: int,
) -> int:
    if value >= 0:
        return (value + quantum // 2) // quantum

    return -((-value + quantum // 2) // quantum)


def _normalized_box_signature(
    polygon: IntPolygon,
    *,
    origin_x: int,
    origin_y: int,
    quantum_mm: int,
) -> tuple[int, int, int, int]:
    min_x, min_y, max_x, max_y = _bbox(polygon)

    width = max_x - min_x
    depth = max_y - min_y

    # Use doubled centroids to remain entirely integer-valued.
    center_x2 = min_x + max_x - 2 * origin_x
    center_y2 = min_y + max_y - 2 * origin_y

    return (
        _quantize(
            center_x2,
            quantum_mm * 2,
        ),
        _quantize(
            center_y2,
            quantum_mm * 2,
        ),
        _quantize(
            width,
            quantum_mm,
        ),
        _quantize(
            depth,
            quantum_mm,
        ),
    )


def solved_spatial_signature(
    document: PlanDocument,
    *,
    quantum_mm: int = SPATIAL_DEDUP_QUANTUM_MM,
) -> str:
    """Hash architectural arrangement, excluding all entity UUIDs.

    The signature represents room/site-space type, normalized position and
    dimensions at a 300 mm material-change scale. Candidate IDs, room IDs,
    revision IDs and small CP-SAT lattice jitter cannot create fake diversity.
    """

    if quantum_mm <= 0:
        raise ValueError("quantum_mm must be positive.")

    floors: list[dict[str, object]] = []

    for floor in sorted(
        document.floors,
        key=lambda item: item.index,
    ):
        if floor.boundary is None:
            raise ValueError("Candidate spatial deduplication requires an explicit floor boundary.")

        floor_min_x, floor_min_y, floor_max_x, floor_max_y = _bbox(floor.boundary)

        rooms = tuple(
            sorted(
                (
                    room.room_type.value,
                    *_normalized_box_signature(
                        room.polygon,
                        origin_x=floor_min_x,
                        origin_y=floor_min_y,
                        quantum_mm=quantum_mm,
                    ),
                )
                for room in floor.rooms
            )
        )

        site_spaces = tuple(
            sorted(
                (
                    space.kind.value,
                    *_normalized_box_signature(
                        space.polygon,
                        origin_x=floor_min_x,
                        origin_y=floor_min_y,
                        quantum_mm=quantum_mm,
                    ),
                )
                for space in floor.site_spaces
            )
        )

        floors.append(
            {
                "floor_index": floor.index,
                "envelope": (
                    _quantize(
                        floor_max_x - floor_min_x,
                        quantum_mm,
                    ),
                    _quantize(
                        floor_max_y - floor_min_y,
                        quantum_mm,
                    ),
                ),
                "rooms": rooms,
                "site_spaces": site_spaces,
            }
        )

    return _hash_payload(tuple(floors))


def _room_spatial_record(
    room: RoomGeometry,
) -> tuple[str, int, int, int, int]:
    room_type = room.room_type.value
    min_x, min_y, max_x, max_y = _bbox(room.polygon)

    # Doubled centroid keeps comparison integer-only.
    center_x2 = min_x + max_x
    center_y2 = min_y + max_y

    return (
        room_type,
        center_x2,
        center_y2,
        max_x - min_x,
        max_y - min_y,
    )


def _site_space_spatial_record(
    space: PurposefulSiteSpace,
) -> tuple[str, int, int, int, int]:
    kind = space.kind.value
    min_x, min_y, max_x, max_y = _bbox(space.polygon)

    center_x2 = min_x + max_x
    center_y2 = min_y + max_y

    return (
        kind,
        center_x2,
        center_y2,
        max_x - min_x,
        max_y - min_y,
    )


def _records_equivalent(
    first: tuple[str, int, int, int, int],
    second: tuple[str, int, int, int, int],
    *,
    tolerance_mm: int,
) -> bool:
    if first[0] != second[0]:
        return False

    # Centroids are stored doubled, therefore positional tolerance doubles.
    return (
        abs(first[1] - second[1]) <= tolerance_mm * 2
        and abs(first[2] - second[2]) <= tolerance_mm * 2
        and abs(first[3] - second[3]) <= tolerance_mm
        and abs(first[4] - second[4]) <= tolerance_mm
    )


def _match_spatial_records(
    first: tuple[tuple[str, int, int, int, int], ...],
    second: tuple[tuple[str, int, int, int, int], ...],
    *,
    tolerance_mm: int,
) -> bool:
    """One-to-one fuzzy matching for same-type spatial records."""

    if len(first) != len(second):
        return False

    remaining = list(second)

    for record in first:
        match_index = next(
            (
                index
                for index, candidate in enumerate(remaining)
                if _records_equivalent(
                    record,
                    candidate,
                    tolerance_mm=tolerance_mm,
                )
            ),
            None,
        )

        if match_index is None:
            return False

        remaining.pop(match_index)

    return not remaining


def spatially_equivalent(
    first: PlanDocument,
    second: PlanDocument,
    *,
    tolerance_mm: int = SPATIAL_DEDUP_QUANTUM_MM,
) -> bool:
    """Return True when two solved plans are materially the same.

    Unlike bucketed hashing, this comparison has no quantization-boundary
    artefact: a 50 mm solver jitter remains a 50 mm difference regardless of
    its absolute coordinate.
    """

    if tolerance_mm < 0:
        raise ValueError("tolerance_mm cannot be negative.")

    if len(first.floors) != len(second.floors):
        return False

    first_floors = sorted(
        first.floors,
        key=lambda item: item.index,
    )
    second_floors = sorted(
        second.floors,
        key=lambda item: item.index,
    )

    for first_floor, second_floor in zip(
        first_floors,
        second_floors,
        strict=True,
    ):
        if first_floor.index != second_floor.index:
            return False

        if first_floor.boundary is None or second_floor.boundary is None:
            return False

        first_boundary = _bbox(first_floor.boundary)
        second_boundary = _bbox(second_floor.boundary)

        first_width = first_boundary[2] - first_boundary[0]
        first_depth = first_boundary[3] - first_boundary[1]
        second_width = second_boundary[2] - second_boundary[0]
        second_depth = second_boundary[3] - second_boundary[1]

        if (
            abs(first_width - second_width) > tolerance_mm
            or abs(first_depth - second_depth) > tolerance_mm
        ):
            return False

        first_rooms = tuple(
            sorted(
                (_room_spatial_record(room) for room in first_floor.rooms),
                key=lambda item: (
                    item[0],
                    item[1],
                    item[2],
                    item[3],
                    item[4],
                ),
            )
        )

        second_rooms = tuple(
            sorted(
                (_room_spatial_record(room) for room in second_floor.rooms),
                key=lambda item: (
                    item[0],
                    item[1],
                    item[2],
                    item[3],
                    item[4],
                ),
            )
        )

        if not _match_spatial_records(
            first_rooms,
            second_rooms,
            tolerance_mm=tolerance_mm,
        ):
            return False

        first_spaces = tuple(
            sorted(
                (_site_space_spatial_record(space) for space in first_floor.site_spaces),
                key=lambda item: (
                    item[0],
                    item[1],
                    item[2],
                    item[3],
                    item[4],
                ),
            )
        )

        second_spaces = tuple(
            sorted(
                (_site_space_spatial_record(space) for space in second_floor.site_spaces),
                key=lambda item: (
                    item[0],
                    item[1],
                    item[2],
                    item[3],
                    item[4],
                ),
            )
        )

        if not _match_spatial_records(
            first_spaces,
            second_spaces,
            tolerance_mm=tolerance_mm,
        ):
            return False

    return True


def duplicate_reason_code(
    *,
    topology_signature: str,
    spatial_signature: str,
    prior_topology_signature: str,
    prior_spatial_signature: str,
) -> str | None:
    """Return rejection code for a duplicate solved alternative."""

    if spatial_signature != prior_spatial_signature:
        return None

    if topology_signature == prior_topology_signature:
        return "DUPLICATE_TOPOLOGY_AND_SPATIAL"

    return "DUPLICATE_SPATIAL_CANDIDATE"
