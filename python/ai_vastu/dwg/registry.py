from __future__ import annotations

from .models import DwgBackendCandidate, DwgBackendKind, DwgTargetVersion


def builtin_backend_candidates() -> tuple[DwgBackendCandidate, ...]:
    return (
        DwgBackendCandidate(
            backend_id="oda-drawings-sdk",
            kind=DwgBackendKind.ODA_DRAWINGS_SDK,
            display_name="Open Design Alliance Drawings SDK",
            source_url="https://www.opendesign.com/products/drawings",
            source_checked_on="2026-09-14",
            license_summary="Commercial ODA membership/runtime; not bundled in this repository.",
            supported_targets=(DwgTargetVersion.R2018,),
            modern_dwg_write=True,
            production_candidate=True,
            bundled=False,
            notes=(
                "ODA documents native DWG create/edit/save support and AC1032-era output.",
                (
                    "Production use still requires licensed runtime integration "
                    "and our own round-trip qualification."
                ),
            ),
        ),
        DwgBackendCandidate(
            backend_id="gnu-libredwg",
            kind=DwgBackendKind.LIBREDWG,
            display_name="GNU LibreDWG",
            source_url="https://www.gnu.org/software/libredwg/",
            source_checked_on="2026-09-14",
            license_summary="GPL-3.0-or-later; not bundled in this repository.",
            supported_targets=(),
            modern_dwg_write=False,
            production_candidate=False,
            bundled=False,
            notes=(
                "LibreDWG 0.13.4 documents useful DWG writing only through R2000.",
                "It is therefore not eligible for the Phase 14 R2018 production target.",
            ),
        ),
    )


def preferred_production_candidate() -> DwgBackendCandidate:
    return next(item for item in builtin_backend_candidates() if item.production_candidate)
