from __future__ import annotations

from collections.abc import Iterable

from .models import SiteAccounting, SpaceAllocation


def close_site_accounting(
    *,
    envelope_area_mm2: int,
    allocations: Iterable[SpaceAllocation],
) -> SiteAccounting:
    if envelope_area_mm2 <= 0:
        raise ValueError("envelope_area_mm2 must be positive.")
    items = tuple(allocations)
    classified = sum(item.area_mm2 for item in items)
    if classified > envelope_area_mm2:
        raise ValueError("Classified area exceeds the confirmed envelope.")
    residual = envelope_area_mm2 - classified
    allocation_bp = min(
        10_000,
        (classified * 10_000 + envelope_area_mm2 // 2) // envelope_area_mm2,
    )
    return SiteAccounting(
        envelope_area_mm2=envelope_area_mm2,
        allocations=items,
        classified_area_mm2=classified,
        residual_area_mm2=residual,
        allocation_basis_points=allocation_bp,
    )


def require_no_unexplained_residual(
    accounting: SiteAccounting,
    *,
    tolerance_mm2: int = 10_000,
) -> None:
    if accounting.residual_area_mm2 > tolerance_mm2:
        raise ValueError(
            "Unexplained residual site area exceeds tolerance; classify it as "
            "setback/open-space/courtyard/landscape/utility or allocate it to the plan."
        )
