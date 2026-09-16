from __future__ import annotations

from collections.abc import Iterable

from .errors import RuleSourceError
from .models import SourceRecord, SourceReference


class SourceRegistry:
    """Immutable-by-convention lookup for Vastu rule provenance records."""

    def __init__(self, records: Iterable[SourceRecord]) -> None:
        ordered = tuple(sorted(records, key=lambda item: item.source_id))
        by_id = {record.source_id: record for record in ordered}
        if len(by_id) != len(ordered):
            raise RuleSourceError("Duplicate source_id in source registry.")
        self._records = ordered
        self._by_id = by_id

    @property
    def records(self) -> tuple[SourceRecord, ...]:
        return self._records

    def require(self, reference: SourceReference) -> SourceRecord:
        try:
            return self._by_id[reference.source_id]
        except KeyError as exc:
            raise RuleSourceError(
                f"Rule references unknown source_id {reference.source_id!r}."
            ) from exc

    def validate_references(self, references: Iterable[SourceReference]) -> None:
        for reference in references:
            self.require(reference)
