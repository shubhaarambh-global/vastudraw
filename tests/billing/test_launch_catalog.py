from ai_vastu.billing.catalog import get_product, public_catalog


def test_launch_catalog_prices_and_project_generation_metadata() -> None:
    single = get_product("project_single")
    pack = get_product("project_pack_10")
    monthly = get_product("pro_monthly")
    yearly = get_product("pro_yearly")

    assert single.amount_paise == 49_900
    assert single.project_credits == 1
    assert single.generation_limit_per_project == 3

    assert pack.amount_paise == 489_900
    assert pack.project_credits == 10
    assert pack.generation_limit_per_project == 5

    assert monthly.amount_paise == 999_900
    assert monthly.generation_limit_per_project is None

    assert yearly.amount_paise == 6_999_900
    assert yearly.generation_limit_per_project is None

    public = {item["sku"]: item for item in public_catalog()}
    assert public["project_single"]["generation_limit_per_project"] == 3
    assert public["project_pack_10"]["generation_limit_per_project"] == 5
