from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .models import (
    PrecedentEdge,
    PrecedentMatch,
    PrecedentNode,
    PrecedentQuery,
)

_DEFAULT_LIMIT_SCAN = 2500


class PrecedentIndexError(RuntimeError):
    """Raised when the configured precedent index is invalid."""


def _json_list(value: str) -> list[Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise PrecedentIndexError("Expected JSON list in precedent index.")
    return parsed


def _json_dict(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise PrecedentIndexError("Expected JSON object in precedent index.")
    return parsed


def _normalized_delta(actual: float, target: float) -> float:
    if target <= 0:
        return 1.0
    return min(1.0, abs(actual - target) / target)


def _match_score(
    row: sqlite3.Row,
    query: PrecedentQuery,
) -> int:
    """Deterministic similarity score.

    This score is retrieval evidence only. It is not an architectural-quality
    score and must never be presented to the user as design quality.
    """

    penalty = 0

    penalty += abs(int(row["bedroom_count"]) - query.bedrooms) * 3000
    penalty += abs(int(row["bathroom_count"]) - query.bathrooms) * 1200
    penalty += abs(int(row["kitchen_count"]) - query.kitchens) * 1800
    penalty += abs(int(row["living_count"]) - query.living_rooms) * 1500

    parking_count = int(row["parking_count"])
    if parking_count < query.parking_spaces:
        penalty += (query.parking_spaces - parking_count) * 1800
    elif parking_count > query.parking_spaces:
        penalty += (parking_count - query.parking_spaces) * 250

    if query.target_aspect_ratio is not None:
        penalty += round(
            1600
            * _normalized_delta(
                float(row["aspect_ratio"]),
                query.target_aspect_ratio,
            )
        )

    metric_area = row["metric_area_m2"]
    if query.target_area_m2 is not None:
        if metric_area is None:
            penalty += 1000
        else:
            penalty += round(
                1200
                * _normalized_delta(
                    float(metric_area),
                    query.target_area_m2,
                )
            )

    if int(row["front_door_count"]) <= 0:
        penalty += 700

    if int(row["graph_edge_count"]) <= 0:
        penalty += 1200

    entry_types = tuple(str(item) for item in _json_list(str(row["entry_room_types_json"])))

    # A directly legible public arrival sequence is useful evidence for
    # residential precedents. It remains only a retrieval preference.
    if "living" in entry_types:
        penalty -= 150

    return max(0, min(10_000, 10_000 - penalty))


def _to_match(
    row: sqlite3.Row,
    query: PrecedentQuery,
) -> PrecedentMatch:
    nodes_json = _json_list(str(row["nodes_json"]))
    edges_json = _json_list(str(row["edges_json"]))
    pair_json = _json_dict(str(row["pair_counts_json"]))

    nodes = tuple(
        PrecedentNode(
            node_id=str(item["id"]),
            room_type=str(item["type"]),
            x_normalized=(None if item.get("x") is None else float(item["x"])),
            y_normalized=(None if item.get("y") is None else float(item["y"])),
            area_ratio=(None if item.get("area_ratio") is None else float(item["area_ratio"])),
        )
        for item in nodes_json
        if isinstance(item, dict) and "id" in item and "type" in item
    )

    edges = tuple(
        PrecedentEdge(
            source_id=str(item["a"]),
            target_id=str(item["b"]),
            relationship=str(item["type"]),
        )
        for item in edges_json
        if isinstance(item, dict) and "a" in item and "b" in item and "type" in item
    )

    entry_types = tuple(sorted(str(item) for item in _json_list(str(row["entry_room_types_json"]))))

    pair_counts = tuple(
        sorted(
            (
                str(key),
                int(value),
            )
            for key, value in pair_json.items()
        )
    )

    return PrecedentMatch(
        precedent_id=str(row["precedent_id"]),
        source_index=int(row["source_index"]),
        score_basis_points=_match_score(row, query),
        metric_area_m2=(None if row["metric_area_m2"] is None else float(row["metric_area_m2"])),
        width_m=(None if row["width_m"] is None else float(row["width_m"])),
        depth_m=(None if row["depth_m"] is None else float(row["depth_m"])),
        aspect_ratio=float(row["aspect_ratio"]),
        living_count=int(row["living_count"]),
        bedroom_count=int(row["bedroom_count"]),
        bathroom_count=int(row["bathroom_count"]),
        kitchen_count=int(row["kitchen_count"]),
        balcony_count=int(row["balcony_count"]),
        storage_count=int(row["storage_count"]),
        stair_count=int(row["stair_count"]),
        parking_count=int(row["parking_count"]),
        door_count=int(row["door_count"]),
        window_count=int(row["window_count"]),
        front_door_count=int(row["front_door_count"]),
        entry_room_types=entry_types,
        nodes=nodes,
        edges=edges,
        pair_counts=pair_counts,
        topology_signature=str(row["topology_signature"]),
    )


class ResPlanPrecedentStore:
    def __init__(self, index_path: Path) -> None:
        self._index_path = index_path.resolve()

        if not self._index_path.is_file():
            raise PrecedentIndexError(f"ResPlan precedent index not found: {self._index_path}")

    @property
    def index_path(self) -> Path:
        return self._index_path

    @classmethod
    def from_environment(
        cls,
    ) -> ResPlanPrecedentStore:
        raw = os.getenv(
            "AI_VASTU_RESPLAN_INDEX_PATH",
            "",
        ).strip()

        if not raw:
            raise PrecedentIndexError("AI_VASTU_RESPLAN_INDEX_PATH is not configured.")

        return cls(Path(raw))

    def _connect(self) -> sqlite3.Connection:
        uri = self._index_path.as_uri() + "?mode=ro"
        connection = sqlite3.connect(
            uri,
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def metadata(self) -> dict[str, str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT key, value
                FROM metadata
                ORDER BY key
                """
            ).fetchall()

        return {str(row["key"]): str(row["value"]) for row in rows}

    def search(
        self,
        query: PrecedentQuery,
    ) -> tuple[PrecedentMatch, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM precedents
                WHERE graph_ok = 1
                  AND bedroom_count BETWEEN ? AND ?
                  AND bathroom_count BETWEEN ? AND ?
                  AND kitchen_count >= ?
                  AND living_count >= ?
                ORDER BY
                    ABS(bedroom_count - ?) ASC,
                    ABS(bathroom_count - ?) ASC,
                    precedent_id ASC
                LIMIT ?
                """,
                (
                    max(0, query.bedrooms - 1),
                    query.bedrooms + 1,
                    max(0, query.bathrooms - 1),
                    query.bathrooms + 1,
                    max(1, query.kitchens),
                    max(1, query.living_rooms),
                    query.bedrooms,
                    query.bathrooms,
                    _DEFAULT_LIMIT_SCAN,
                ),
            ).fetchall()

        matches = [_to_match(row, query) for row in rows]

        matches.sort(
            key=lambda item: (
                -item.score_basis_points,
                (
                    abs(item.aspect_ratio - query.target_aspect_ratio)
                    if query.target_aspect_ratio is not None
                    else 0.0
                ),
                (
                    abs((item.metric_area_m2 or 0.0) - query.target_area_m2)
                    if query.target_area_m2 is not None
                    else 0.0
                ),
                item.precedent_id,
            )
        )

        # Do not feed multiple nearly-identical topologies to the reasoning
        # layer when a diverse precedent set is available.
        selected: list[PrecedentMatch] = []
        seen_topologies: set[str] = set()

        for match in matches:
            if match.topology_signature in seen_topologies:
                continue

            seen_topologies.add(match.topology_signature)
            selected.append(match)

            if len(selected) >= query.limit:
                break

        return tuple(selected)


def resplan_precedents_enabled() -> bool:
    raw = (
        os.getenv(
            "AI_VASTU_RESPLAN_PRECEDENTS_ENABLED",
            "0",
        )
        .strip()
        .lower()
    )

    return raw in {
        "1",
        "true",
        "yes",
        "on",
    }
