"""
Mock utilities for testing authentication and external services.
"""
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from jose import jwt

from app.config import get_settings


# Use test settings
TEST_SECRET_KEY = "test-secret-key-for-testing-only"
TEST_ALGORITHM = "HS256"


def create_test_token(
    user_id: str,
    email: str,
    system_role: str = "user",
    org_memberships: list[dict] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a valid JWT token for testing.

    Args:
        user_id: User ID to include in token
        email: User email
        system_role: System role (user/admin)
        org_memberships: List of org memberships
        expires_delta: Token expiration time

    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=1)

    expires_at = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": user_id,
        "type": "user",
        "email": email,
        "role": system_role,
        "orgs": org_memberships or [],
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
        "iss": "soapboxderbynet.com",
    }

    return jwt.encode(payload, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)


def create_expired_token(user_id: str, email: str) -> str:
    """Create an expired token for testing expiration handling."""
    return create_test_token(
        user_id=user_id,
        email=email,
        expires_delta=timedelta(hours=-1),  # Expired 1 hour ago
    )


def create_device_token(
    device_id: str,
    org_id: str,
    permissions: list[str] | None = None,
) -> str:
    """Create a device JWT token for testing."""
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    payload = {
        "sub": device_id,
        "type": "device",
        "org_id": org_id,
        "permissions": permissions or ["sync:write", "telemetry:write"],
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
        "iss": "soapboxderbynet.com",
    }

    return jwt.encode(payload, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)


class MockFirebaseAuth:
    """
    Mock Firebase Authentication for testing.

    Usage:
        with patch("modules.auth.firebase.verify_firebase_token", MockFirebaseAuth.verify_token):
            # Test code that uses Firebase auth
    """

    # Predefined test users
    TEST_USERS = {
        "valid_token": {
            "uid": "firebase_test_uid_123",
            "email": "testuser@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
            "email_verified": True,
            "sign_in_provider": "google.com",
        },
        "admin_token": {
            "uid": "firebase_admin_uid_456",
            "email": "admin@gmail.com",
            "name": "Admin User",
            "picture": None,
            "email_verified": True,
            "sign_in_provider": "google.com",
        },
        "unverified_token": {
            "uid": "firebase_unverified_uid",
            "email": "unverified@gmail.com",
            "name": "Unverified User",
            "email_verified": False,
            "sign_in_provider": "google.com",
        },
        "non_google_token": {
            "uid": "firebase_password_uid",
            "email": "password@example.com",
            "name": "Password User",
            "email_verified": True,
            "sign_in_provider": "password",
        },
    }

    @classmethod
    async def verify_token(cls, id_token: str) -> dict[str, Any]:
        """
        Mock Firebase token verification.

        Pass specific token strings to get predefined responses:
        - "valid_token": Returns valid user
        - "admin_token": Returns admin user
        - "unverified_token": Raises error (email not verified)
        - "non_google_token": Raises error (not Google sign-in)
        - "invalid_token": Raises error
        - "expired_token": Raises error

        Any other token starting with "valid_" returns a generated user.
        """
        if id_token in cls.TEST_USERS:
            user = cls.TEST_USERS[id_token]

            # Check email verified
            if not user.get("email_verified", False):
                raise ValueError("Email not verified")

            # Check sign-in provider
            if user.get("sign_in_provider") != "google.com":
                raise ValueError("Invalid sign-in provider: Only Google sign-in is allowed.")

            return user

        if id_token == "invalid_token":
            raise ValueError("Invalid ID token")

        if id_token == "expired_token":
            raise ValueError("ID token has expired")

        if id_token.startswith("valid_"):
            # Generate a user for any "valid_" prefixed token
            return {
                "uid": f"firebase_{id_token}",
                "email": f"{id_token}@gmail.com",
                "name": f"User {id_token}",
                "picture": None,
                "email_verified": True,
                "sign_in_provider": "google.com",
            }

        raise ValueError("Invalid ID token")


class MockRedis:
    """Mock Redis client for testing."""

    def __init__(self):
        self._data: dict[str, Any] = {}
        self._expiry: dict[str, datetime] = {}

    async def get(self, key: str) -> str | None:
        """Get a value from mock Redis."""
        if key in self._expiry:
            if datetime.utcnow() > self._expiry[key]:
                del self._data[key]
                del self._expiry[key]
                return None
        return self._data.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool:
        """Set a value in mock Redis."""
        if nx and key in self._data:
            return False

        self._data[key] = value
        if ex:
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=ex)
        return True

    async def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set a value with expiration."""
        return await self.set(key, value, ex=seconds)

    async def delete(self, key: str) -> int:
        """Delete a key."""
        if key in self._data:
            del self._data[key]
            if key in self._expiry:
                del self._expiry[key]
            return 1
        return 0

    async def incr(self, key: str) -> int:
        """Increment a counter."""
        if key not in self._data:
            self._data[key] = 0
        self._data[key] = int(self._data[key]) + 1
        return self._data[key]

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key."""
        if key in self._data:
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=seconds)
            return True
        return False

    async def ping(self) -> bool:
        """Health check."""
        return True

    def clear(self):
        """Clear all data."""
        self._data.clear()
        self._expiry.clear()


class MockAlertManager:
    """Mock Alert Manager for testing."""

    def __init__(self):
        self.alerts: list[dict] = []

    async def send(
        self,
        level: str,
        category: str,
        title: str,
        message: str,
        metadata: dict | None = None,
    ) -> bool:
        """Record alert for testing."""
        self.alerts.append({
            "level": level,
            "category": category,
            "title": title,
            "message": message,
            "metadata": metadata,
            "timestamp": datetime.utcnow(),
        })
        return True

    async def auth_failure(self, reason: str, **kwargs) -> bool:
        return await self.send("warning", "security", "Auth Failure", reason, kwargs)

    async def device_sync_error(self, device_id: str, error: str) -> bool:
        return await self.send("warning", "system", "Sync Error", error, {"device_id": device_id})

    async def system_error(self, error: str, **kwargs) -> bool:
        return await self.send("critical", "system", "System Error", error, kwargs)

    async def rate_limit_exceeded(self, identifier: str, endpoint: str, limit: int) -> bool:
        return await self.send("notice", "security", "Rate Limit", f"{identifier} on {endpoint}", {"limit": limit})

    def get_alerts(self, level: str | None = None) -> list[dict]:
        """Get recorded alerts, optionally filtered by level."""
        if level:
            return [a for a in self.alerts if a["level"] == level]
        return self.alerts

    def clear(self):
        """Clear recorded alerts."""
        self.alerts.clear()
