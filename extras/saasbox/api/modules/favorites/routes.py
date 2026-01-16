"""
Favorites routes - User favorite racers for notifications.

All routes require authentication.
Routes are mounted at /v1/me/favorites
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.dependencies import AuthenticationError, NotFoundError
from modules.auth.jwt_handler import verify_access_token
from modules.favorites.schemas import (
    FavoriteCreate,
    FavoriteUpdate,
    FavoriteResponse,
    FavoriteListResponse,
    RacerInfo,
)
from schemas.common import APIResponse, ErrorCodes


router = APIRouter()


async def get_current_user_id(
    authorization: str | None = Header(default=None),
) -> str:
    """
    Extract and verify user ID from Authorization header.

    Returns the user ID from the JWT token.
    Raises AuthenticationError if token is invalid or missing.
    """
    if not authorization:
        raise AuthenticationError(
            detail="Authorization header required",
            code=ErrorCodes.AUTH_MISSING_TOKEN,
        )

    if not authorization.startswith("Bearer "):
        raise AuthenticationError(
            detail="Invalid authorization header format",
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

    return payload["sub"]


# Type alias for current user dependency
CurrentUser = Annotated[str, Depends(get_current_user_id)]


def _build_racer_info(racer) -> RacerInfo:
    """Build RacerInfo from a Racer model instance."""
    return RacerInfo(
        id=racer.id,
        first_name=racer.first_name,
        last_name=racer.last_name,
        car_number=racer.car_number,
        car_name=racer.car_name,
        class_name=racer.racer_class.name if racer.racer_class else None,
        event_id=racer.event_id,
        event_name=racer.event.name if racer.event else None,
    )


@router.get("", response_model=APIResponse[list[FavoriteListResponse]])
async def list_favorites(
    user_id: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[list[FavoriteListResponse]]:
    """
    List all favorite racers for the current user.

    Returns favorites with racer details and notification settings.
    """
    from models.engagement import UserFavorite
    from models.racer import Racer

    stmt = (
        select(UserFavorite)
        .where(UserFavorite.user_id == user_id)
        .options(
            joinedload(UserFavorite.racer).joinedload(Racer.racer_class),
            joinedload(UserFavorite.racer).joinedload(Racer.event),
        )
        .order_by(UserFavorite.created_at.desc())
    )
    result = await db.execute(stmt)
    favorites = result.scalars().unique().all()

    response_data = [
        FavoriteListResponse(
            id=fav.id,
            racer_id=fav.racer_id,
            racer=_build_racer_info(fav.racer),
            notify_upcoming=fav.notify_upcoming,
            notify_results=fav.notify_results,
            created_at=fav.created_at,
        )
        for fav in favorites
    ]

    return APIResponse(data=response_data)


@router.post("", response_model=APIResponse[FavoriteResponse], status_code=status.HTTP_201_CREATED)
async def add_favorite(
    body: FavoriteCreate,
    user_id: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[FavoriteResponse]:
    """
    Add a racer to the user's favorites.

    The racer must exist. Duplicate favorites return 409 Conflict.
    """
    from models.engagement import UserFavorite
    from models.racer import Racer

    # Verify racer exists
    stmt = (
        select(Racer)
        .where(Racer.id == body.racer_id)
        .options(
            joinedload(Racer.racer_class),
            joinedload(Racer.event),
        )
    )
    result = await db.execute(stmt)
    racer = result.scalar_one_or_none()

    if racer is None:
        raise NotFoundError(resource="Racer")

    # Check if already favorited
    existing_stmt = select(UserFavorite).where(
        UserFavorite.user_id == user_id,
        UserFavorite.racer_id == body.racer_id,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": ErrorCodes.VAL_DUPLICATE_ENTRY,
                "message": "Racer is already in favorites",
            },
        )

    # Create favorite
    favorite = UserFavorite(
        user_id=user_id,
        racer_id=body.racer_id,
        notify_upcoming=body.notify_upcoming,
        notify_results=body.notify_results,
    )
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)

    return APIResponse(
        data=FavoriteResponse(
            id=favorite.id,
            racer_id=favorite.racer_id,
            racer=_build_racer_info(racer),
            notify_upcoming=favorite.notify_upcoming,
            notify_results=favorite.notify_results,
            created_at=favorite.created_at,
        )
    )


@router.patch("/{racer_id}", response_model=APIResponse[FavoriteResponse])
async def update_favorite(
    racer_id: str,
    body: FavoriteUpdate,
    user_id: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[FavoriteResponse]:
    """
    Update notification settings for a favorite racer.
    """
    from models.engagement import UserFavorite
    from models.racer import Racer

    stmt = (
        select(UserFavorite)
        .where(
            UserFavorite.user_id == user_id,
            UserFavorite.racer_id == racer_id,
        )
        .options(
            joinedload(UserFavorite.racer).joinedload(Racer.racer_class),
            joinedload(UserFavorite.racer).joinedload(Racer.event),
        )
    )
    result = await db.execute(stmt)
    favorite = result.scalar_one_or_none()

    if favorite is None:
        raise NotFoundError(resource="Favorite")

    # Update fields
    if body.notify_upcoming is not None:
        favorite.notify_upcoming = body.notify_upcoming
    if body.notify_results is not None:
        favorite.notify_results = body.notify_results

    await db.commit()
    await db.refresh(favorite)

    return APIResponse(
        data=FavoriteResponse(
            id=favorite.id,
            racer_id=favorite.racer_id,
            racer=_build_racer_info(favorite.racer),
            notify_upcoming=favorite.notify_upcoming,
            notify_results=favorite.notify_results,
            created_at=favorite.created_at,
        )
    )


@router.delete("/{racer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    racer_id: str,
    user_id: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Remove a racer from the user's favorites.
    """
    from models.engagement import UserFavorite

    stmt = select(UserFavorite).where(
        UserFavorite.user_id == user_id,
        UserFavorite.racer_id == racer_id,
    )
    result = await db.execute(stmt)
    favorite = result.scalar_one_or_none()

    if favorite is None:
        raise NotFoundError(resource="Favorite")

    await db.delete(favorite)
    await db.commit()


@router.get("/count", response_model=APIResponse[dict])
async def get_favorites_count(
    user_id: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[dict]:
    """
    Get count of favorite racers for the current user.
    """
    from models.engagement import UserFavorite

    stmt = select(func.count(UserFavorite.id)).where(UserFavorite.user_id == user_id)
    result = await db.execute(stmt)
    count = result.scalar()

    return APIResponse(data={"count": count})
