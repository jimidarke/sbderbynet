"""
Authentication dependencies for protecting routes.
"""
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import AuthenticationError, AuthorizationError
from modules.auth.jwt_handler import verify_access_token, verify_device_token
from modules.auth.device_auth import verify_device_signature, DeviceSignatureError
from schemas.common import ErrorCodes


class CurrentUser:
    """Represents the currently authenticated user."""

    def __init__(
        self,
        user_id: str,
        email: str,
        system_role: str,
        org_memberships: list[dict],
    ):
        self.user_id = user_id
        self.email = email
        self.system_role = system_role
        self.org_memberships = org_memberships

    @property
    def is_system_admin(self) -> bool:
        return self.system_role == "admin"

    def is_org_member(self, org_id: str) -> bool:
        """Check if user is a member of the organization."""
        return any(m["id"] == org_id for m in self.org_memberships)

    def is_org_admin(self, org_id: str) -> bool:
        """Check if user is an admin of the organization."""
        for m in self.org_memberships:
            if m["id"] == org_id and m["role"] in ("owner", "admin"):
                return True
        return False

    def get_org_role(self, org_id: str) -> str | None:
        """Get user's role in an organization."""
        for m in self.org_memberships:
            if m["id"] == org_id:
                return m["role"]
        return None


class CurrentDevice:
    """Represents the currently authenticated device."""

    def __init__(
        self,
        device_id: str,
        org_id: str,
        permissions: list[str],
    ):
        self.device_id = device_id
        self.org_id = org_id
        self.permissions = permissions

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    """
    Dependency to get the current authenticated user from JWT token.

    Usage:
        @router.get("/me")
        async def get_me(user: CurrentUser = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    if not authorization:
        raise AuthenticationError(
            detail="Missing Authorization header",
            code=ErrorCodes.AUTH_INVALID_TOKEN,
        )

    if not authorization.startswith("Bearer "):
        raise AuthenticationError(
            detail="Invalid Authorization header format. Use 'Bearer <token>'",
            code=ErrorCodes.AUTH_INVALID_TOKEN,
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        payload = verify_access_token(token)
    except ValueError as e:
        raise AuthenticationError(
            detail=str(e),
            code=ErrorCodes.AUTH_INVALID_TOKEN,
        )

    # Store user info in request state for logging
    request.state.user_id = payload["sub"]

    return CurrentUser(
        user_id=payload["sub"],
        email=payload.get("email", ""),
        system_role=payload.get("role", "user"),
        org_memberships=payload.get("orgs", []),
    )


async def get_current_user_optional(
    request: Request,
    authorization: str | None = Header(default=None),
) -> CurrentUser | None:
    """
    Dependency to optionally get the current user.
    Returns None if no valid token is provided.

    Use for endpoints that work for both authenticated and anonymous users.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]

    try:
        payload = verify_access_token(token)
        request.state.user_id = payload["sub"]
        return CurrentUser(
            user_id=payload["sub"],
            email=payload.get("email", ""),
            system_role=payload.get("role", "user"),
            org_memberships=payload.get("orgs", []),
        )
    except ValueError:
        return None


async def get_current_device(
    request: Request,
    x_device_id: str = Header(...),
    x_timestamp: int = Header(...),
    x_nonce: str = Header(...),
    x_signature: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> CurrentDevice:
    """
    Dependency to authenticate a device using RSA signature.

    Usage:
        @router.post("/sync")
        async def sync_data(device: CurrentDevice = Depends(get_current_device)):
            return {"device_id": device.device_id}
    """
    from models.device import Device, DeviceStatus

    # Look up device
    stmt = select(Device).where(
        Device.id == x_device_id,
        Device.status.in_([DeviceStatus.ACTIVE, DeviceStatus.PENDING]),
    )
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()

    if device is None:
        raise AuthenticationError(
            detail="Device not registered or revoked",
            code=ErrorCodes.AUTH_DEVICE_NOT_REGISTERED,
        )

    # Get request body for signature verification
    body = await request.body()

    # Verify signature
    try:
        await verify_device_signature(
            public_key_pem=device.public_key,
            device_id=x_device_id,
            timestamp=x_timestamp,
            nonce=x_nonce,
            signature_b64=x_signature,
            method=request.method,
            path=request.url.path,
            body=body if body else None,
        )
    except DeviceSignatureError as e:
        raise AuthenticationError(
            detail=str(e),
            code=ErrorCodes.AUTH_INVALID_SIGNATURE,
        )

    # Update last seen
    from datetime import datetime
    device.last_seen_at = datetime.utcnow()
    device.last_ip = request.client.host
    await db.commit()

    return CurrentDevice(
        device_id=device.id,
        org_id=device.org_id,
        permissions=["sync:write", "telemetry:write"],
    )


def require_org_member(org_id_param: str = "org_id"):
    """
    Dependency factory to require user is a member of the organization.

    Usage:
        @router.get("/orgs/{org_id}/events")
        async def list_events(
            org_id: str,
            user: CurrentUser = Depends(get_current_user),
            _: None = Depends(require_org_member()),
        ):
            ...
    """
    async def dependency(
        request: Request,
        user: CurrentUser = Depends(get_current_user),
    ) -> None:
        org_id = request.path_params.get(org_id_param)
        if not org_id:
            raise AuthorizationError(
                detail="Organization ID not found in path",
                code=ErrorCodes.AUTHZ_FORBIDDEN,
            )

        # System admins can access any org
        if user.is_system_admin:
            return

        if not user.is_org_member(org_id):
            raise AuthorizationError(
                detail="You are not a member of this organization",
                code=ErrorCodes.AUTHZ_NOT_ORG_MEMBER,
            )

    return dependency


def require_org_admin(org_id_param: str = "org_id"):
    """
    Dependency factory to require user is an admin of the organization.
    """
    async def dependency(
        request: Request,
        user: CurrentUser = Depends(get_current_user),
    ) -> None:
        org_id = request.path_params.get(org_id_param)
        if not org_id:
            raise AuthorizationError(
                detail="Organization ID not found in path",
                code=ErrorCodes.AUTHZ_FORBIDDEN,
            )

        # System admins can access any org
        if user.is_system_admin:
            return

        if not user.is_org_admin(org_id):
            raise AuthorizationError(
                detail="You must be an organization admin",
                code=ErrorCodes.AUTHZ_NOT_ORG_ADMIN,
            )

    return dependency


def require_system_admin():
    """
    Dependency to require user is a system admin.
    """
    async def dependency(
        user: CurrentUser = Depends(get_current_user),
    ) -> None:
        if not user.is_system_admin:
            raise AuthorizationError(
                detail="System administrator access required",
                code=ErrorCodes.AUTHZ_NOT_SYSTEM_ADMIN,
            )

    return dependency


# Type aliases for cleaner route signatures
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
OptionalUser = Annotated[CurrentUser | None, Depends(get_current_user_optional)]
AuthenticatedDevice = Annotated[CurrentDevice, Depends(get_current_device)]
