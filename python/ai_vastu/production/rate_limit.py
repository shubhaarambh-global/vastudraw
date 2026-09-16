from __future__ import annotations

import hashlib
from dataclasses import dataclass

import psycopg


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    count: int | None
    limit: int


def hash_rate_limit_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def consume_postgres_fixed_window(
    *,
    database_url: str,
    scope: str,
    key_hash: str,
    limit: int,
    window_seconds: int = 3600,
) -> RateLimitDecision:
    if limit <= 0 or window_seconds <= 0:
        raise ValueError("Rate-limit values must be positive.")

    query = """
    INSERT INTO ai_vastu_rate_limit_windows (
        scope,
        key_hash,
        window_start,
        request_count
    )
    VALUES (
        %(scope)s,
        %(key_hash)s,
        to_timestamp(
            floor(extract(epoch from clock_timestamp()) / %(window_seconds)s)
            * %(window_seconds)s
        ),
        1
    )
    ON CONFLICT (scope, key_hash, window_start)
    DO UPDATE
      SET request_count = ai_vastu_rate_limit_windows.request_count + 1
    WHERE ai_vastu_rate_limit_windows.request_count < %(limit)s
    RETURNING request_count
    """

    params = {
        "scope": scope,
        "key_hash": key_hash,
        "window_seconds": window_seconds,
        "limit": limit,
    }

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
        connection.commit()

    if row is None:
        return RateLimitDecision(allowed=False, count=None, limit=limit)
    return RateLimitDecision(allowed=True, count=int(row[0]), limit=limit)
