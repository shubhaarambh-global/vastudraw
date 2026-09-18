from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import PrecedentFingerprint, RetrievedPrecedent
from .source_registry import production_allowed_source_ids


@dataclass(frozen=True, slots=True)
class PrecedentQuery:
    width_mm: int
    depth_mm: int
    bedroom_count: int
    toilet_count: int
    parking_count: int
    room_types: frozenset[str]
    road_side: str | None = None
    entrance_side: str | None = None


def _ratio_delta(a_width: int, a_depth: int, b_width: int, b_depth: int) -> float:
    return abs((a_width / a_depth) - (b_width / b_depth))


def _similarity(
    query: PrecedentQuery,
    item: PrecedentFingerprint,
) -> tuple[int, tuple[str, ...]]:
    score = 10_000
    reasons: list[str] = []

    ratio_penalty = min(
        3000,
        int(
            _ratio_delta(
                query.width_mm,
                query.depth_mm,
                item.width_mm,
                item.depth_mm,
            )
            * 4000
        ),
    )
    score -= ratio_penalty
    if ratio_penalty < 500:
        reasons.append("similar plot aspect ratio")

    area_q = query.width_mm * query.depth_mm
    area_i = item.width_mm * item.depth_mm
    area_delta = abs(area_q - area_i) / max(area_q, area_i)
    score -= min(2500, int(area_delta * 4000))
    if area_delta <= 0.15:
        reasons.append("similar plot area")

    program_penalty = (
        abs(query.bedroom_count - item.bedroom_count) * 650
        + abs(query.toilet_count - item.toilet_count) * 350
        + abs(query.parking_count - item.parking_count) * 300
    )
    score -= min(3000, program_penalty)
    if query.bedroom_count == item.bedroom_count:
        reasons.append("same bedroom count")

    overlap = len(query.room_types.intersection(item.room_types))
    union = len(query.room_types.union(item.room_types)) or 1
    score -= int((1 - overlap / union) * 1500)
    if overlap:
        reasons.append("matching room program")

    if query.road_side and item.road_side:
        if query.road_side == item.road_side:
            score += 250
            reasons.append("same road side")
        else:
            score -= 250
    if query.entrance_side and item.entrance_side:
        if query.entrance_side == item.entrance_side:
            score += 250
            reasons.append("same entrance side")
        else:
            score -= 250

    return max(0, min(10_000, score)), tuple(reasons)


class JsonlPrecedentStore:
    def __init__(self, path: str | Path, *, production_mode: bool = True) -> None:
        self._path = Path(path)
        self._production_mode = production_mode

    def load(self) -> tuple[PrecedentFingerprint, ...]:
        if not self._path.exists():
            return ()
        allowed = production_allowed_source_ids()
        records: list[PrecedentFingerprint] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                item = PrecedentFingerprint.model_validate_json(line)
                if self._production_mode and item.source_id not in allowed:
                    continue
                records.append(item)
        return tuple(records)

    def append(self, item: PrecedentFingerprint) -> None:
        if self._production_mode and item.source_id not in production_allowed_source_ids():
            raise PermissionError(
                f"Source {item.source_id!r} is not approved for production ingestion."
            )
        normalized = item.with_content_hash()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(normalized.model_dump_json())
            handle.write("\n")

    def retrieve(
        self,
        query: PrecedentQuery,
        *,
        limit: int = 24,
    ) -> tuple[RetrievedPrecedent, ...]:
        ranked: list[RetrievedPrecedent] = []
        for item in self.load():
            score, reasons = _similarity(query, item)
            ranked.append(
                RetrievedPrecedent(
                    fingerprint=item,
                    similarity_basis_points=score,
                    reasons=reasons,
                )
            )
        ranked.sort(
            key=lambda result: (
                -result.similarity_basis_points,
                result.fingerprint.precedent_id,
            )
        )
        return tuple(ranked[:limit])
