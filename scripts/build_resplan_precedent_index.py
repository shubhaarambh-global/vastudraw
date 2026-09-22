from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

INDEX_VERSION = "vastudraw-resplan-v1"

GRAPH_ROOM_TYPES = (
    "living",
    "kitchen",
    "bedroom",
    "bathroom",
    "balcony",
    "storage",
    "stair",
)

EXTRA_TYPES = (
    "parking",
    "garden",
    "pool",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


def geometry_parts(geometry: Any) -> tuple[Any, ...]:
    if geometry is None:
        return ()

    if getattr(geometry, "is_empty", True):
        return ()

    if hasattr(geometry, "geoms"):
        return tuple(
            item
            for item in geometry.geoms
            if not getattr(item, "is_empty", True)
        )

    return (geometry,)


def geometry_count(geometry: Any) -> int:
    return len(geometry_parts(geometry))


def positive_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(result) or result <= 0:
        return None

    return result


def metric_area(plan: dict[str, Any]) -> tuple[float | None, str | None]:
    """Select the released real-world area field without trusting raw canvas units."""

    for key in ("net_area", "area"):
        value = positive_float(plan.get(key))

        # Wide safety range. We preserve the original values separately too.
        if value is not None and 10.0 <= value <= 5000.0:
            return value, key

    return None, None


def split_lookup(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, str] = {}

    for split_name, identifiers in data.items():
        for identifier in identifiers:
            result[str(identifier)] = str(split_name)

    return result


def canonical_pair(
    left_type: str,
    edge_type: str,
    right_type: str,
) -> str:
    left, right = sorted((left_type, right_type))
    return f"{left}|{edge_type}|{right}"


def topology_signature(
    room_counts: dict[str, int],
    pair_counts: dict[str, int],
    entry_types: tuple[str, ...],
) -> str:
    payload = {
        "rooms": dict(sorted(room_counts.items())),
        "edges": dict(sorted(pair_counts.items())),
        "entry": list(sorted(entry_types)),
    }

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP TABLE IF EXISTS metadata;
        DROP TABLE IF EXISTS precedents;

        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE precedents (
            precedent_id TEXT PRIMARY KEY,
            source_index INTEGER NOT NULL,
            dataset_split TEXT NOT NULL,

            source_area REAL,
            source_net_area REAL,
            metric_area_m2 REAL,
            metric_area_source TEXT,

            raw_width REAL NOT NULL,
            raw_depth REAL NOT NULL,
            raw_inner_area REAL NOT NULL,

            width_m REAL,
            depth_m REAL,
            aspect_ratio REAL NOT NULL,
            wall_depth_m REAL,

            living_count INTEGER NOT NULL,
            bedroom_count INTEGER NOT NULL,
            bathroom_count INTEGER NOT NULL,
            kitchen_count INTEGER NOT NULL,
            balcony_count INTEGER NOT NULL,
            storage_count INTEGER NOT NULL,
            stair_count INTEGER NOT NULL,
            parking_count INTEGER NOT NULL,
            garden_count INTEGER NOT NULL,
            pool_count INTEGER NOT NULL,

            door_count INTEGER NOT NULL,
            window_count INTEGER NOT NULL,
            front_door_count INTEGER NOT NULL,

            graph_ok INTEGER NOT NULL,
            graph_node_count INTEGER NOT NULL,
            graph_edge_count INTEGER NOT NULL,

            direct_edge_count INTEGER NOT NULL,
            door_edge_count INTEGER NOT NULL,
            adjacency_edge_count INTEGER NOT NULL,
            window_edge_count INTEGER NOT NULL,

            entry_room_types_json TEXT NOT NULL,
            room_counts_json TEXT NOT NULL,
            nodes_json TEXT NOT NULL,
            edges_json TEXT NOT NULL,
            pair_counts_json TEXT NOT NULL,

            topology_signature TEXT NOT NULL
        );

        CREATE INDEX precedents_program_idx
            ON precedents(
                bedroom_count,
                bathroom_count,
                kitchen_count,
                parking_count
            );

        CREATE INDEX precedents_aspect_idx
            ON precedents(aspect_ratio);

        CREATE INDEX precedents_area_idx
            ON precedents(metric_area_m2);

        CREATE INDEX precedents_topology_idx
            ON precedents(topology_signature);

        CREATE INDEX precedents_split_idx
            ON precedents(dataset_split);
        """
    )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--resplan-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    root: Path = args.resplan_root.resolve()
    pickle_path = root / "ResPlan.pkl"
    split_path = root / "split.json"

    if not pickle_path.exists():
        raise SystemExit(f"Missing: {pickle_path}")

    if not split_path.exists():
        raise SystemExit(f"Missing: {split_path}")

    # Use ResPlan's own MIT-licensed graph extraction implementation.
    sys.path.insert(0, str(root))

    from resplan_utils import (  # type: ignore[import-not-found]
        add_adjacency_edges,
        plan_to_graph,
    )

    print("Loading ResPlan...")

    with pickle_path.open("rb") as handle:
        plans = pickle.load(handle)

    splits = split_lookup(split_path)

    output: Path = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists():
        output.unlink()

    connection = sqlite3.connect(output)

    try:
        create_schema(connection)

        source_hash = sha256_file(pickle_path)

        metadata = {
            "index_version": INDEX_VERSION,
            "source": "ResPlan",
            "source_url": "https://github.com/m-agour/ResPlan",
            "source_license": "CC BY 4.0 data; MIT code",
            "source_sha256": source_hash,
            "plan_count": str(len(plans)),
        }

        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            tuple(metadata.items()),
        )

        graph_failures = 0

        for index, plan in enumerate(plans):
            inner = plan.get("inner")

            if inner is None or inner.is_empty:
                continue

            min_x, min_y, max_x, max_y = inner.bounds

            raw_width = float(max_x - min_x)
            raw_depth = float(max_y - min_y)
            raw_inner_area = float(inner.area)

            if (
                raw_width <= 0
                or raw_depth <= 0
                or raw_inner_area <= 0
            ):
                continue

            ratio = max(raw_width, raw_depth) / min(
                raw_width,
                raw_depth,
            )

            real_area, real_area_source = metric_area(plan)

            width_m: float | None = None
            depth_m: float | None = None
            wall_depth_m: float | None = None

            if real_area is not None:
                linear_scale = math.sqrt(
                    real_area / raw_inner_area
                )

                width_m = raw_width * linear_scale
                depth_m = raw_depth * linear_scale

                wall_depth = positive_float(
                    plan.get("wall_depth")
                )

                if wall_depth is not None:
                    wall_depth_m = (
                        wall_depth * linear_scale
                    )

            raw_counts = {
                room_type: geometry_count(
                    plan.get(room_type)
                )
                for room_type in (
                    *GRAPH_ROOM_TYPES,
                    *EXTRA_TYPES,
                )
            }

            door_count = geometry_count(plan.get("door"))
            window_count = geometry_count(
                plan.get("window")
            )
            front_door_count = geometry_count(
                plan.get("front_door")
            )

            graph_ok = 1
            nodes: list[dict[str, Any]] = []
            edges: list[dict[str, str]] = []
            pair_counts: Counter[str] = Counter()
            edge_type_counts: Counter[str] = Counter()
            entry_types: set[str] = set()

            try:
                graph = plan_to_graph(plan)
                graph = add_adjacency_edges(graph)

                for node_id, data in sorted(
                    graph.nodes(data=True),
                    key=lambda item: str(item[0]),
                ):
                    node_type = str(
                        data.get("type", "unknown")
                    )
                    geometry = data.get("geometry")

                    node = {
                        "id": str(node_id),
                        "type": node_type,
                    }

                    if (
                        geometry is not None
                        and not geometry.is_empty
                    ):
                        centroid = geometry.centroid

                        node["x"] = round(
                            (
                                float(centroid.x)
                                - min_x
                            )
                            / raw_width,
                            6,
                        )

                        node["y"] = round(
                            (
                                float(centroid.y)
                                - min_y
                            )
                            / raw_depth,
                            6,
                        )

                        node["area_ratio"] = round(
                            float(
                                getattr(
                                    geometry,
                                    "area",
                                    0.0,
                                )
                            )
                            / raw_inner_area,
                            6,
                        )

                    nodes.append(node)

                for left, right, data in sorted(
                    graph.edges(data=True),
                    key=lambda item: (
                        str(item[0]),
                        str(item[1]),
                        str(
                            item[2].get(
                                "type",
                                "unknown",
                            )
                        ),
                    ),
                ):
                    edge_type = str(
                        data.get("type", "unknown")
                    )

                    left_type = str(
                        graph.nodes[left].get(
                            "type",
                            "unknown",
                        )
                    )
                    right_type = str(
                        graph.nodes[right].get(
                            "type",
                            "unknown",
                        )
                    )

                    edges.append(
                        {
                            "a": str(left),
                            "b": str(right),
                            "type": edge_type,
                        }
                    )

                    edge_type_counts[edge_type] += 1

                    pair_counts[
                        canonical_pair(
                            left_type,
                            edge_type,
                            right_type,
                        )
                    ] += 1

                    if left_type == "front_door":
                        entry_types.add(right_type)

                    if right_type == "front_door":
                        entry_types.add(left_type)

            except Exception as exc:
                graph_ok = 0
                graph_failures += 1

                # Keep geometry/program metadata even if the
                # graph cannot be extracted from a damaged plan.
                nodes = []
                edges = []
                pair_counts = Counter()
                edge_type_counts = Counter()
                entry_types = set()

                if graph_failures <= 10:
                    print(
                        "Graph extraction warning:",
                        index,
                        type(exc).__name__,
                        str(exc)[:160],
                    )

            room_counts = {
                key: int(value)
                for key, value in raw_counts.items()
            }

            signature = topology_signature(
                room_counts,
                dict(pair_counts),
                tuple(entry_types),
            )

            precedent_id = str(
                plan.get("id", index)
            )

            dataset_split = splits.get(
                precedent_id,
                "unknown",
            )

            connection.execute(
                """
                INSERT INTO precedents (
                    precedent_id,
                    source_index,
                    dataset_split,

                    source_area,
                    source_net_area,
                    metric_area_m2,
                    metric_area_source,

                    raw_width,
                    raw_depth,
                    raw_inner_area,

                    width_m,
                    depth_m,
                    aspect_ratio,
                    wall_depth_m,

                    living_count,
                    bedroom_count,
                    bathroom_count,
                    kitchen_count,
                    balcony_count,
                    storage_count,
                    stair_count,
                    parking_count,
                    garden_count,
                    pool_count,

                    door_count,
                    window_count,
                    front_door_count,

                    graph_ok,
                    graph_node_count,
                    graph_edge_count,

                    direct_edge_count,
                    door_edge_count,
                    adjacency_edge_count,
                    window_edge_count,

                    entry_room_types_json,
                    room_counts_json,
                    nodes_json,
                    edges_json,
                    pair_counts_json,

                    topology_signature
                )
                VALUES (
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?
                )
                """,
                (
                    precedent_id,
                    index,
                    dataset_split,

                    positive_float(
                        plan.get("area")
                    ),
                    positive_float(
                        plan.get("net_area")
                    ),
                    real_area,
                    real_area_source,

                    raw_width,
                    raw_depth,
                    raw_inner_area,

                    width_m,
                    depth_m,
                    ratio,
                    wall_depth_m,

                    raw_counts["living"],
                    raw_counts["bedroom"],
                    raw_counts["bathroom"],
                    raw_counts["kitchen"],
                    raw_counts["balcony"],
                    raw_counts["storage"],
                    raw_counts["stair"],
                    raw_counts["parking"],
                    raw_counts["garden"],
                    raw_counts["pool"],

                    door_count,
                    window_count,
                    front_door_count,

                    graph_ok,
                    len(nodes),
                    len(edges),

                    edge_type_counts["direct"],
                    edge_type_counts["via_door"],
                    edge_type_counts["adjacency"],
                    edge_type_counts["via_window"],

                    json.dumps(
                        sorted(entry_types),
                        separators=(",", ":"),
                    ),
                    json.dumps(
                        room_counts,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    json.dumps(
                        nodes,
                        separators=(",", ":"),
                    ),
                    json.dumps(
                        edges,
                        separators=(",", ":"),
                    ),
                    json.dumps(
                        dict(sorted(pair_counts.items())),
                        separators=(",", ":"),
                    ),

                    signature,
                ),
            )

            if (index + 1) % 1000 == 0:
                connection.commit()
                print(
                    f"Indexed {index + 1:,}"
                    f" / {len(plans):,}"
                )

        connection.commit()

        total = connection.execute(
            "SELECT COUNT(*) FROM precedents"
        ).fetchone()[0]

        graph_ok = connection.execute(
            """
            SELECT COUNT(*)
            FROM precedents
            WHERE graph_ok = 1
            """
        ).fetchone()[0]

        two_bed = connection.execute(
            """
            SELECT COUNT(*)
            FROM precedents
            WHERE bedroom_count = 2
            """
        ).fetchone()[0]

        three_bed = connection.execute(
            """
            SELECT COUNT(*)
            FROM precedents
            WHERE bedroom_count = 3
            """
        ).fetchone()[0]

        parking = connection.execute(
            """
            SELECT COUNT(*)
            FROM precedents
            WHERE parking_count > 0
            """
        ).fetchone()[0]

        print()
        print("========================================")
        print("VASTUDRAW RESPLAN INDEX COMPLETE")
        print("========================================")
        print("Indexed plans :", total)
        print("Graph-valid   :", graph_ok)
        print("Graph failures:", graph_failures)
        print("2-bedroom     :", two_bed)
        print("3-bedroom     :", three_bed)
        print("With parking  :", parking)
        print("Source SHA256 :", source_hash)
        print("Output        :", output)
        print(
            "Output size   :",
            round(
                output.stat().st_size
                / 1024
                / 1024,
                2,
            ),
            "MB",
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()
