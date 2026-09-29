from __future__ import annotations

import os

from ai_vastu.production.settings import load_production_settings

from .phonepe import PhonePeClient, PhonePeConfigurationError


def create_phonepe_client() -> PhonePeClient:
    """Create the single configured server-side PhonePe adapter."""

    if os.getenv("APP_ENV", "development").strip().lower() == "production":
        settings = load_production_settings()
        environment = settings.phonepe_environment
        client_id = settings.phonepe_client_id
        client_secret = settings.phonepe_client_secret
        client_version = settings.phonepe_client_version
        redirect_url = settings.phonepe_redirect_url
        webhook_username = settings.phonepe_webhook_username
        webhook_password = settings.phonepe_webhook_password
        connect_timeout = settings.phonepe_connect_timeout_seconds
        read_timeout = settings.phonepe_read_timeout_seconds
        expire_seconds = settings.phonepe_order_expire_seconds
        if any(
            value is None
            for value in (
                environment,
                client_id,
                client_secret,
                client_version,
                redirect_url,
                webhook_username,
                webhook_password,
                connect_timeout,
                read_timeout,
                expire_seconds,
            )
        ):
            raise PhonePeConfigurationError("PhonePe configuration is incomplete.")
        assert environment is not None
        assert client_id is not None
        assert client_secret is not None
        assert client_version is not None
        assert redirect_url is not None
        assert webhook_username is not None
        assert webhook_password is not None
        assert connect_timeout is not None
        assert read_timeout is not None
        assert expire_seconds is not None
        return PhonePeClient(
            environment=environment,
            client_id=client_id,
            client_secret=client_secret,
            client_version=client_version,
            redirect_url=redirect_url,
            webhook_username=webhook_username,
            webhook_password=webhook_password,
            connect_timeout_seconds=connect_timeout,
            read_timeout_seconds=read_timeout,
            order_expire_seconds=expire_seconds,
        )

    try:
        return PhonePeClient(
            environment=os.getenv("AI_VASTU_PHONEPE_ENVIRONMENT", "sandbox"),
            client_id=os.getenv("AI_VASTU_PHONEPE_CLIENT_ID", ""),
            client_secret=os.getenv("AI_VASTU_PHONEPE_CLIENT_SECRET", ""),
            client_version=os.getenv("AI_VASTU_PHONEPE_CLIENT_VERSION", "1"),
            redirect_url=os.getenv("AI_VASTU_PHONEPE_REDIRECT_URL", ""),
            webhook_username=os.getenv("AI_VASTU_PHONEPE_WEBHOOK_USERNAME", ""),
            webhook_password=os.getenv("AI_VASTU_PHONEPE_WEBHOOK_PASSWORD", ""),
            connect_timeout_seconds=float(
                os.getenv("AI_VASTU_PHONEPE_CONNECT_TIMEOUT_SECONDS", "3")
            ),
            read_timeout_seconds=float(
                os.getenv("AI_VASTU_PHONEPE_READ_TIMEOUT_SECONDS", "10")
            ),
            order_expire_seconds=int(
                os.getenv("AI_VASTU_PHONEPE_ORDER_EXPIRE_SECONDS", "1200")
            ),
        )
    except ValueError as exc:
        raise PhonePeConfigurationError("PhonePe configuration is invalid.") from exc
