from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, NoReturn
from urllib.parse import quote, urlparse

import httpx

MAX_PHONEPE_RESPONSE_BYTES = 64 * 1024
DEFAULT_TOKEN_EXPIRY_SKEW_SECONDS = 60.0
MAX_EPOCH_MILLISECONDS = 4_102_444_800_000


class PhonePeEnvironment(StrEnum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"


class PhonePeOrderState(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PhonePeFailureCategory(StrEnum):
    AUTHENTICATION = "authentication"
    REQUEST_REJECTED = "request_rejected"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"


class PhonePeConfigurationError(ValueError):
    """Raised for invalid local PhonePe configuration."""


class PhonePeRequestError(ValueError):
    """Raised before I/O when a checkout/status request violates the provider contract."""


class PhonePeProviderError(RuntimeError):
    """Sanitized PhonePe failure that never contains a response body or credential."""

    def __init__(self, category: PhonePeFailureCategory) -> None:
        self.category = category
        self.retryable = category in {
            PhonePeFailureCategory.RATE_LIMITED,
            PhonePeFailureCategory.UNAVAILABLE,
            PhonePeFailureCategory.TIMEOUT,
        }
        super().__init__(f"PhonePe request failed ({category.value}).")


@dataclass(frozen=True, slots=True)
class PhonePeCheckout:
    merchant_order_id: str
    provider_order_id: str
    redirect_url: str
    state: PhonePeOrderState
    expire_at: int


@dataclass(frozen=True, slots=True)
class PhonePeOrderStatus:
    merchant_order_id: str
    provider_order_id: str
    state: PhonePeOrderState
    amount_paise: int
    currency: str | None
    expire_at: int


@dataclass(frozen=True, slots=True)
class _PhonePeEndpoints:
    oauth_url: str
    payment_url: str
    status_url_template: str


_ENDPOINTS = {
    PhonePeEnvironment.SANDBOX: _PhonePeEndpoints(
        oauth_url="https://api-preprod.phonepe.com/apis/pg-sandbox/v1/oauth/token",
        payment_url="https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/pay",
        status_url_template=(
            "https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/order/"
            "{merchant_order_id}/status"
        ),
    ),
    PhonePeEnvironment.PRODUCTION: _PhonePeEndpoints(
        oauth_url="https://api.phonepe.com/apis/identity-manager/v1/oauth/token",
        payment_url="https://api.phonepe.com/apis/pg/checkout/v2/pay",
        status_url_template=(
            "https://api.phonepe.com/apis/pg/checkout/v2/order/"
            "{merchant_order_id}/status"
        ),
    ),
}

_MERCHANT_ORDER_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,63}\Z")
_CLIENT_VERSION_PATTERN = re.compile(r"[1-9][0-9]{0,8}\Z")
_TOKEN_PATTERN = re.compile(r"[^\s]{1,16384}\Z")
_PROVIDER_ORDER_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")


def validate_callback_authorization(
    username: str,
    password: str,
    authorization: str,
) -> bool:
    """Validate PhonePe's SHA callback Authorization value in constant time."""

    expected = hashlib.sha256(f"{username}:{password}".encode()).hexdigest()
    return hmac.compare_digest(expected, authorization)


class PhonePeClient:
    """Small direct-HTTP adapter for PhonePe Standard Checkout v2."""

    def __init__(
        self,
        *,
        environment: PhonePeEnvironment | str,
        client_id: str,
        client_secret: str,
        client_version: str | int,
        redirect_url: str,
        webhook_username: str,
        webhook_password: str,
        connect_timeout_seconds: float = 3.0,
        read_timeout_seconds: float = 10.0,
        order_expire_seconds: int = 1200,
        token_expiry_skew_seconds: float = DEFAULT_TOKEN_EXPIRY_SKEW_SECONDS,
        max_response_bytes: int = MAX_PHONEPE_RESPONSE_BYTES,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.time,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        try:
            resolved_environment = PhonePeEnvironment(environment)
        except ValueError as exc:
            raise PhonePeConfigurationError("PhonePe environment is invalid.") from exc
        if not _is_bounded_text(client_id, maximum=256) or not _is_bounded_text(
            client_secret, maximum=512
        ):
            raise PhonePeConfigurationError("PhonePe API credentials are invalid.")
        normalized_client_version = str(client_version)
        if _CLIENT_VERSION_PATTERN.fullmatch(normalized_client_version) is None:
            raise PhonePeConfigurationError("PhonePe client version is invalid.")
        if not _is_redirect_url(redirect_url, require_https=resolved_environment == "production"):
            raise PhonePeConfigurationError("PhonePe redirect URL is invalid.")
        if not _is_bounded_text(webhook_username, maximum=256) or not _is_bounded_text(
            webhook_password, maximum=512
        ):
            raise PhonePeConfigurationError("PhonePe callback credentials are invalid.")
        _validate_positive_finite(connect_timeout_seconds, "connect timeout")
        _validate_positive_finite(read_timeout_seconds, "read timeout")
        if not 300 <= order_expire_seconds <= 3600:
            raise PhonePeConfigurationError("PhonePe order expiry is invalid.")
        if (
            isinstance(token_expiry_skew_seconds, bool)
            or not isinstance(token_expiry_skew_seconds, int | float)
            or token_expiry_skew_seconds < 0
            or token_expiry_skew_seconds > 300
            or not math.isfinite(token_expiry_skew_seconds)
        ):
            raise PhonePeConfigurationError("PhonePe token expiry skew is invalid.")
        if not 1024 <= max_response_bytes <= 1024 * 1024:
            raise PhonePeConfigurationError("PhonePe response limit is invalid.")

        self._environment = resolved_environment
        self._endpoints = _ENDPOINTS[resolved_environment]
        self._client_id = client_id
        self._client_secret = client_secret
        self._client_version = normalized_client_version
        self._redirect_url = redirect_url
        self._webhook_username = webhook_username
        self._webhook_password = webhook_password
        self._order_expire_seconds = order_expire_seconds
        self._token_expiry_skew_seconds = token_expiry_skew_seconds
        self._max_response_bytes = max_response_bytes
        self._clock = clock
        self._monotonic = monotonic
        self._total_timeout_seconds = connect_timeout_seconds + read_timeout_seconds
        self._http = httpx.Client(
            timeout=httpx.Timeout(
                read_timeout_seconds,
                connect=connect_timeout_seconds,
                read=read_timeout_seconds,
                write=connect_timeout_seconds,
                pool=connect_timeout_seconds,
            ),
            transport=transport,
            follow_redirects=False,
        )
        self._token: str | None = None
        self._token_type: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = threading.Lock()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> PhonePeClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def create_checkout(
        self,
        *,
        merchant_order_id: str,
        amount_paise: int,
        currency: str,
    ) -> PhonePeCheckout:
        """Create one checkout exactly once; ambiguous failures are never retried."""

        _validate_merchant_order_id(merchant_order_id)
        if isinstance(amount_paise, bool) or not isinstance(amount_paise, int):
            raise PhonePeRequestError("PhonePe checkout amount is invalid.")
        if not 100 <= amount_paise <= 2**63 - 1:
            raise PhonePeRequestError("PhonePe checkout amount is invalid.")
        if currency != "INR":
            raise PhonePeRequestError("PhonePe checkout currency is unsupported.")

        result = self._request_json(
            "POST",
            self._endpoints.payment_url,
            headers={
                "Authorization": self._authorization_header(),
                "Content-Type": "application/json",
            },
            json_body={
                "merchantOrderId": merchant_order_id,
                "amount": amount_paise,
                "expireAfter": self._order_expire_seconds,
                "paymentFlow": {
                    "type": "PG_CHECKOUT",
                    "merchantUrls": {"redirectUrl": self._redirect_url},
                },
            },
        )
        provider_order_id = _required_provider_order_id(result, "orderId")
        state = _required_state(result)
        if state is not PhonePeOrderState.PENDING:
            raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)
        redirect_url = _required_checkout_url(result, "redirectUrl")
        expire_at = _required_epoch_milliseconds(result, "expireAt")
        return PhonePeCheckout(
            merchant_order_id=merchant_order_id,
            provider_order_id=provider_order_id,
            redirect_url=redirect_url,
            state=state,
            expire_at=expire_at,
        )

    def get_order_status(self, merchant_order_id: str) -> PhonePeOrderStatus:
        """Query one authoritative order status without automatic retries."""

        _validate_merchant_order_id(merchant_order_id)
        escaped_order_id = quote(merchant_order_id, safe="")
        result = self._request_json(
            "GET",
            self._endpoints.status_url_template.format(
                merchant_order_id=escaped_order_id
            ),
            headers={
                "Authorization": self._authorization_header(),
                "Content-Type": "application/json",
            },
            query={"details": "false", "errorContext": "false"},
        )
        response_merchant_order_id = result.get("merchantOrderId")
        if (
            response_merchant_order_id is not None
            and response_merchant_order_id != merchant_order_id
        ):
            raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)
        currency = result.get("currency")
        if currency is not None and currency != "INR":
            raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)
        return PhonePeOrderStatus(
            merchant_order_id=merchant_order_id,
            provider_order_id=_required_provider_order_id(result, "orderId"),
            state=_required_state(result),
            amount_paise=_required_positive_int(result, "amount"),
            currency=currency,
            expire_at=_required_epoch_milliseconds(result, "expireAt"),
        )

    def verify_callback_authorization(self, authorization: str) -> bool:
        return validate_callback_authorization(
            self._webhook_username,
            self._webhook_password,
            authorization,
        )

    def _authorization_header(self) -> str:
        token, token_type = self._get_token()
        return f"{token_type} {token}"

    def _get_token(self) -> tuple[str, str]:
        now = self._clock()
        if self._token_is_fresh(now):
            assert self._token is not None
            assert self._token_type is not None
            return self._token, self._token_type
        with self._token_lock:
            now = self._clock()
            if self._token_is_fresh(now):
                assert self._token is not None
                assert self._token_type is not None
                return self._token, self._token_type
            result = self._request_json(
                "POST",
                self._endpoints.oauth_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                form_body={
                    "client_id": self._client_id,
                    "client_version": self._client_version,
                    "client_secret": self._client_secret,
                    "grant_type": "client_credentials",
                },
            )
            token = result.get("access_token")
            token_type = result.get("token_type")
            expires_at = result.get("expires_at")
            if (
                not isinstance(token, str)
                or _TOKEN_PATTERN.fullmatch(token) is None
                or token_type != "O-Bearer"
                or isinstance(expires_at, bool)
                or not isinstance(expires_at, int)
                or expires_at > 9_999_999_999
                or expires_at <= now
            ):
                raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)
            self._token = token
            self._token_type = token_type
            self._token_expires_at = float(expires_at)
            return token, token_type

    def _token_is_fresh(self, now: float) -> bool:
        return (
            self._token is not None
            and self._token_type is not None
            and now < self._token_expires_at - self._token_expiry_skew_seconds
        )

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any] | None = None,
        form_body: dict[str, str] | None = None,
        query: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        deadline = self._monotonic() + self._total_timeout_seconds
        try:
            with self._http.stream(
                method,
                url,
                headers=headers,
                json=json_body,
                data=form_body,
                params=query,
            ) as response:
                if response.status_code < 200 or response.status_code >= 300:
                    self._raise_for_status(response.status_code)
                body = self._read_bounded_body(response, deadline=deadline)
        except PhonePeProviderError:
            raise
        except httpx.TimeoutException:
            raise PhonePeProviderError(PhonePeFailureCategory.TIMEOUT) from None
        except httpx.RequestError:
            raise PhonePeProviderError(PhonePeFailureCategory.UNAVAILABLE) from None

        return _decode_json_object(body)

    def _read_bounded_body(self, response: httpx.Response, *, deadline: float) -> bytes:
        raw_length = response.headers.get("Content-Length")
        if raw_length is not None:
            try:
                declared_length = int(raw_length)
            except ValueError:
                raise PhonePeProviderError(
                    PhonePeFailureCategory.INVALID_RESPONSE
                ) from None
            if declared_length < 0 or declared_length > self._max_response_bytes:
                raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)

        body = bytearray()
        for chunk in response.iter_bytes():
            if self._monotonic() >= deadline:
                raise PhonePeProviderError(PhonePeFailureCategory.TIMEOUT)
            if len(body) + len(chunk) > self._max_response_bytes:
                raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)
            body.extend(chunk)
        if self._monotonic() >= deadline:
            raise PhonePeProviderError(PhonePeFailureCategory.TIMEOUT)
        return bytes(body)

    @staticmethod
    def _raise_for_status(status_code: int) -> NoReturn:
        if status_code in {401, 403}:
            category = PhonePeFailureCategory.AUTHENTICATION
        elif status_code == 429:
            category = PhonePeFailureCategory.RATE_LIMITED
        elif 400 <= status_code < 500:
            category = PhonePeFailureCategory.REQUEST_REJECTED
        else:
            category = PhonePeFailureCategory.UNAVAILABLE
        raise PhonePeProviderError(category)


def _validate_positive_finite(value: float, label: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or value <= 0
        or value > 60
        or not math.isfinite(value)
    ):
        raise PhonePeConfigurationError(f"PhonePe {label} is invalid.")


def _is_bounded_text(value: object, *, maximum: int) -> bool:
    return isinstance(value, str) and 0 < len(value) <= maximum and value.strip() == value


def _is_redirect_url(value: str, *, require_https: bool) -> bool:
    if not _is_bounded_text(value, maximum=2048):
        return False
    parsed = urlparse(value)
    allowed_schemes = {"https"} if require_https else {"http", "https"}
    return (
        parsed.scheme in allowed_schemes
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
    )


def _validate_merchant_order_id(merchant_order_id: str) -> None:
    if (
        not isinstance(merchant_order_id, str)
        or _MERCHANT_ORDER_ID_PATTERN.fullmatch(merchant_order_id) is None
    ):
        raise PhonePeRequestError("PhonePe merchant order ID is invalid.")


def _required_provider_order_id(value: dict[str, Any], field: str) -> str:
    provider_order_id = value.get(field)
    if (
        not isinstance(provider_order_id, str)
        or _PROVIDER_ORDER_ID_PATTERN.fullmatch(provider_order_id) is None
    ):
        raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)
    return provider_order_id


def _required_state(value: dict[str, Any]) -> PhonePeOrderState:
    raw_state = value.get("state")
    if not isinstance(raw_state, str):
        raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)
    try:
        return PhonePeOrderState(raw_state)
    except ValueError:
        raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE) from None


def _required_positive_int(value: dict[str, Any], field: str) -> int:
    result = value.get(field)
    if isinstance(result, bool) or not isinstance(result, int) or result <= 0:
        raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)
    return result


def _required_epoch_milliseconds(value: dict[str, Any], field: str) -> int:
    result = _required_positive_int(value, field)
    if result > MAX_EPOCH_MILLISECONDS:
        raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)
    return result


def _required_checkout_url(value: dict[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not _is_redirect_url(result, require_https=True):
        raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)
    parsed = urlparse(result)
    hostname = parsed.hostname or ""
    if (
        hostname != "phonepe.com"
        and not hostname.endswith(".phonepe.com")
    ) or parsed.port not in {None, 443}:
        raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)
    return result


def _decode_json_object(body: bytes) -> dict[str, Any]:
    def reject_constant(_value: str) -> NoReturn:
        raise ValueError

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    def parse_finite_float(raw_value: str) -> float:
        result = float(raw_value)
        if not math.isfinite(result):
            raise ValueError
        return result

    try:
        value = json.loads(
            body,
            parse_constant=reject_constant,
            parse_float=parse_finite_float,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
        raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE) from None
    if not isinstance(value, dict):
        raise PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)
    return value
