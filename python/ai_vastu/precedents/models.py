from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PrecedentQuery:
    bedrooms: int
    bathrooms: int
    kitchens: int = 1
    living_rooms: int = 1
    parking_spaces: int = 0
    target_aspect_ratio: float | None = None
    target_area_m2: float | None = None
    limit: int = 12

    def __post_init__(self) -> None:
        if self.bedrooms < 0:
            raise ValueError("bedrooms cannot be negative.")
        if self.bathrooms < 0:
            raise ValueError("bathrooms cannot be negative.")
        if self.kitchens < 0:
            raise ValueError("kitchens cannot be negative.")
        if self.living_rooms < 0:
            raise ValueError("living_rooms cannot be negative.")
        if self.parking_spaces < 0:
            raise ValueError("parking_spaces cannot be negative.")
        if self.target_aspect_ratio is not None and self.target_aspect_ratio <= 0:
            raise ValueError("target_aspect_ratio must be positive.")
        if self.target_area_m2 is not None and self.target_area_m2 <= 0:
            raise ValueError("target_area_m2 must be positive.")
        if not 1 <= self.limit <= 100:
            raise ValueError("limit must be between 1 and 100.")


@dataclass(frozen=True, slots=True)
class PrecedentNode:
    node_id: str
    room_type: str
    x_normalized: float | None = None
    y_normalized: float | None = None
    area_ratio: float | None = None


@dataclass(frozen=True, slots=True)
class PrecedentEdge:
    source_id: str
    target_id: str
    relationship: str


@dataclass(frozen=True, slots=True)
class PrecedentMatch:
    precedent_id: str
    source_index: int
    score_basis_points: int

    metric_area_m2: float | None
    width_m: float | None
    depth_m: float | None
    aspect_ratio: float

    living_count: int
    bedroom_count: int
    bathroom_count: int
    kitchen_count: int
    balcony_count: int
    storage_count: int
    stair_count: int
    parking_count: int

    door_count: int
    window_count: int
    front_door_count: int

    entry_room_types: tuple[str, ...]
    nodes: tuple[PrecedentNode, ...]
    edges: tuple[PrecedentEdge, ...]
    pair_counts: tuple[tuple[str, int], ...]
    topology_signature: str

    def architectural_context(self) -> dict[str, object]:
        """Compact topology context safe to pass to the reasoning layer."""

        return {
            "precedent_id": self.precedent_id,
            "similarity_basis_points": self.score_basis_points,
            "area_m2": self.metric_area_m2,
            "aspect_ratio": self.aspect_ratio,
            "program": {
                "living": self.living_count,
                "bedroom": self.bedroom_count,
                "bathroom": self.bathroom_count,
                "kitchen": self.kitchen_count,
                "balcony": self.balcony_count,
                "storage": self.storage_count,
                "stair": self.stair_count,
                "parking": self.parking_count,
            },
            "entry_room_types": self.entry_room_types,
            "room_graph": tuple(
                {
                    "id": node.node_id,
                    "type": node.room_type,
                    "x": node.x_normalized,
                    "y": node.y_normalized,
                    "area_ratio": node.area_ratio,
                }
                for node in self.nodes
            ),
            "relationships": tuple(
                {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "type": edge.relationship,
                }
                for edge in self.edges
            ),
            "relationship_counts": dict(self.pair_counts),
            "topology_signature": self.topology_signature,
        }
