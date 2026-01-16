"""
Alert Manager integration for centralized logging and error reporting.
Sends alerts to https://alert.d-t.pw per CLIENTNODE.md specification.
"""
import time
from enum import Enum
from typing import Any

import httpx

from app.config import get_settings


settings = get_settings()


class AlertLevel(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    NOTICE = "notice"
    INFO = "info"
    DEBUG = "debug"


class AlertCategory(str, Enum):
    """Alert categories for routing."""
    SECURITY = "security"
    SYSTEM = "system"
    APPLICATION = "application"
    NETWORK = "network"


class AlertManager:
    """
    Client for sending alerts to the Alert Manager system.
    Follows CLIENTNODE.md v1.4.0 specification.
    """

    def __init__(self):
        self.url = settings.alert_manager_url
        self.auth = (
            settings.alert_manager_username,
            settings.alert_manager_password,
        )
        self.enabled = settings.alert_manager_enabled
        self.source = "api.soapboxderbynet.com"
        self.client_name = "soapboxderbynet"

    async def send(
        self,
        level: AlertLevel,
        category: AlertCategory,
        title: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send an alert to Alert Manager.

        Args:
            level: Severity level (critical, warning, notice, info, debug)
            category: Category for routing (security, system, application, network)
            title: Short alert title
            message: Detailed message (will be sanitized for file logs)
            metadata: Optional key-value metadata

        Returns:
            True if alert was sent successfully, False otherwise.
        """
        if not self.enabled:
            return False

        payload = {
            "timestamp": int(time.time()),
            "level": level.value,
            "category": category.value,
            "title": title,
            "message": message,
            "source": self.source,
            "client": self.client_name,
        }

        if metadata:
            payload["metadata"] = metadata

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.url,
                    json=payload,
                    auth=self.auth,
                    headers={
                        "Content-Type": "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    timeout=5.0,
                )
                return response.status_code == 200
        except Exception:
            # Don't let logging failures crash the application
            return False

    async def auth_failure(
        self,
        reason: str,
        user_id: str | None = None,
        ip_address: str | None = None,
    ) -> bool:
        """Log authentication failure."""
        return await self.send(
            level=AlertLevel.WARNING,
            category=AlertCategory.SECURITY,
            title="Authentication Failure",
            message=reason,
            metadata={
                "user_id": user_id,
                "ip_address": ip_address,
            },
        )

    async def device_sync_error(
        self,
        device_id: str,
        error: str,
    ) -> bool:
        """Log device sync error."""
        return await self.send(
            level=AlertLevel.WARNING,
            category=AlertCategory.SYSTEM,
            title="Device Sync Error",
            message=f"Device {device_id}: {error}",
            metadata={"device_id": device_id},
        )

    async def payment_error(
        self,
        user_id: str,
        error: str,
        stripe_error_code: str | None = None,
    ) -> bool:
        """Log payment/donation error."""
        return await self.send(
            level=AlertLevel.WARNING,
            category=AlertCategory.APPLICATION,
            title="Payment Error",
            message=error,
            metadata={
                "user_id": user_id,
                "stripe_error_code": stripe_error_code,
            },
        )

    async def rate_limit_exceeded(
        self,
        identifier: str,
        endpoint: str,
        limit: int,
    ) -> bool:
        """Log rate limit violation."""
        return await self.send(
            level=AlertLevel.NOTICE,
            category=AlertCategory.SECURITY,
            title="Rate Limit Exceeded",
            message=f"Identifier {identifier} exceeded {limit} requests on {endpoint}",
            metadata={
                "identifier": identifier,
                "endpoint": endpoint,
                "limit": limit,
            },
        )

    async def system_error(
        self,
        error: str,
        request_id: str | None = None,
        traceback: str | None = None,
    ) -> bool:
        """Log system/500 error."""
        message = error
        if traceback:
            # Truncate traceback for file logs (max 500 chars per CLIENTNODE.md)
            message = f"{error} | Traceback: {traceback[:400]}"

        return await self.send(
            level=AlertLevel.CRITICAL,
            category=AlertCategory.SYSTEM,
            title="System Error",
            message=message,
            metadata={"request_id": request_id},
        )

    async def security_event(
        self,
        event_type: str,
        description: str,
        user_id: str | None = None,
        ip_address: str | None = None,
    ) -> bool:
        """Log security-relevant event."""
        return await self.send(
            level=AlertLevel.WARNING,
            category=AlertCategory.SECURITY,
            title=event_type,
            message=description,
            metadata={
                "user_id": user_id,
                "ip_address": ip_address,
            },
        )


# Singleton instance
alert_manager = AlertManager()
