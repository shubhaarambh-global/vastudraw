from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ai_vastu.precedents import (
    PrecedentQuery,
    ResPlanPrecedentStore,
)


def _make_index(path: Path) -> None:
    connection = sqlite3.connect(path)

    try:
        connection.executescript(
            """
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
            """
        )

        rows = [
            (
                "best",
                1,
                "train",
                125.0,
                125.0,
                125.0,
                "net_area",
                256.0,
                154.0,
                39000.0,
                15.2,
                9.1,
                1.67,
                0.2,
                1,
                2,
                2,
                1,
                0,
                0,
                0,
                1,
                0,
                0,
                8,
                7,
                1,
                1,
                6,
                8,
                0,
                5,
                3,
                0,
                json.dumps(["living"]),
                json.dumps(
                    {
                        "living": 1,
                        "bedroom": 2,
                        "bathroom": 2,
                        "kitchen": 1,
                        "parking": 1,
                    }
                ),
                json.dumps(
                    [
                        {
                            "id": "living-1",
                            "type": "living",
                            "x": 0.4,
                            "y": 0.3,
                            "area_ratio": 0.2,
                        },
                        {
                            "id": "bedroom-1",
                            "type": "bedroom",
                            "x": 0.2,
                            "y": 0.7,
                            "area_ratio": 0.14,
                        },
                    ]
                ),
                json.dumps(
                    [
                        {
                            "a": "front",
                            "b": "living-1",
                            "type": "via_door",
                        }
                    ]
                ),
                json.dumps({"front_door|via_door|living": 1}),
                "topology-best",
            ),
            (
                "worse",
                2,
                "train",
                200.0,
                200.0,
                200.0,
                "net_area",
                256.0,
                256.0,
                65000.0,
                14.1,
                14.1,
                1.0,
                0.2,
                1,
                3,
                3,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                5,
                3,
                1,
                1,
                5,
                5,
                0,
                2,
                3,
                0,
                json.dumps(["living"]),
                json.dumps(
                    {
                        "living": 1,
                        "bedroom": 3,
                        "bathroom": 3,
                        "kitchen": 1,
                        "parking": 0,
                    }
                ),
                json.dumps([]),
                json.dumps([]),
                json.dumps({}),
                "topology-worse",
            ),
        ]

        connection.executemany(
            """
            INSERT INTO precedents
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
            rows,
        )

        connection.execute(
            """
            INSERT INTO metadata(key, value)
            VALUES ('index_version', 'test-v1')
            """
        )

        connection.commit()

    finally:
        connection.close()


def test_exact_program_and_shape_rank_first(
    tmp_path: Path,
) -> None:
    database = tmp_path / "precedents.sqlite3"
    _make_index(database)

    store = ResPlanPrecedentStore(database)

    results = store.search(
        PrecedentQuery(
            bedrooms=2,
            bathrooms=2,
            kitchens=1,
            living_rooms=1,
            parking_spaces=1,
            target_aspect_ratio=50 / 30,
            target_area_m2=125.0,
            limit=5,
        )
    )

    assert results
    assert results[0].precedent_id == "best"
    assert results[0].score_basis_points > results[-1].score_basis_points


def test_architectural_context_exposes_topology(
    tmp_path: Path,
) -> None:
    database = tmp_path / "precedents.sqlite3"
    _make_index(database)

    result = ResPlanPrecedentStore(database).search(
        PrecedentQuery(
            bedrooms=2,
            bathrooms=2,
            parking_spaces=1,
            target_aspect_ratio=50 / 30,
            target_area_m2=125.0,
            limit=1,
        )
    )[0]

    context = result.architectural_context()

    assert context["precedent_id"] == "best"
    assert context["entry_room_types"] == ("living",)
    assert context["program"]["bedroom"] == 2
    assert context["relationships"]


def test_retrieval_diversifies_topology_signatures(
    tmp_path: Path,
) -> None:
    database = tmp_path / "precedents.sqlite3"
    _make_index(database)

    connection = sqlite3.connect(database)
    try:
        duplicate = connection.execute(
            """
            SELECT *
            FROM precedents
            WHERE precedent_id = 'best'
            """
        ).fetchone()

        assert duplicate is not None

        values = list(duplicate)
        values[0] = "best-copy"
        values[1] = 3

        connection.execute(
            """
            INSERT INTO precedents
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
            values,
        )
        connection.commit()
    finally:
        connection.close()

    results = ResPlanPrecedentStore(database).search(
        PrecedentQuery(
            bedrooms=2,
            bathrooms=2,
            parking_spaces=1,
            target_aspect_ratio=50 / 30,
            target_area_m2=125.0,
            limit=10,
        )
    )

    signatures = [item.topology_signature for item in results]

    assert len(signatures) == len(set(signatures))


def test_metadata_is_readable(
    tmp_path: Path,
) -> None:
    database = tmp_path / "precedents.sqlite3"
    _make_index(database)

    metadata = ResPlanPrecedentStore(database).metadata()

    assert metadata["index_version"] == "test-v1"
