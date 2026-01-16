"""
FastAPI dependencies for authentication, authorization, and tenant context.
"""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, get_tenant_db
from app.redis_client import RateLimiter
from middleware.logging import alert_manager
from schemas.common import ErrorCodes


settings = get_settings()


# Type aliases for dependencies
DBSession = Annotated[AsyncSession, Depends(get_db)]


class AuthenticationError(HTTPException):
    """Authentication failed."""

    def __init__(self, detail: str, code: str = ErrorCodes.AUTH_INVALID_TOKEN):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": code, "message": detail},
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Authorization failed."""

    def __init__(self, detail: str, code: str = ErrorCodes.AUTHZ_FORBIDDEN):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": code, "message": detail},
        )


class NotFoundError(HTTPException):
    """Resource not found."""

    def __init__(self, resource: str, code: str = ErrorCodes.NOT_FOUND):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": code, "message": f"{resource} not found"},
        )


class RateLimitError(HTTPException):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": ErrorCodes.RATE_LIMIT_EXCEEDED,
                "message": "Rate limit exceeded",
            },
            headers={"Retry-After": str(retry_after)},
        )


async def rate_limit_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    """
    Rate limiting for authenticated user requests.
    100 requests per minute per user.
    """
    # Extract user identifier from token or IP
    if authorization and authorization.startswith("Bearer "):
        # Use user ID from token (will be extracted by auth dependency)
        identifier = f"user:{request.state.user_id}" if hasattr(request.state, "user_id") else f"ip:{request.client.host}"
    else:
        identifier = f"ip:{request.client.host}"

    allowed, remaining = await RateLimiter.check(
        identifier=identifier,
        limit=settings.rate_limit_user_per_minute,
        window_seconds=60,
    )

    if not allowed:
        await alert_manager.rate_limit_exceeded(
            identifier=identifier,
            endpoint=str(request.url.path),
            limit=settings.rate_limit_user_per_minute,
        )
        raise RateLimitError()

    # Add remaining count to request state for response header
    request.state.rate_limit_remaining = remaining


async def rate_limit_device(
    request: Request,
    x_device_id: str = Header(...),
) -> None:
    """
    Rate limiting for device requests.
    1000 requests per minute per device.
    """
    identifier = f"device:{x_device_id}"

    allowed, remaining = await RateLimiter.check(
        identifier=identifier,
        limit=settings.rate_limit_device_per_minute,
        window_seconds=60,
    )

    if not allowed:
        await alert_manager.rate_limit_exceeded(
            identifier=identifier,
            endpoint=str(request.url.path),
            limit=settings.rate_limit_device_per_minute,
        )
        raise RateLimitError()

    request.state.rate_limit_remaining = remaining


async def rate_limit_auth(request: Request) -> None:
    """
    Stricter rate limiting for authentication endpoints.
    20 requests per minute per IP.
    """
    identifier = f"auth:{request.client.host}"

    allowed, remaining = await RateLimiter.check(
        identifier=identifier,
        limit=settings.rate_limit_auth_per_minute,
        window_seconds=60,
    )

    if not allowed:
        await alert_manager.rate_limit_exceeded(
            identifier=identifier,
            endpoint=str(request.url.path),
            limit=settings.rate_limit_auth_per_minute,
        )
        raise RateLimitError()


# Dependency types
RateLimitUser = Annotated[None, Depends(rate_limit_user)]
RateLimitDevice = Annotated[None, Depends(rate_limit_device)]
RateLimitAuth = Annotated[None, Depends(rate_limit_auth)]
