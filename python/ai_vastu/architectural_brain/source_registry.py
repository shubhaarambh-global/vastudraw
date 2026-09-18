from __future__ import annotations

from .models import LicenseClass, PrecedentSource


def default_source_registry() -> tuple[PrecedentSource, ...]:
    return (
        PrecedentSource(
            source_id="resplan",
            name="ResPlan",
            url="https://github.com/m-agour/ResPlan",
            license_id="CC-BY-4.0",
            license_class=LicenseClass.PRODUCTION_ALLOWED,
            attribution_required=True,
            notes="17,000 residential vector plans with connectivity graphs.",
        ),
        PrecedentSource(
            source_id="msd-json",
            name="Modified Swiss Dwellings JSON",
            url="https://zenodo.org/records/17294451",
            license_id="VERIFY_RELEASE_METADATA",
            license_class=LicenseClass.REVIEW_REQUIRED,
            attribution_required=True,
            notes="4,572 geometries/topological graphs; verify exact release metadata.",
        ),
        PrecedentSource(
            source_id="floorplanqa-layouts",
            name="FloorplanQA Layouts",
            url="https://huggingface.co/datasets/OldDelorean/FloorplanQA-Layouts",
            license_id="CC-BY-4.0",
            license_class=LicenseClass.PRODUCTION_ALLOWED,
            attribution_required=True,
            notes="Structured room layouts with objects, doors and windows.",
        ),
        PrecedentSource(
            source_id="cubicasa5k",
            name="CubiCasa5K",
            url="https://github.com/CubiCasa/CubiCasa5k",
            license_id="CC-BY-NC-4.0",
            license_class=LicenseClass.RESEARCH_ONLY,
            attribution_required=True,
            notes="Do not ingest into the commercial production corpus.",
        ),
        PrecedentSource(
            source_id="zind",
            name="ZInD",
            url="https://github.com/zillow/zind",
            license_id="NON_COMMERCIAL_TERMS",
            license_class=LicenseClass.RESEARCH_ONLY,
            attribution_required=True,
            notes="Research/reference only unless separate commercial rights are obtained.",
        ),
    )


def production_allowed_source_ids() -> frozenset[str]:
    return frozenset(
        item.source_id
        for item in default_source_registry()
        if item.license_class is LicenseClass.PRODUCTION_ALLOWED
    )
