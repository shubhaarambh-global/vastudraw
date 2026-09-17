from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from ai_vastu.plan_schema import IntPoint, IntPolygon

from .errors import NonIntegralGeometryError
from .ring_math import canonicalize_polygon, point_in_ring, signed_area2_ring

PathLike = Sequence[Sequence[float | int]]


def polygon_to_paths(polygon: IntPolygon) -> list[list[tuple[int, int]]]:
    canonical = canonicalize_polygon(polygon)
    paths: list[list[tuple[int, int]]] = []
    paths.append([(p.x_mm, p.y_mm) for p in canonical.outer])
    paths.extend([[(p.x_mm, p.y_mm) for p in hole] for hole in canonical.holes])
    return paths


def _to_int_coordinate(value: Any) -> int:
    numeric = float(value)
    rounded = round(numeric)
    if abs(numeric - rounded) > 1e-9:
        raise NonIntegralGeometryError(
            f"Primary integer geometry kernel returned non-integral coordinate {numeric!r}."
        )
    return int(rounded)


def path_to_ring(path: Iterable[Sequence[Any]]) -> tuple[IntPoint, ...]:
    points = tuple(
        IntPoint(x_mm=_to_int_coordinate(point[0]), y_mm=_to_int_coordinate(point[1]))
        for point in path
    )
    if len(points) >= 2 and points[0] == points[-1]:
        points = points[:-1]
    if len(points) < 3:
        raise NonIntegralGeometryError(
            "Geometry kernel returned a degenerate path with <3 vertices."
        )
    return points


def paths_to_polygons(paths: Iterable[Iterable[Sequence[Any]]]) -> tuple[IntPolygon, ...]:
    rings = [path_to_ring(path) for path in paths]
    rings = [ring for ring in rings if signed_area2_ring(ring) != 0]
    if not rings:
        return ()

    abs_areas = [abs(signed_area2_ring(ring)) for ring in rings]
    parent: list[int | None] = [None] * len(rings)
    for child_idx, child in enumerate(rings):
        probe = child[0]
        candidates: list[tuple[int, int]] = []
        for container_idx, container in enumerate(rings):
            if child_idx == container_idx or abs_areas[container_idx] <= abs_areas[child_idx]:
                continue
            if point_in_ring(probe, container):
                candidates.append((abs_areas[container_idx], container_idx))
        if candidates:
            parent[child_idx] = min(candidates)[1]

    depth: list[int] = [0] * len(rings)
    for idx in range(len(rings)):
        seen: set[int] = set()
        cur = idx
        d = 0
        next_parent = parent[cur]
        while next_parent is not None:
            if cur in seen:
                raise NonIntegralGeometryError("Geometry kernel returned cyclic ring containment.")
            seen.add(cur)
            cur = next_parent
            d += 1
            next_parent = parent[cur]
        depth[idx] = d

    polygons: list[IntPolygon] = []
    for idx, ring in enumerate(rings):
        if depth[idx] % 2 != 0:
            continue
        holes = [
            rings[h] for h in range(len(rings)) if parent[h] == idx and depth[h] == depth[idx] + 1
        ]
        polygons.append(canonicalize_polygon(IntPolygon(outer=ring, holes=tuple(holes))))

    from .ring_math import polygon_sort_key

    return tuple(sorted(polygons, key=polygon_sort_key))
