"""
JWT token creation and validation.
Issues API tokens after Firebase authentication.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.config import get_settings


class TokenType:
    """Token type constants."""
    ACCESS = "access"
    REFRESH = "refresh"


def create_access_token(
    user_id: str,
    email: str,
    system_role: str,
    org_memberships: list[dict[str, str]] | None = None,
) -> tuple[str, datetime]:
    """
    Create an access token (short-lived JWT).

    Args:
        user_id: Internal user ID (usr_xxx)
        email: User's email
        system_role: System role (admin/user)
        org_memberships: List of {id, role} for org memberships

    Returns:
        Tuple of (token, expiration_datetime)
    """
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )

    payload = {
        "sub": user_id,
        "type": "user",
        "email": email,
        "role": system_role,
        "orgs": org_memberships or [],
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
        "iss": settings.jwt_issuer,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return token, expires_at


def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    """
    Create a refresh token (longer-lived, opaque).

    Args:
        user_id: Internal user ID

    Returns:
        Tuple of (token, expiration_datetime)
    """
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )

    # Refresh tokens are opaque with embedded claims
    payload = {
        "sub": user_id,
        "type": TokenType.REFRESH,
        "jti": secrets.token_urlsafe(16),  # Unique token ID
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
        "iss": settings.jwt_issuer,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return token, expires_at


def create_device_token(
    device_id: str,
    org_id: str,
    permissions: list[str] | None = None,
) -> tuple[str, datetime]:
    """
    Create a device token after successful RSA authentication.

    Args:
        device_id: Device ID (dev_xxx)
        org_id: Organization ID the device belongs to
        permissions: List of permission strings

    Returns:
        Tuple of (token, expiration_datetime)
    """
    settings = get_settings()
    # Device tokens last 24 hours
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    payload = {
        "sub": device_id,
        "type": "device",
        "org_id": org_id,
        "permissions": permissions or ["sync:write", "telemetry:write"],
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
        "iss": settings.jwt_issuer,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return token, expires_at


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token string

    Returns:
        Decoded token payload

    Raises:
        ValueError: If token is invalid or expired
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


def verify_access_token(token: str) -> dict[str, Any]:
    """
    Verify an access token specifically.

    Args:
        token: The JWT access token

    Returns:
        Decoded payload with user info

    Raises:
        ValueError: If token is invalid, expired, or wrong type
    """
    payload = decode_token(token)

    # Ensure it's an access token (not refresh)
    token_type = payload.get("type")
    if token_type == TokenType.REFRESH:
        raise ValueError("Cannot use refresh token for API access")

    return payload


def verify_refresh_token(token: str) -> dict[str, Any]:
    """
    Verify a refresh token specifically.

    Args:
        token: The JWT refresh token

    Returns:
        Decoded payload with user_id

    Raises:
        ValueError: If token is invalid, expired, or wrong type
    """
    payload = decode_token(token)

    if payload.get("type") != TokenType.REFRESH:
        raise ValueError("Invalid refresh token")

    return payload


def verify_device_token(token: str) -> dict[str, Any]:
    """
    Verify a device token specifically.

    Args:
        token: The JWT device token

    Returns:
        Decoded payload with device info

    Raises:
        ValueError: If token is invalid or wrong type
    """
    payload = decode_token(token)

    if payload.get("type") != "device":
        raise ValueError("Invalid device token")

    return payload
