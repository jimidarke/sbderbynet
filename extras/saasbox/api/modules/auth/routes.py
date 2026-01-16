"""
Authentication routes.
Handles Firebase token exchange, refresh, and logout.
"""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import RateLimitAuth, AuthenticationError
from middleware.logging import alert_manager
from modules.auth.firebase import verify_firebase_token
from modules.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from schemas.common import ErrorCodes


settings = get_settings()
router = APIRouter()


# Request/Response schemas
class FirebaseVerifyRequest(BaseModel):
    """Request to exchange Firebase ID token for API tokens."""
    id_token: str = Field(..., description="Firebase ID token from client")


class TokenResponse(BaseModel):
    """Response containing API tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: datetime
    user: "UserResponse"


class UserResponse(BaseModel):
    """User information in token response."""
    id: str
    email: str
    display_name: str | None
    role: str
    organizations: list[dict]


class RefreshRequest(BaseModel):
    """Request to refresh access token."""
    refresh_token: str


class RefreshResponse(BaseModel):
    """Response with new access token."""
    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime


@router.post("/firebase/verify", response_model=TokenResponse)
async def verify_firebase(
    request: Request,
    body: FirebaseVerifyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _rate_limit: RateLimitAuth,
) -> TokenResponse:
    """
    Exchange a Firebase ID token for API access and refresh tokens.

    This endpoint:
    1. Verifies the Firebase ID token
    2. Creates or updates the user in the database
    3. Records consent timestamp
    4. Issues API JWT tokens

    Only Google sign-in is currently supported.
    """
    # Verify Firebase token
    try:
        firebase_user = await verify_firebase_token(body.id_token)
    except ValueError as e:
        await alert_manager.auth_failure(
            reason=str(e),
            ip_address=request.client.host,
        )
        raise AuthenticationError(
            detail=str(e),
            code=ErrorCodes.AUTH_INVALID_TOKEN,
        )

    # Import here to avoid circular imports
    from models.user import User, UserConsent, SystemRole

    # Find or create user
    stmt = select(User).where(User.firebase_uid == firebase_user["uid"])
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        # Create new user
        user = User(
            firebase_uid=firebase_user["uid"],
            email=firebase_user["email"],
            display_name=firebase_user.get("name"),
            avatar_url=firebase_user.get("picture"),
            system_role=SystemRole.USER,
            consented_at=datetime.utcnow(),
            privacy_version="1.0",
            last_login_at=datetime.utcnow(),
            last_login_ip=request.client.host,
        )
        db.add(user)
        # Flush to get the user ID before creating consent
        await db.flush()

        # Record initial consent
        consent = UserConsent(
            user_id=user.id,
            consent_type="privacy_policy",
            policy_version="1.0",
            consented_at=datetime.utcnow(),
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
        )
        db.add(consent)
    else:
        # Update existing user
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = request.client.host
        if firebase_user.get("name"):
            user.display_name = firebase_user["name"]
        if firebase_user.get("picture"):
            user.avatar_url = firebase_user["picture"]

    await db.commit()
    await db.refresh(user)

    # Get organization memberships
    from models.organization import OrganizationMember

    stmt = select(OrganizationMember).where(
        OrganizationMember.user_id == user.id,
        OrganizationMember.is_active == True,
    )
    result = await db.execute(stmt)
    memberships = result.scalars().all()

    org_list = [
        {"id": m.org_id, "role": m.role.value}
        for m in memberships
    ]

    # Create tokens
    access_token, expires_at = create_access_token(
        user_id=user.id,
        email=user.email,
        system_role=user.system_role.value,
        org_memberships=org_list,
    )
    refresh_token, _ = create_refresh_token(user_id=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        user=UserResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.system_role.value,
            organizations=org_list,
        ),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_access_token(
    request: Request,
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _rate_limit: RateLimitAuth,
) -> RefreshResponse:
    """
    Refresh an access token using a refresh token.
    """
    # Verify refresh token
    try:
        payload = verify_refresh_token(body.refresh_token)
    except ValueError as e:
        raise AuthenticationError(
            detail=str(e),
            code=ErrorCodes.AUTH_EXPIRED_TOKEN,
        )

    user_id = payload["sub"]

    # Verify user still exists and is active
    from models.user import User

    stmt = select(User).where(User.id == user_id, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError(
            detail="User not found or inactive",
            code=ErrorCodes.AUTH_INVALID_TOKEN,
        )

    if user.banned_at is not None:
        raise AuthenticationError(
            detail="User has been banned",
            code=ErrorCodes.AUTH_INVALID_TOKEN,
        )

    # Get current org memberships
    from models.organization import OrganizationMember

    stmt = select(OrganizationMember).where(
        OrganizationMember.user_id == user.id,
        OrganizationMember.is_active == True,
    )
    result = await db.execute(stmt)
    memberships = result.scalars().all()

    org_list = [
        {"id": m.org_id, "role": m.role.value}
        for m in memberships
    ]

    # Create new access token
    access_token, expires_at = create_access_token(
        user_id=user.id,
        email=user.email,
        system_role=user.system_role.value,
        org_memberships=org_list,
    )

    return RefreshResponse(
        access_token=access_token,
        expires_at=expires_at,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
) -> None:
    """
    Log out the current user.

    Note: This endpoint is primarily for client-side cleanup.
    JWTs cannot be truly invalidated server-side without a blocklist.
    The client should discard tokens on logout.
    """
    # In a production system, you might want to:
    # 1. Add the token to a Redis blocklist
    # 2. Revoke Firebase tokens for complete logout
    # For now, this is a no-op - client handles token cleanup
    pass


@router.get("/me")
async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Get the current authenticated user's information.

    Requires: Bearer token in Authorization header
    """
    # This would typically use a dependency to extract user from token
    # For now, return a placeholder - implement with proper auth dependency
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Implement with auth dependency",
    )
