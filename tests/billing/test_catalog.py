from ai_vastu.billing.catalog import get_product, public_catalog


def test_phase23_catalog_prices_are_exact_in_paise() -> None:
    assert get_product("free_first_generation").amount_paise == 0
    assert get_product("project_single").amount_paise == 39_900
    assert get_product("project_pack_10").amount_paise == 339_900
    assert get_product("pro_monthly").amount_paise == 249_900
    assert get_product("pro_yearly").amount_paise == 2_499_900


def test_public_catalog_contains_five_products() -> None:
    assert len(public_catalog()) == 5
