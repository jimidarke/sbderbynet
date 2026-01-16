"""
Races routes - rounds, heats, results, and real-time polling.

Route order is important! Specific paths must come before parameterized paths
to avoid `/{race_id}` matching literal paths like `/rounds` or `/stats`.
"""
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.database import get_db
from app.dependencies import NotFoundError
from app.redis_client import RaceCache
from modules.auth.dependencies import OptionalUser, require_org_member
from modules.races.schemas import (
    RoundResponse,
    RoundListResponse,
    HeatResponse,
    HeatListResponse,
    HeatResultsResponse,
    RaceResultResponse,
    CurrentRaceResponse,
    RacerInLane,
    RacerBrief,
    TimerInfo,
    RoundStandingsResponse,
    RacerStanding,
    EventStatsResponse,
    UpcomingHeat,
)
from schemas.common import APIResponse, PaginatedResponse, PaginationMeta


router = APIRouter()

DBSession = Annotated[AsyncSession, Depends(get_db)]


def format_time(time_value: Decimal | float | None) -> str | None:
    """Format finish time as string with 4 decimal places."""
    if time_value is None:
        return None
    return f"{float(time_value):.4f}"


# =============================================================================
# SPECIFIC PATH ROUTES - Must come BEFORE parameterized routes
# =============================================================================

@router.get(
    "/current",
    response_model=CurrentRaceResponse,
)
async def get_current_race(
    request: Request,
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    user: OptionalUser,
    db: DBSession,
) -> CurrentRaceResponse:
    """
    Get the current race status (polling endpoint).

    This is the primary endpoint for real-time race updates.
    Designed to be polled every 1-5 seconds.

    No authentication required for public events.
    Returns server-recommended poll interval based on race status.
    """
    from models.event import Event
    from models.race import Round, Heat, RaceResult, HeatStatus
    from models.racer import Racer, RacerClass

    # Check cache first
    cached = await RaceCache.get(event_id)
    if cached:
        return CurrentRaceResponse(**cached)

    # Get event
    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
        Event.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise NotFoundError("Event")

    # Check access for private events
    if not event.is_public:
        if user is None or (not user.is_system_admin and not user.is_org_member(org_id)):
            raise NotFoundError("Event")

    # Find current heat
    stmt = (
        select(Heat)
        .join(Round)
        .where(
            Round.event_id == event_id,
            Heat.is_current == True,
        )
        .options(
            joinedload(Heat.round).joinedload(Round.racer_class),
            selectinload(Heat.results).joinedload(RaceResult.racer),
        )
    )
    result = await db.execute(stmt)
    current_heat = result.unique().scalar_one_or_none()

    # Determine race status and poll interval
    now_racing = False
    race_status = "idle"
    poll_interval = 5000  # 5 seconds default

    if current_heat:
        if current_heat.status == HeatStatus.RACING:
            now_racing = True
            race_status = "racing"
            poll_interval = 1000  # 1 second during racing
        elif current_heat.status == HeatStatus.STAGING:
            race_status = "staging"
            poll_interval = 2000  # 2 seconds during staging
        elif current_heat.status == HeatStatus.FINISHED:
            race_status = "finished"
            poll_interval = 3000

    # Get total heats in current round
    total_heats = 0
    if current_heat:
        total_heats = (await db.execute(
            select(func.count()).where(Heat.round_id == current_heat.round_id)
        )).scalar() or 0

    # Build racer list with results
    racers: list[RacerInLane] = []
    if current_heat:
        for race_result in sorted(current_heat.results, key=lambda r: r.lane):
            racer = race_result.racer
            racer_class = current_heat.round.racer_class

            racers.append(RacerInLane(
                lane=race_result.lane,
                racer=RacerBrief(
                    id=racer.id,
                    first_name=racer.first_name,
                    last_name=racer.last_name,
                    car_number=racer.car_number,
                    car_name=racer.car_name,
                    class_name=racer_class.name if racer_class else None,
                ),
                finish_time=format_time(race_result.finish_time),
                finish_place=race_result.finish_place,
            ))

    # Build response
    response = CurrentRaceResponse(
        now_racing=now_racing,
        race_status=race_status,
        current_heat=HeatResponse(
            id=current_heat.id,
            round_id=current_heat.round_id,
            round_name=current_heat.round.name,
            heat_number=current_heat.heat_number,
            status=current_heat.status.value,
            is_current=True,
            started_at=current_heat.started_at,
            finished_at=current_heat.finished_at,
            racers=racers,
        ) if current_heat else None,
        round_name=current_heat.round.name if current_heat else None,
        class_name=current_heat.round.racer_class.name if current_heat and current_heat.round.racer_class else None,
        heat_number=current_heat.heat_number if current_heat else None,
        total_heats=total_heats,
        racers=racers,
        timer=None,  # Timer info would come from device sync
        poll_interval=poll_interval,
        updated_at=datetime.utcnow(),
    )

    # Cache the response
    await RaceCache.set(event_id, response.model_dump(mode="json"))

    return response


@router.get(
    "/rounds",
    response_model=APIResponse[list[RoundListResponse]],
)
async def list_rounds(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    user: OptionalUser,
    db: DBSession,
) -> APIResponse[list[RoundListResponse]]:
    """
    List all rounds for an event.

    No authentication required for public events.
    """
    from models.event import Event
    from models.race import Round, Heat

    # Verify event access
    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
        Event.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise NotFoundError("Event")

    if not event.is_public:
        if user is None or (not user.is_system_admin and not user.is_org_member(org_id)):
            raise NotFoundError("Event")

    # Get rounds with class info
    stmt = (
        select(Round)
        .where(Round.event_id == event_id)
        .options(joinedload(Round.racer_class))
        .order_by(Round.round_number)
    )
    result = await db.execute(stmt)
    rounds = result.unique().scalars().all()

    # Check which round has current heat
    current_round_id = None
    stmt = (
        select(Heat.round_id)
        .join(Round)
        .where(Round.event_id == event_id, Heat.is_current == True)
    )
    result = await db.execute(stmt)
    current_round_row = result.first()
    if current_round_row:
        current_round_id = current_round_row[0]

    round_list = [
        RoundListResponse(
            id=round_obj.id,
            name=round_obj.name,
            class_name=round_obj.racer_class.name if round_obj.racer_class else None,
            round_number=round_obj.round_number,
            status=round_obj.status.value,
            heats_scheduled=round_obj.heats_scheduled,
            heats_completed=round_obj.heats_completed,
            is_current=round_obj.id == current_round_id,
        )
        for round_obj in rounds
    ]

    return APIResponse(data=round_list)


@router.get(
    "/rounds/{round_id}/standings",
    response_model=APIResponse[RoundStandingsResponse],
)
async def get_round_standings(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    round_id: Annotated[str, Path(description="Round ID")],
    user: OptionalUser,
    db: DBSession,
) -> APIResponse[RoundStandingsResponse]:
    """
    Get standings for a round.

    Calculates rankings based on finish times or points.
    No authentication required for public events.
    """
    from models.event import Event
    from models.race import Round, Heat, RaceResult
    from models.racer import Racer

    # Verify event access
    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
        Event.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise NotFoundError("Event")

    if not event.is_public:
        if user is None or (not user.is_system_admin and not user.is_org_member(org_id)):
            raise NotFoundError("Event")

    # Get round
    stmt = (
        select(Round)
        .where(Round.id == round_id, Round.event_id == event_id)
        .options(joinedload(Round.racer_class))
    )
    result = await db.execute(stmt)
    round_obj = result.unique().scalar_one_or_none()

    if round_obj is None:
        raise NotFoundError("Round")

    # Get all results for this round
    stmt = (
        select(RaceResult)
        .join(Heat)
        .where(Heat.round_id == round_id)
        .options(joinedload(RaceResult.racer))
    )
    result = await db.execute(stmt)
    results = result.unique().scalars().all()

    # Aggregate by racer
    racer_stats: dict[str, dict] = {}
    for race_result in results:
        racer_id = race_result.racer_id
        if racer_id not in racer_stats:
            racer_stats[racer_id] = {
                "racer": race_result.racer,
                "races": 0,
                "times": [],
                "points": 0,
                "wins": 0,
                "podiums": 0,
            }

        stats = racer_stats[racer_id]
        stats["races"] += 1

        if race_result.finish_time:
            stats["times"].append(float(race_result.finish_time))

        if race_result.points:
            stats["points"] += race_result.points

        if race_result.finish_place == 1:
            stats["wins"] += 1
        if race_result.finish_place and race_result.finish_place <= 3:
            stats["podiums"] += 1

    # Build standings
    standings: list[RacerStanding] = []
    for racer_id, stats in racer_stats.items():
        racer = stats["racer"]
        times = stats["times"]

        standing = RacerStanding(
            rank=0,  # Will be set after sorting
            racer=RacerBrief(
                id=racer.id,
                first_name=racer.first_name,
                last_name=racer.last_name,
                car_number=racer.car_number,
                car_name=racer.car_name,
                class_name=round_obj.racer_class.name if round_obj.racer_class else None,
            ),
            races_completed=stats["races"],
            total_time=format_time(sum(times)) if times else None,
            average_time=format_time(sum(times) / len(times)) if times else None,
            best_time=format_time(min(times)) if times else None,
            total_points=stats["points"] if event.use_points else None,
            wins=stats["wins"],
            podiums=stats["podiums"],
        )
        standings.append(standing)

    # Sort by best time (or points if using points system)
    if event.use_points:
        standings.sort(key=lambda s: (-s.total_points or 0, s.best_time or "999"))
    else:
        standings.sort(key=lambda s: (s.best_time or "999", -s.wins))

    # Assign ranks
    for i, standing in enumerate(standings, 1):
        standing.rank = i

    # Get heat counts
    total_heats = (await db.execute(
        select(func.count()).where(Heat.round_id == round_id)
    )).scalar() or 0

    completed_heats = (await db.execute(
        select(func.count()).where(
            Heat.round_id == round_id,
            Heat.status == "finished",
        )
    )).scalar() or 0

    return APIResponse(data=RoundStandingsResponse(
        round_id=round_obj.id,
        round_name=round_obj.name,
        class_name=round_obj.racer_class.name if round_obj.racer_class else None,
        heats_completed=completed_heats,
        heats_total=total_heats,
        standings=standings,
        use_points=event.use_points,
    ))


@router.get(
    "/stats",
    response_model=APIResponse[EventStatsResponse],
)
async def get_event_stats(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    user: OptionalUser,
    db: DBSession,
) -> APIResponse[EventStatsResponse]:
    """
    Get overall statistics for an event.

    No authentication required for public events.
    """
    from models.event import Event
    from models.racer import Racer, RacerClass
    from models.race import Round, Heat, RaceResult, HeatStatus

    # Verify event access
    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
        Event.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise NotFoundError("Event")

    if not event.is_public:
        if user is None or (not user.is_system_admin and not user.is_org_member(org_id)):
            raise NotFoundError("Event")

    # Get counts
    total_racers = (await db.execute(
        select(func.count()).where(Racer.event_id == event_id)
    )).scalar() or 0

    total_classes = (await db.execute(
        select(func.count()).where(RacerClass.event_id == event_id)
    )).scalar() or 0

    total_rounds = (await db.execute(
        select(func.count()).where(Round.event_id == event_id)
    )).scalar() or 0

    total_heats = (await db.execute(
        select(func.count()).select_from(Heat).join(Round).where(Round.event_id == event_id)
    )).scalar() or 0

    heats_completed = (await db.execute(
        select(func.count())
        .select_from(Heat)
        .join(Round)
        .where(Round.event_id == event_id, Heat.status == HeatStatus.FINISHED)
    )).scalar() or 0

    # Get fastest time
    stmt = (
        select(RaceResult.finish_time, Racer.first_name, Racer.last_name)
        .join(Heat)
        .join(Round)
        .join(Racer, RaceResult.racer_id == Racer.id)
        .where(
            Round.event_id == event_id,
            RaceResult.finish_time.isnot(None),
        )
        .order_by(RaceResult.finish_time)
        .limit(1)
    )
    result = await db.execute(stmt)
    fastest = result.first()

    fastest_time = None
    fastest_racer = None
    if fastest:
        fastest_time = format_time(fastest[0])
        fastest_racer = f"{fastest[1]} {fastest[2]}"

    # Get average time
    avg_result = await db.execute(
        select(func.avg(RaceResult.finish_time))
        .join(Heat)
        .join(Round)
        .where(
            Round.event_id == event_id,
            RaceResult.finish_time.isnot(None),
        )
    )
    avg_time = avg_result.scalar()

    # Check if currently racing
    is_racing = (await db.execute(
        select(func.count())
        .select_from(Heat)
        .join(Round)
        .where(
            Round.event_id == event_id,
            Heat.is_current == True,
            Heat.status == HeatStatus.RACING,
        )
    )).scalar() or 0 > 0

    return APIResponse(data=EventStatsResponse(
        event_id=event_id,
        event_name=event.name,
        total_racers=total_racers,
        total_classes=total_classes,
        total_rounds=total_rounds,
        total_heats=total_heats,
        heats_completed=heats_completed,
        fastest_time=fastest_time,
        fastest_racer=fastest_racer,
        average_time=format_time(avg_time) if avg_time else None,
        event_status=event.status.value,
        is_racing=is_racing,
    ))


# =============================================================================
# LIST ROUTES - Empty path for listing
# =============================================================================

@router.get(
    "",
    response_model=PaginatedResponse[HeatListResponse],
)
async def list_races(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    user: OptionalUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    round_id: str | None = Query(None, description="Filter by round"),
    status_filter: str | None = Query(None, alias="status"),
) -> PaginatedResponse[HeatListResponse]:
    """
    List all heats/races for an event.

    No authentication required for public events.
    """
    from models.event import Event
    from models.race import Round, Heat

    # Verify event access
    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
        Event.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise NotFoundError("Event")

    if not event.is_public:
        if user is None or (not user.is_system_admin and not user.is_org_member(org_id)):
            raise NotFoundError("Event")

    # Build query
    query = (
        select(Heat)
        .join(Round)
        .where(Round.event_id == event_id)
        .options(joinedload(Heat.round))
    )

    if round_id:
        query = query.where(Heat.round_id == round_id)

    if status_filter:
        query = query.where(Heat.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated results
    query = query.order_by(Round.round_number, Heat.heat_number)
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    heats = result.unique().scalars().all()

    heat_list = [
        HeatListResponse(
            id=heat.id,
            round_name=heat.round.name,
            heat_number=heat.heat_number,
            status=heat.status.value,
            is_current=heat.is_current,
        )
        for heat in heats
    ]

    return PaginatedResponse(
        data=heat_list,
        meta=PaginationMeta.from_query(total, page, per_page),
    )


# =============================================================================
# PARAMETERIZED ROUTES - Must come AFTER specific paths
# =============================================================================

@router.get(
    "/{race_id}",
    response_model=APIResponse[HeatResponse],
)
async def get_race(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    race_id: Annotated[str, Path(description="Heat/Race ID")],
    user: OptionalUser,
    db: DBSession,
) -> APIResponse[HeatResponse]:
    """
    Get details of a specific heat/race.

    No authentication required for public events.
    """
    from models.event import Event
    from models.race import Round, Heat, RaceResult

    # Verify event access
    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
        Event.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise NotFoundError("Event")

    if not event.is_public:
        if user is None or (not user.is_system_admin and not user.is_org_member(org_id)):
            raise NotFoundError("Event")

    # Get heat with results
    stmt = (
        select(Heat)
        .where(Heat.id == race_id)
        .options(
            joinedload(Heat.round).joinedload(Round.racer_class),
            selectinload(Heat.results).joinedload(RaceResult.racer),
        )
    )
    result = await db.execute(stmt)
    heat = result.unique().scalar_one_or_none()

    if heat is None or heat.round.event_id != event_id:
        raise NotFoundError("Race")

    # Build racer list
    racers: list[RacerInLane] = []
    for race_result in sorted(heat.results, key=lambda r: r.lane):
        racer = race_result.racer
        racer_class = heat.round.racer_class

        racers.append(RacerInLane(
            lane=race_result.lane,
            racer=RacerBrief(
                id=racer.id,
                first_name=racer.first_name,
                last_name=racer.last_name,
                car_number=racer.car_number,
                car_name=racer.car_name,
                class_name=racer_class.name if racer_class else None,
            ),
            finish_time=format_time(race_result.finish_time),
            finish_place=race_result.finish_place,
        ))

    return APIResponse(data=HeatResponse(
        id=heat.id,
        round_id=heat.round_id,
        round_name=heat.round.name,
        heat_number=heat.heat_number,
        status=heat.status.value,
        is_current=heat.is_current,
        started_at=heat.started_at,
        finished_at=heat.finished_at,
        racers=racers,
    ))


@router.get(
    "/{race_id}/results",
    response_model=APIResponse[HeatResultsResponse],
)
async def get_race_results(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    race_id: Annotated[str, Path(description="Heat/Race ID")],
    user: OptionalUser,
    db: DBSession,
) -> APIResponse[HeatResultsResponse]:
    """
    Get results for a specific heat/race.

    No authentication required for public events.
    """
    from models.event import Event
    from models.race import Round, Heat, RaceResult

    # Verify event access
    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
        Event.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise NotFoundError("Event")

    if not event.is_public:
        if user is None or (not user.is_system_admin and not user.is_org_member(org_id)):
            raise NotFoundError("Event")

    # Get heat with results
    stmt = (
        select(Heat)
        .where(Heat.id == race_id)
        .options(
            joinedload(Heat.round),
            selectinload(Heat.results).joinedload(RaceResult.racer),
        )
    )
    result = await db.execute(stmt)
    heat = result.unique().scalar_one_or_none()

    if heat is None or heat.round.event_id != event_id:
        raise NotFoundError("Race")

    # Build results sorted by place
    results = sorted(
        heat.results,
        key=lambda r: (r.finish_place or 999, r.lane),
    )

    result_list = [
        RaceResultResponse(
            id=r.id,
            heat_id=heat.id,
            racer_id=r.racer_id,
            racer_name=f"{r.racer.first_name} {r.racer.last_name}",
            car_number=r.racer.car_number,
            lane=r.lane,
            finish_time=format_time(r.finish_time),
            finish_place=r.finish_place,
            points=r.points,
        )
        for r in results
    ]

    return APIResponse(data=HeatResultsResponse(
        heat_id=heat.id,
        round_name=heat.round.name,
        heat_number=heat.heat_number,
        status=heat.status.value,
        results=result_list,
    ))
