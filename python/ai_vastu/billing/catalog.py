from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProductKind(StrEnum):
    FREE = "free"
    PROJECT = "project"
    PROJECT_PACK = "project_pack"
    SUBSCRIPTION = "subscription"


@dataclass(frozen=True, slots=True)
class BillingProduct:
    sku: str
    name: str
    kind: ProductKind
    amount_paise: int
    currency: str = "INR"
    project_credits: int = 0
    billing_period: str | None = None
    generation_limit_per_project: int | None = None


CATALOG: tuple[BillingProduct, ...] = (
    BillingProduct(
        sku="free_first_generation",
        name="First generation",
        kind=ProductKind.FREE,
        amount_paise=0,
    ),
    BillingProduct(
        sku="project_single",
        name="Single Project",
        kind=ProductKind.PROJECT,
        amount_paise=39_900,
        project_credits=1,
        generation_limit_per_project=3,
    ),
    BillingProduct(
        sku="project_pack_10",
        name="10 Project Pack",
        kind=ProductKind.PROJECT_PACK,
        amount_paise=339_900,
        project_credits=10,
        generation_limit_per_project=5,
    ),
    BillingProduct(
        sku="pro_monthly",
        name="Pro Monthly",
        kind=ProductKind.SUBSCRIPTION,
        amount_paise=249_900,
        billing_period="monthly",
    ),
    BillingProduct(
        sku="pro_yearly",
        name="Pro Yearly",
        kind=ProductKind.SUBSCRIPTION,
        amount_paise=2_499_900,
        billing_period="yearly",
    ),
)

_BY_SKU = {product.sku: product for product in CATALOG}


def get_product(sku: str) -> BillingProduct:
    try:
        return _BY_SKU[sku]
    except KeyError as exc:
        raise ValueError(f"Unknown billing SKU: {sku}") from exc


def public_catalog() -> list[dict[str, object]]:
    return [
        {
            "sku": item.sku,
            "name": item.name,
            "kind": item.kind.value,
            "amount_paise": item.amount_paise,
            "currency": item.currency,
            "project_credits": item.project_credits,
            "billing_period": item.billing_period,
            "generation_limit_per_project": item.generation_limit_per_project,
        }
        for item in CATALOG
    ]
