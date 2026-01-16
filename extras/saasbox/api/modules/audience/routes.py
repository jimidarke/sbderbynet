"""
Audience Participation Module - Predictions, Cheers, and Polls.

This module provides interactive engagement features for derby event spectators,
enabling them to participate beyond just watching races.

## Base URL

All routes are mounted at:
`/v1/orgs/{org_id}/events/{event_id}/audience`

## Features Overview

### Predictions
Let users predict heat winners before races start. Points are awarded for
correct predictions, and a leaderboard tracks top predictors.

### Cheers
Allow spectators to send "cheers" to their favorite racers. Rate-limited
to prevent spam while enabling meaningful support.

### Polls
Interactive voting for categories like "Best Looking Car" or "Fan Favorite".
One vote per user per poll, with results hidden until voting or poll close.

## Authentication Patterns

| Feature | List/View | Participate |
|---------|-----------|-------------|
| Predictions | Public | Requires auth |
| Cheers | Public | Requires auth |
| Polls | Public | Requires auth |

All participation actions require authentication to ensure one-action-per-user
integrity and to track user engagement.

## Common Use Cases

1. **Race Day Engagement**: Spectators make predictions before each heat
2. **Award Voting**: "Best Looking Car" poll during inspection period
3. **Fan Support**: Cheers accumulate to show racer popularity
4. **Leaderboards**: Competition among spectators for prediction accuracy
"""
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.dependencies import AuthenticationError, NotFoundError
from modules.auth.jwt_handler import verify_access_token
from modules.audience.schemas import (
    PredictionCreate,
    PredictionResponse,
    PredictionListResponse,
    LeaderboardEntry,
    LeaderboardResponse,
    PredictionStats,
    UpcomingHeatForPrediction,
    RacerBrief,
    HeatBrief,
    # Cheer schemas
    CheerResponse,
    CheerCountResponse,
    RacerCheerStats,
    EventCheerLeaderboard,
    UserCheerStatus,
    # Poll schemas
    PollOptionSchema,
    PollOptionWithVotes,
    PollResponse,
    PollListResponse,
    PollVoteCreate,
    PollVoteResponse,
    PollResultsResponse,
)
from schemas.common import APIResponse, ErrorCodes


router = APIRouter()


async def get_current_user_id(
    authorization: str | None = Header(default=None),
) -> str:
    """Extract and verify user ID from Authorization header."""
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

    token = authorization[7:]

    try:
        payload = verify_access_token(token)
    except ValueError as e:
        raise AuthenticationError(
            detail=str(e),
            code=ErrorCodes.AUTH_INVALID_TOKEN,
        )

    return payload["sub"]


async def get_optional_user_id(
    authorization: str | None = Header(default=None),
) -> str | None:
    """Optionally extract user ID - returns None if not authenticated."""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    try:
        payload = verify_access_token(authorization[7:])
        return payload["sub"]
    except ValueError:
        return None


CurrentUser = Annotated[str, Depends(get_current_user_id)]
OptionalUser = Annotated[str | None, Depends(get_optional_user_id)]


async def verify_event_access(
    org_id: str,
    event_id: str,
    db: AsyncSession,
) -> "Event":
    """Verify event exists and belongs to organization."""
    from models.event import Event

    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
        Event.deleted_at == None,
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise NotFoundError(resource="Event")

    return event


def _build_racer_brief(racer) -> RacerBrief:
    """Build RacerBrief from model."""
    return RacerBrief(
        id=racer.id,
        first_name=racer.first_name,
        last_name=racer.last_name,
        car_number=racer.car_number,
        car_name=racer.car_name,
    )


def _build_heat_brief(heat) -> HeatBrief:
    """Build HeatBrief from model."""
    return HeatBrief(
        id=heat.id,
        heat_number=heat.heat_number,
        round_name=heat.round.name if heat.round else None,
        status=heat.status.value,
    )


# =============================================================================
# Prediction Endpoints
# =============================================================================

@router.post("/predictions", response_model=APIResponse[PredictionResponse], status_code=status.HTTP_201_CREATED)
async def create_prediction(
    org_id: Annotated[str, Path()],
    event_id: Annotated[str, Path()],
    body: PredictionCreate,
    user_id: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[PredictionResponse]:
    """
    Submit a prediction for a heat.

    The racer must be participating in the heat.
    Only one prediction per user per heat is allowed.
    Predictions may be blocked after a cutoff time before the heat starts.
    """
    from models.engagement import Prediction
    from models.race import Heat, RaceResult, HeatStatus
    from models.racer import Racer

    # Verify event exists
    event = await verify_event_access(org_id, event_id, db)

    # Check if predictions are allowed
    if not event.settings.get("allow_predictions", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": ErrorCodes.AUTHZ_FORBIDDEN,
                "message": "Predictions are not allowed for this event",
            },
        )

    # Verify heat exists and belongs to event
    stmt = (
        select(Heat)
        .join(Heat.round)
        .where(
            Heat.id == body.heat_id,
            Heat.round.has(event_id=event_id),
        )
        .options(joinedload(Heat.round))
    )
    result = await db.execute(stmt)
    heat = result.scalar_one_or_none()

    if heat is None:
        raise NotFoundError(resource="Heat")

    # Check if heat is already started/finished
    if heat.status in (HeatStatus.RACING, HeatStatus.FINISHED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": ErrorCodes.VAL_INVALID_INPUT,
                "message": "Cannot predict for a heat that has already started",
            },
        )

    # Verify racer exists and is in this heat
    stmt = select(RaceResult).where(
        RaceResult.heat_id == body.heat_id,
        RaceResult.racer_id == body.predicted_racer_id,
    )
    result = await db.execute(stmt)
    race_entry = result.scalar_one_or_none()

    if race_entry is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": ErrorCodes.VAL_INVALID_INPUT,
                "message": "Racer is not participating in this heat",
            },
        )

    # Check for existing prediction
    stmt = select(Prediction).where(
        Prediction.user_id == user_id,
        Prediction.heat_id == body.heat_id,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": ErrorCodes.VAL_DUPLICATE_ENTRY,
                "message": "You have already made a prediction for this heat",
            },
        )

    # Get racer details
    stmt = select(Racer).where(Racer.id == body.predicted_racer_id)
    result = await db.execute(stmt)
    racer = result.scalar_one()

    # Create prediction
    prediction = Prediction(
        user_id=user_id,
        heat_id=body.heat_id,
        predicted_racer_id=body.predicted_racer_id,
    )
    db.add(prediction)
    await db.commit()
    await db.refresh(prediction)

    return APIResponse(
        data=PredictionResponse(
            id=prediction.id,
            heat_id=prediction.heat_id,
            heat=_build_heat_brief(heat),
            predicted_racer_id=prediction.predicted_racer_id,
            predicted_racer=_build_racer_brief(racer),
            is_correct=prediction.is_correct,
            points_earned=prediction.points_earned,
            created_at=prediction.created_at,
        )
    )


@router.get("/predictions", response_model=APIResponse[list[PredictionListResponse]])
async def list_predictions(
    org_id: Annotated[str, Path()],
    event_id: Annotated[str, Path()],
    user_id: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[list[PredictionListResponse]]:
    """
    List the current user's predictions for an event.
    """
    from models.engagement import Prediction
    from models.race import Heat, Round
    from models.racer import Racer

    # Verify event exists
    await verify_event_access(org_id, event_id, db)

    # Get predictions for this user and event
    stmt = (
        select(Prediction)
        .join(Heat, Prediction.heat_id == Heat.id)
        .join(Round, Heat.round_id == Round.id)
        .where(
            Prediction.user_id == user_id,
            Round.event_id == event_id,
        )
        .options(
            joinedload(Prediction.heat).joinedload(Heat.round),
            joinedload(Prediction.predicted_racer),
        )
        .order_by(Prediction.created_at.desc())
    )
    result = await db.execute(stmt)
    predictions = result.scalars().unique().all()

    response_data = [
        PredictionListResponse(
            id=p.id,
            heat_id=p.heat_id,
            heat_number=p.heat.heat_number,
            round_name=p.heat.round.name if p.heat.round else None,
            predicted_racer=_build_racer_brief(p.predicted_racer),
            is_correct=p.is_correct,
            points_earned=p.points_earned,
            created_at=p.created_at,
        )
        for p in predictions
    ]

    return APIResponse(data=response_data)


@router.get("/predictions/leaderboard", response_model=APIResponse[LeaderboardResponse])
async def get_leaderboard(
    org_id: Annotated[str, Path()],
    event_id: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=100),
) -> APIResponse[LeaderboardResponse]:
    """
    Get the prediction leaderboard for an event.

    Public endpoint - no authentication required.
    """
    from models.engagement import Prediction
    from models.race import Heat, Round
    from models.user import User

    # Verify event exists
    event = await verify_event_access(org_id, event_id, db)

    # Build subquery to get predictions for this event
    event_predictions = (
        select(
            Prediction.user_id,
            func.count(Prediction.id).label("total_predictions"),
            func.sum(case((Prediction.is_correct == True, 1), else_=0)).label("correct_predictions"),
            func.sum(Prediction.points_earned).label("total_points"),
        )
        .join(Heat, Prediction.heat_id == Heat.id)
        .join(Round, Heat.round_id == Round.id)
        .where(Round.event_id == event_id)
        .group_by(Prediction.user_id)
        .subquery()
    )

    # Get leaderboard with user info
    stmt = (
        select(
            User.id,
            User.display_name,
            event_predictions.c.total_predictions,
            event_predictions.c.correct_predictions,
            event_predictions.c.total_points,
        )
        .join(event_predictions, User.id == event_predictions.c.user_id)
        .order_by(event_predictions.c.total_points.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    entries = []
    for rank, row in enumerate(rows, 1):
        total = row.total_predictions or 0
        correct = row.correct_predictions or 0
        accuracy = (correct / total * 100) if total > 0 else 0.0

        entries.append(
            LeaderboardEntry(
                rank=rank,
                user_id=row.id,
                display_name=row.display_name,
                total_predictions=total,
                correct_predictions=correct,
                total_points=row.total_points or 0,
                accuracy_percent=round(accuracy, 1),
            )
        )

    # Get total participants count
    count_stmt = (
        select(func.count(func.distinct(Prediction.user_id)))
        .join(Heat, Prediction.heat_id == Heat.id)
        .join(Round, Heat.round_id == Round.id)
        .where(Round.event_id == event_id)
    )
    count_result = await db.execute(count_stmt)
    total_participants = count_result.scalar() or 0

    return APIResponse(
        data=LeaderboardResponse(
            event_id=event.id,
            event_name=event.name,
            total_participants=total_participants,
            entries=entries,
        )
    )


@router.get("/predictions/stats", response_model=APIResponse[PredictionStats])
async def get_prediction_stats(
    org_id: Annotated[str, Path()],
    event_id: Annotated[str, Path()],
    user_id: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[PredictionStats]:
    """
    Get the current user's prediction statistics for an event.
    """
    from models.engagement import Prediction
    from models.race import Heat, Round

    # Verify event exists
    await verify_event_access(org_id, event_id, db)

    # Get stats for user
    stmt = (
        select(
            func.count(Prediction.id).label("total"),
            func.sum(case((Prediction.is_correct == True, 1), else_=0)).label("correct"),
            func.sum(case((Prediction.is_correct == None, 1), else_=0)).label("pending"),
            func.sum(Prediction.points_earned).label("points"),
        )
        .join(Heat, Prediction.heat_id == Heat.id)
        .join(Round, Heat.round_id == Round.id)
        .where(
            Prediction.user_id == user_id,
            Round.event_id == event_id,
        )
    )
    result = await db.execute(stmt)
    row = result.one()

    total = row.total or 0
    correct = row.correct or 0
    pending = row.pending or 0
    points = row.points or 0
    accuracy = (correct / total * 100) if total > 0 else 0.0

    # Get user's rank
    rank = None
    if total > 0:
        # Count users with more points
        rank_stmt = (
            select(func.count(func.distinct(Prediction.user_id)))
            .join(Heat, Prediction.heat_id == Heat.id)
            .join(Round, Heat.round_id == Round.id)
            .where(Round.event_id == event_id)
            .group_by(Prediction.user_id)
            .having(func.sum(Prediction.points_earned) > points)
        )
        rank_result = await db.execute(select(func.count()).select_from(rank_stmt.subquery()))
        users_above = rank_result.scalar() or 0
        rank = users_above + 1

    return APIResponse(
        data=PredictionStats(
            event_id=event_id,
            total_predictions=total,
            correct_predictions=correct,
            pending_predictions=pending,
            total_points=points,
            accuracy_percent=round(accuracy, 1),
            rank=rank,
        )
    )


@router.get("/predictions/upcoming", response_model=APIResponse[list[UpcomingHeatForPrediction]])
async def get_upcoming_heats(
    org_id: Annotated[str, Path()],
    event_id: Annotated[str, Path()],
    user_id: OptionalUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=5, ge=1, le=20),
) -> APIResponse[list[UpcomingHeatForPrediction]]:
    """
    Get upcoming heats available for prediction.

    Returns heats that haven't started yet, with racer lineups.
    If authenticated, includes whether user has already predicted.
    """
    from models.engagement import Prediction
    from models.race import Heat, Round, RaceResult, HeatStatus
    from models.racer import Racer, RacerClass

    # Verify event exists
    event = await verify_event_access(org_id, event_id, db)

    # Get upcoming heats
    stmt = (
        select(Heat)
        .join(Round, Heat.round_id == Round.id)
        .where(
            Round.event_id == event_id,
            Heat.status == HeatStatus.SCHEDULED,
        )
        .options(
            joinedload(Heat.round).joinedload(Round.racer_class),
            joinedload(Heat.results).joinedload(RaceResult.racer),
        )
        .order_by(Heat.heat_number)
        .limit(limit)
    )
    result = await db.execute(stmt)
    heats = result.scalars().unique().all()

    # Get user's existing predictions for these heats
    user_predictions = set()
    if user_id:
        heat_ids = [h.id for h in heats]
        pred_stmt = select(Prediction.heat_id).where(
            Prediction.user_id == user_id,
            Prediction.heat_id.in_(heat_ids),
        )
        pred_result = await db.execute(pred_stmt)
        user_predictions = {row[0] for row in pred_result.all()}

    # Calculate prediction cutoff time
    cutoff_minutes = event.settings.get("prediction_cutoff_minutes", 5)

    response_data = []
    for heat in heats:
        racers = [
            _build_racer_brief(r.racer)
            for r in heat.results
            if r.racer
        ]

        response_data.append(
            UpcomingHeatForPrediction(
                heat_id=heat.id,
                heat_number=heat.heat_number,
                round_name=heat.round.name if heat.round else "Unknown",
                class_name=heat.round.racer_class.name if heat.round and heat.round.racer_class else None,
                racers=racers,
                prediction_cutoff_at=None,  # Would be set based on actual race schedule
                user_has_predicted=heat.id in user_predictions,
            )
        )

    return APIResponse(data=response_data)


# =============================================================================
# Prediction Resolution (Internal/Admin)
# =============================================================================

async def resolve_heat_predictions(heat_id: str, db: AsyncSession) -> int:
    """
    Resolve predictions for a completed heat.

    Returns the number of predictions resolved.
    Called when a heat finishes.
    """
    from models.engagement import Prediction
    from models.race import Heat, RaceResult

    # Get winning racer (place == 1)
    stmt = select(RaceResult).where(
        RaceResult.heat_id == heat_id,
        RaceResult.finish_place == 1,
    )
    result = await db.execute(stmt)
    winner = result.scalar_one_or_none()

    if winner is None:
        return 0  # No winner determined

    # Get all predictions for this heat
    stmt = select(Prediction).where(
        Prediction.heat_id == heat_id,
        Prediction.is_correct == None,  # Only unresolved
    )
    result = await db.execute(stmt)
    predictions = result.scalars().all()

    resolved_count = 0
    for prediction in predictions:
        prediction.is_correct = prediction.predicted_racer_id == winner.racer_id
        if prediction.is_correct:
            prediction.points_earned = 10  # Base points for correct prediction
        resolved_count += 1

    if resolved_count > 0:
        await db.commit()

    return resolved_count


# =============================================================================
# Cheer Endpoints
# =============================================================================

# Default max cheers per racer per user per event
DEFAULT_MAX_CHEERS = 5


async def verify_racer_in_event(
    racer_id: str,
    event_id: str,
    db: AsyncSession,
) -> "Racer":
    """Verify racer exists and belongs to event."""
    from models.racer import Racer

    stmt = select(Racer).where(
        Racer.id == racer_id,
        Racer.event_id == event_id,
    )
    result = await db.execute(stmt)
    racer = result.scalar_one_or_none()

    if racer is None:
        raise NotFoundError(resource="Racer")

    return racer


@router.post("/cheers/{racer_id}", response_model=APIResponse[CheerResponse], status_code=status.HTTP_201_CREATED)
async def send_cheer(
    org_id: Annotated[str, Path()],
    event_id: Annotated[str, Path()],
    racer_id: Annotated[str, Path()],
    user_id: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[CheerResponse]:
    """
    Send a cheer to a racer.

    Rate limited to max_cheers_per_racer (default 5) cheers per racer per user per event.
    """
    from models.engagement import Cheer
    from models.racer import Racer

    # Verify event exists and get settings
    event = await verify_event_access(org_id, event_id, db)

    # Check if cheers are allowed
    if not event.settings.get("allow_cheers", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": ErrorCodes.AUTHZ_FORBIDDEN,
                "message": "Cheers are not allowed for this event",
            },
        )

    # Verify racer exists and belongs to event
    racer = await verify_racer_in_event(racer_id, event_id, db)

    # Check rate limit
    max_cheers = event.settings.get("max_cheers_per_racer", DEFAULT_MAX_CHEERS)
    stmt = select(func.count(Cheer.id)).where(
        Cheer.user_id == user_id,
        Cheer.racer_id == racer_id,
    )
    result = await db.execute(stmt)
    current_cheers = result.scalar() or 0

    if current_cheers >= max_cheers:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": ErrorCodes.RATE_LIMIT_EXCEEDED,
                "message": f"Maximum cheers ({max_cheers}) reached for this racer",
            },
        )

    # Create cheer
    cheer = Cheer(
        user_id=user_id,
        racer_id=racer_id,
    )
    db.add(cheer)
    await db.commit()
    await db.refresh(cheer)

    return APIResponse(
        data=CheerResponse(
            id=cheer.id,
            racer_id=cheer.racer_id,
            racer=_build_racer_brief(racer),
            created_at=cheer.created_at,
        )
    )


@router.get("/cheers/{racer_id}/status", response_model=APIResponse[UserCheerStatus])
async def get_cheer_status(
    org_id: Annotated[str, Path()],
    event_id: Annotated[str, Path()],
    racer_id: Annotated[str, Path()],
    user_id: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[UserCheerStatus]:
    """
    Get user's cheer status for a racer.

    Shows how many cheers sent and whether more can be sent.
    """
    from models.engagement import Cheer

    # Verify event exists and get settings
    event = await verify_event_access(org_id, event_id, db)

    # Verify racer exists and belongs to event
    await verify_racer_in_event(racer_id, event_id, db)

    # Get current cheer count
    max_cheers = event.settings.get("max_cheers_per_racer", DEFAULT_MAX_CHEERS)
    stmt = select(func.count(Cheer.id)).where(
        Cheer.user_id == user_id,
        Cheer.racer_id == racer_id,
    )
    result = await db.execute(stmt)
    cheers_sent = result.scalar() or 0

    return APIResponse(
        data=UserCheerStatus(
            racer_id=racer_id,
            cheers_sent=cheers_sent,
            max_cheers=max_cheers,
            can_cheer=cheers_sent < max_cheers,
        )
    )


@router.get("/cheers/{racer_id}/count", response_model=APIResponse[CheerCountResponse])
async def get_cheer_count(
    org_id: Annotated[str, Path()],
    event_id: Annotated[str, Path()],
    racer_id: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[CheerCountResponse]:
    """
    Get total cheer count for a racer.

    Public endpoint - no authentication required.
    """
    from models.engagement import Cheer
    from models.racer import Racer

    # Verify event exists
    await verify_event_access(org_id, event_id, db)

    # Verify racer exists and belongs to event
    racer = await verify_racer_in_event(racer_id, event_id, db)

    # Get total cheer count
    stmt = select(func.count(Cheer.id)).where(Cheer.racer_id == racer_id)
    result = await db.execute(stmt)
    cheer_count = result.scalar() or 0

    return APIResponse(
        data=CheerCountResponse(
            racer_id=racer_id,
            racer=_build_racer_brief(racer),
            cheer_count=cheer_count,
        )
    )


@router.get("/cheers/leaderboard", response_model=APIResponse[EventCheerLeaderboard])
async def get_cheer_leaderboard(
    org_id: Annotated[str, Path()],
    event_id: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
) -> APIResponse[EventCheerLeaderboard]:
    """
    Get the cheer leaderboard for an event.

    Shows most-cheered racers. Public endpoint - no authentication required.
    """
    from models.engagement import Cheer
    from models.racer import Racer

    # Verify event exists
    event = await verify_event_access(org_id, event_id, db)

    # Get cheer stats per racer
    stmt = (
        select(
            Racer,
            func.count(Cheer.id).label("total_cheers"),
            func.count(func.distinct(Cheer.user_id)).label("unique_supporters"),
        )
        .outerjoin(Cheer, Cheer.racer_id == Racer.id)
        .where(Racer.event_id == event_id)
        .group_by(Racer.id)
        .order_by(func.count(Cheer.id).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    entries = [
        RacerCheerStats(
            racer_id=row.Racer.id,
            racer=_build_racer_brief(row.Racer),
            total_cheers=row.total_cheers or 0,
            unique_supporters=row.unique_supporters or 0,
        )
        for row in rows
    ]

    return APIResponse(
        data=EventCheerLeaderboard(
            event_id=event.id,
            event_name=event.name,
            entries=entries,
        )
    )


# =============================================================================
# Poll Endpoints
# =============================================================================
#
# POLLS SYSTEM OVERVIEW
# ---------------------
# Polls allow event organizers to gather audience feedback and run interactive
# voting during derby events. Common use cases include:
#
# - "Best Looking Car" - Let spectators vote for their favorite car design
# - "Fan Favorite Racer" - Audience picks their favorite competitor
# - "Most Creative Design" - Vote on car creativity/originality
# - "Best Team Spirit" - Recognize enthusiastic participants
#
# POLL LIFECYCLE
# --------------
# Polls follow a three-stage lifecycle:
#
# 1. DRAFT - Poll is being configured, not visible to users
# 2. ACTIVE - Poll is open for voting (respects opens_at/closes_at times)
# 3. CLOSED - Voting has ended, results are publicly visible
#
# VOTING RULES
# ------------
# - One vote per user per poll (enforced at database level)
# - Users must be authenticated to vote
# - Votes cannot be changed once submitted
# - Time constraints (opens_at, closes_at) are enforced server-side
#
# RESULTS VISIBILITY
# ------------------
# To prevent vote manipulation, results are hidden until:
# - The user has voted (they can see results after voting), OR
# - The poll is closed (everyone can see final results)
#
# This encourages authentic voting without being influenced by current standings.
# =============================================================================


@router.get("/polls", response_model=APIResponse[list[PollListResponse]])
async def list_polls(
    org_id: Annotated[str, Path()],
    event_id: Annotated[str, Path()],
    user_id: OptionalUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
) -> APIResponse[list[PollListResponse]]:
    """
    List polls for an event.

    Returns polls for the specified event, filtered by status. This endpoint
    is used to display available polls to spectators in the mobile app or
    web interface.

    ## Use Cases

    - **Active polls display**: Show users which polls they can vote in
    - **Poll history**: Display past polls with `status=closed`
    - **Admin overview**: List all polls with `status=all`

    ## Status Filter

    | Value | Description |
    |-------|-------------|
    | (default) | Active polls only - currently accepting votes |
    | `active` | Same as default |
    | `closed` | Completed polls - voting has ended |
    | `all` | All non-draft polls (active + closed) |

    Note: Draft polls are never returned via this endpoint.

    ## Authentication

    **Public endpoint** - no authentication required.

    When authenticated, the response includes `user_has_voted` for each poll,
    allowing the UI to show which polls the user has already participated in.

    ## Response Fields

    - `id`: Unique poll identifier
    - `question`: The poll question text
    - `status`: Current poll status (active/closed)
    - `opens_at`: When voting opens (null = immediately)
    - `closes_at`: When voting closes (null = manually closed)
    - `total_votes`: Number of votes cast
    - `user_has_voted`: Whether the authenticated user has voted

    ## Example Response

    ```json
    {
      "data": [
        {
          "id": "pol_abc123",
          "question": "Who has the Best Looking Car?",
          "status": "active",
          "opens_at": null,
          "closes_at": "2024-06-15T18:00:00Z",
          "total_votes": 42,
          "user_has_voted": false
        }
      ]
    }
    ```
    """
    from models.engagement import Poll, PollVote, PollStatus

    # Verify event exists
    await verify_event_access(org_id, event_id, db)

    # Build query based on status filter
    stmt = select(Poll).where(Poll.event_id == event_id)

    if status_filter == "closed":
        stmt = stmt.where(Poll.status == PollStatus.CLOSED)
    elif status_filter == "all":
        stmt = stmt.where(Poll.status != PollStatus.DRAFT)
    else:
        # Default: active polls only
        stmt = stmt.where(Poll.status == PollStatus.ACTIVE)

    stmt = stmt.order_by(Poll.created_at.desc())
    result = await db.execute(stmt)
    polls = result.scalars().all()

    # Get vote counts and user votes
    poll_ids = [p.id for p in polls]
    user_votes = set()

    if user_id and poll_ids:
        vote_stmt = select(PollVote.poll_id).where(
            PollVote.user_id == user_id,
            PollVote.poll_id.in_(poll_ids),
        )
        vote_result = await db.execute(vote_stmt)
        user_votes = {row[0] for row in vote_result.all()}

    # Get vote counts per poll
    vote_counts = {}
    if poll_ids:
        count_stmt = (
            select(PollVote.poll_id, func.count(PollVote.id))
            .where(PollVote.poll_id.in_(poll_ids))
            .group_by(PollVote.poll_id)
        )
        count_result = await db.execute(count_stmt)
        vote_counts = {row[0]: row[1] for row in count_result.all()}

    response_data = [
        PollListResponse(
            id=poll.id,
            question=poll.question,
            status=poll.status.value,
            opens_at=poll.opens_at,
            closes_at=poll.closes_at,
            total_votes=vote_counts.get(poll.id, 0),
            user_has_voted=poll.id in user_votes,
        )
        for poll in polls
    ]

    return APIResponse(data=response_data)


@router.get("/polls/{poll_id}", response_model=APIResponse[PollResponse])
async def get_poll(
    org_id: Annotated[str, Path()],
    event_id: Annotated[str, Path()],
    poll_id: Annotated[str, Path()],
    user_id: OptionalUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[PollResponse]:
    """
    Get a poll with its options.

    Returns the full poll details including all voting options. This endpoint
    is used to display the poll voting interface to users.

    ## Use Cases

    - **Voting screen**: Display the poll question and all options for voting
    - **Poll preview**: Show poll details before/after voting
    - **Option linking**: Options may reference racers via `racer_id` for
      displaying car photos or racer details alongside the option

    ## Authentication

    **Public endpoint** - no authentication required.

    When authenticated, the response includes:
    - `user_has_voted`: Whether the user has already voted
    - `user_vote_option_id`: Which option the user selected (if voted)

    ## Poll Options

    Each option contains:
    - `id`: Unique option identifier (used when voting)
    - `label`: Display text for the option
    - `racer_id`: Optional reference to a racer (for car/racer polls)

    ## Errors

    | Status | Code | Description |
    |--------|------|-------------|
    | 404 | ERR-NOT-001 | Poll not found or is still in draft status |

    ## Example Response

    ```json
    {
      "data": {
        "id": "pol_abc123",
        "event_id": "evt_xyz789",
        "question": "Who has the Best Looking Car?",
        "description": "Vote for your favorite car design!",
        "options": [
          {"id": "opt_1", "label": "Car #5 - Lightning Bolt", "racer_id": "rcr_001"},
          {"id": "opt_2", "label": "Car #12 - Thunder", "racer_id": "rcr_002"},
          {"id": "opt_3", "label": "Car #7 - Storm Chaser", "racer_id": "rcr_003"}
        ],
        "status": "active",
        "opens_at": null,
        "closes_at": "2024-06-15T18:00:00Z",
        "created_at": "2024-06-15T08:00:00Z",
        "user_has_voted": false,
        "user_vote_option_id": null
      }
    }
    ```
    """
    from models.engagement import Poll, PollVote, PollStatus

    # Verify event exists
    await verify_event_access(org_id, event_id, db)

    # Get poll
    stmt = select(Poll).where(
        Poll.id == poll_id,
        Poll.event_id == event_id,
        Poll.status != PollStatus.DRAFT,
    )
    result = await db.execute(stmt)
    poll = result.scalar_one_or_none()

    if poll is None:
        raise NotFoundError(resource="Poll")

    # Check if user has voted
    user_has_voted = False
    user_vote_option_id = None
    if user_id:
        vote_stmt = select(PollVote).where(
            PollVote.poll_id == poll_id,
            PollVote.user_id == user_id,
        )
        vote_result = await db.execute(vote_stmt)
        vote = vote_result.scalar_one_or_none()
        if vote:
            user_has_voted = True
            user_vote_option_id = vote.option_id

    # Parse options
    options = [
        PollOptionSchema(
            id=opt.get("id", ""),
            label=opt.get("label", ""),
            racer_id=opt.get("racer_id"),
        )
        for opt in (poll.options or [])
    ]

    return APIResponse(
        data=PollResponse(
            id=poll.id,
            event_id=poll.event_id,
            question=poll.question,
            description=poll.description,
            options=options,
            status=poll.status.value,
            opens_at=poll.opens_at,
            closes_at=poll.closes_at,
            created_at=poll.created_at,
            user_has_voted=user_has_voted,
            user_vote_option_id=user_vote_option_id,
        )
    )


@router.post("/polls/{poll_id}/vote", response_model=APIResponse[PollVoteResponse], status_code=status.HTTP_201_CREATED)
async def vote_in_poll(
    org_id: Annotated[str, Path()],
    event_id: Annotated[str, Path()],
    poll_id: Annotated[str, Path()],
    body: PollVoteCreate,
    user_id: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[PollVoteResponse]:
    """
    Vote in a poll.

    Submits a vote for the specified option in a poll. Each user can only
    vote once per poll, and votes cannot be changed after submission.

    ## Use Cases

    - **Audience voting**: Let spectators vote for their favorite in various
      categories during the event
    - **Real-time engagement**: Encourage participation during race day
    - **Award decisions**: Use poll results to determine "Fan Favorite" or
      similar awards

    ## Voting Rules

    1. **One vote per poll**: Users cannot vote multiple times or change votes
    2. **Time constraints**: Respects `opens_at` and `closes_at` if configured
    3. **Active polls only**: Cannot vote in draft or closed polls
    4. **Valid options only**: The `option_id` must match one of the poll options

    ## Authentication

    **Required** - Users must be authenticated to vote.

    This ensures vote integrity and enables the one-vote-per-user rule.

    ## Request Body

    ```json
    {
      "option_id": "opt_1"
    }
    ```

    ## Errors

    | Status | Code | Description |
    |--------|------|-------------|
    | 400 | ERR-VAL-001 | Invalid option ID |
    | 401 | ERR-AUTH-001 | Authentication required |
    | 403 | ERR-AUTHZ-001 | Poll not accepting votes (closed, not open yet, or expired) |
    | 404 | ERR-NOT-001 | Poll not found |
    | 409 | ERR-VAL-002 | User has already voted in this poll |

    ## Example Request

    ```bash
    POST /v1/orgs/org_xyz/events/evt_abc/audience/polls/pol_123/vote
    Authorization: Bearer <token>
    Content-Type: application/json

    {"option_id": "opt_2"}
    ```

    ## Example Response

    ```json
    {
      "data": {
        "poll_id": "pol_123",
        "option_id": "opt_2",
        "message": "Vote recorded successfully"
      }
    }
    ```

    ## After Voting

    Once a user votes, they can view poll results via `GET /polls/{poll_id}/results`,
    even if the poll is still active. This provides immediate feedback while
    preventing result-influenced voting by users who haven't voted yet.
    """
    from models.engagement import Poll, PollVote, PollStatus

    # Verify event exists
    await verify_event_access(org_id, event_id, db)

    # Get poll
    stmt = select(Poll).where(
        Poll.id == poll_id,
        Poll.event_id == event_id,
    )
    result = await db.execute(stmt)
    poll = result.scalar_one_or_none()

    if poll is None:
        raise NotFoundError(resource="Poll")

    # Check poll is active
    if poll.status != PollStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": ErrorCodes.AUTHZ_FORBIDDEN,
                "message": "This poll is not accepting votes",
            },
        )

    # Check time constraints
    now = datetime.utcnow()
    if poll.opens_at and now < poll.opens_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": ErrorCodes.AUTHZ_FORBIDDEN,
                "message": "This poll is not open yet",
            },
        )
    if poll.closes_at and now > poll.closes_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": ErrorCodes.AUTHZ_FORBIDDEN,
                "message": "This poll has closed",
            },
        )

    # Validate option_id exists
    valid_option_ids = {opt.get("id") for opt in (poll.options or [])}
    if body.option_id not in valid_option_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": ErrorCodes.VAL_INVALID_INPUT,
                "message": "Invalid option ID",
            },
        )

    # Check for existing vote
    existing_stmt = select(PollVote).where(
        PollVote.poll_id == poll_id,
        PollVote.user_id == user_id,
    )
    existing_result = await db.execute(existing_stmt)
    existing_vote = existing_result.scalar_one_or_none()

    if existing_vote is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": ErrorCodes.VAL_DUPLICATE_ENTRY,
                "message": "You have already voted in this poll",
            },
        )

    # Create vote
    vote = PollVote(
        poll_id=poll_id,
        user_id=user_id,
        option_id=body.option_id,
    )
    db.add(vote)
    await db.commit()

    return APIResponse(
        data=PollVoteResponse(
            poll_id=poll_id,
            option_id=body.option_id,
        )
    )


@router.get("/polls/{poll_id}/results", response_model=APIResponse[PollResultsResponse])
async def get_poll_results(
    org_id: Annotated[str, Path()],
    event_id: Annotated[str, Path()],
    poll_id: Annotated[str, Path()],
    user_id: OptionalUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse[PollResultsResponse]:
    """
    Get poll results with vote counts.

    Returns detailed voting results including vote counts and percentages for
    each option. Access is controlled to prevent results from influencing
    voting behavior.

    ## Use Cases

    - **Post-vote feedback**: Show users results immediately after they vote
    - **Final results display**: Show everyone the results after poll closes
    - **Award announcements**: Display winning option for award ceremonies
    - **Analytics**: Track voting patterns and participation

    ## Results Visibility Rules

    Results are **only visible** when one of these conditions is met:

    1. **Poll is closed**: Everyone can see final results (no auth required)
    2. **User has voted**: Authenticated users who voted can see current results

    This design prevents "bandwagon voting" where users might vote for the
    current leader rather than their true preference.

    ## Authentication

    **Conditional** - Required for active polls (to verify user has voted),
    not required for closed polls.

    ## Response Fields

    - `id`: Poll identifier
    - `question`: The poll question
    - `description`: Optional additional context
    - `status`: Current status (active/closed)
    - `total_votes`: Total number of votes cast
    - `options`: Array of options with vote counts
      - `id`: Option identifier
      - `label`: Option display text
      - `racer_id`: Optional linked racer
      - `vote_count`: Number of votes for this option
      - `vote_percent`: Percentage of total votes (rounded to 1 decimal)
    - `closes_at`: When voting ends (if set)
    - `user_vote_option_id`: Which option the authenticated user voted for

    ## Errors

    | Status | Code | Description |
    |--------|------|-------------|
    | 403 | ERR-AUTHZ-001 | Results not visible (poll active and user hasn't voted) |
    | 404 | ERR-NOT-001 | Poll not found |

    ## Example Response

    ```json
    {
      "data": {
        "id": "pol_abc123",
        "question": "Who has the Best Looking Car?",
        "description": "Vote for your favorite car design!",
        "status": "closed",
        "total_votes": 127,
        "options": [
          {
            "id": "opt_1",
            "label": "Car #5 - Lightning Bolt",
            "racer_id": "rcr_001",
            "vote_count": 52,
            "vote_percent": 40.9
          },
          {
            "id": "opt_2",
            "label": "Car #12 - Thunder",
            "racer_id": "rcr_002",
            "vote_count": 45,
            "vote_percent": 35.4
          },
          {
            "id": "opt_3",
            "label": "Car #7 - Storm Chaser",
            "racer_id": "rcr_003",
            "vote_count": 30,
            "vote_percent": 23.6
          }
        ],
        "closes_at": "2024-06-15T18:00:00Z",
        "user_vote_option_id": "opt_1"
      }
    }
    ```

    ## Displaying Results

    Recommended UI patterns:
    - Use horizontal bar charts showing vote percentages
    - Highlight the winning option (highest vote count)
    - Indicate which option the user voted for
    - Show total participation count
    """
    from models.engagement import Poll, PollVote, PollStatus

    # Verify event exists
    await verify_event_access(org_id, event_id, db)

    # Get poll
    stmt = select(Poll).where(
        Poll.id == poll_id,
        Poll.event_id == event_id,
        Poll.status != PollStatus.DRAFT,
    )
    result = await db.execute(stmt)
    poll = result.scalar_one_or_none()

    if poll is None:
        raise NotFoundError(resource="Poll")

    # Check if user can see results
    # Results visible if: poll is closed OR user has voted
    user_vote_option_id = None
    user_has_voted = False
    if user_id:
        vote_stmt = select(PollVote).where(
            PollVote.poll_id == poll_id,
            PollVote.user_id == user_id,
        )
        vote_result = await db.execute(vote_stmt)
        vote = vote_result.scalar_one_or_none()
        if vote:
            user_has_voted = True
            user_vote_option_id = vote.option_id

    if poll.status != PollStatus.CLOSED and not user_has_voted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": ErrorCodes.AUTHZ_FORBIDDEN,
                "message": "Results are only visible after voting or when the poll closes",
            },
        )

    # Get vote counts per option
    count_stmt = (
        select(PollVote.option_id, func.count(PollVote.id))
        .where(PollVote.poll_id == poll_id)
        .group_by(PollVote.option_id)
    )
    count_result = await db.execute(count_stmt)
    option_counts = {row[0]: row[1] for row in count_result.all()}

    # Calculate total
    total_votes = sum(option_counts.values())

    # Build options with votes
    options_with_votes = []
    for opt in (poll.options or []):
        opt_id = opt.get("id", "")
        count = option_counts.get(opt_id, 0)
        percent = (count / total_votes * 100) if total_votes > 0 else 0.0

        options_with_votes.append(
            PollOptionWithVotes(
                id=opt_id,
                label=opt.get("label", ""),
                racer_id=opt.get("racer_id"),
                vote_count=count,
                vote_percent=round(percent, 1),
            )
        )

    return APIResponse(
        data=PollResultsResponse(
            id=poll.id,
            question=poll.question,
            description=poll.description,
            status=poll.status.value,
            total_votes=total_votes,
            options=options_with_votes,
            closes_at=poll.closes_at,
            user_vote_option_id=user_vote_option_id,
        )
    )
