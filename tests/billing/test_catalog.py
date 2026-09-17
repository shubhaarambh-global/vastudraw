from ai_vastu.billing.catalog import get_product, public_catalog


def test_phase23_catalog_prices_are_exact_in_paise() -> None:
    assert get_product("free_first_generation").amount_paise == 0
    assert get_product("project_single").amount_paise == 49_900
    assert get_product("project_pack_10").amount_paise == 489_900
    assert get_product("pro_monthly").amount_paise == 999_900
    assert get_product("pro_yearly").amount_paise == 6_999_900


def test_public_catalog_contains_five_products() -> None:
    assert len(public_catalog()) == 5


def test_launch_catalog_generation_limits_are_exact() -> None:
    single = get_product("project_single")
    pack = get_product("project_pack_10")
    monthly = get_product("pro_monthly")
    yearly = get_product("pro_yearly")

    assert single.generation_limit_per_project == 3
    assert pack.generation_limit_per_project == 5
    assert monthly.generation_limit_per_project is None
    assert yearly.generation_limit_per_project is None
