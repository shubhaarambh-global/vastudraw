from __future__ import annotations

import random
import time
from typing import Any

import httpx

_TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504}


def post_json_with_retry(
    client: httpx.Client,
    url: str,
    *,
    json_payload: dict[str, Any],
    max_attempts: int = 4,
    base_delay_seconds: float = 1.0,
) -> httpx.Response:
    last_response: httpx.Response | None = None
    last_exception: httpx.HTTPError | None = None

    for attempt in range(max_attempts):
        try:
            response = client.post(url, json=json_payload)
            last_response = response

            if response.status_code not in _TRANSIENT_STATUS:
                response.raise_for_status()
                return response

            if attempt == max_attempts - 1:
                response.raise_for_status()

        except (
            httpx.ConnectError,
            httpx.ReadError,
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
        ) as exc:
            last_exception = exc
            if attempt == max_attempts - 1:
                raise

        delay = base_delay_seconds * (2**attempt)
        jitter = random.uniform(0.0, min(1.0, delay * 0.25))
        time.sleep(delay + jitter)

    if last_response is not None:
        last_response.raise_for_status()

    if last_exception is not None:
        raise last_exception

    raise RuntimeError("Gemini retry loop exited unexpectedly.")
