from ai_vastu.production.rate_limit import hash_rate_limit_key


def test_rate_limit_key_is_deterministic_and_does_not_store_secret() -> None:
    secret = "Bearer top-secret-token"
    digest = hash_rate_limit_key(secret)
    assert digest == hash_rate_limit_key(secret)
    assert len(digest) == 64
    assert secret not in digest
