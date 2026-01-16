"""
Events routes - CRUD operations for race day events.
"""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import NotFoundError
from middleware.logging import alert_manager
from modules.auth.dependencies import (
    AuthenticatedUser,
    AuthenticatedDevice,
    OptionalUser,
    require_org_admin,
    require_org_member,
)
from modules.events.schemas import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventListResponse,
    EventPublishRequest,
    EventSyncData,
    SyncStatusResponse,
)
from schemas.common import APIResponse, PaginatedResponse, PaginationMeta


router = APIRouter()


# Type alias for database session
DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "",
    response_model=APIResponse[EventResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    org_id: Annotated[str, Path(description="Organization ID")],
    body: EventCreate,
    user: AuthenticatedUser,
    db: DBSession,
    _: None = Depends(require_org_admin()),
) -> APIResponse[EventResponse]:
    """
    Create a new event for an organization.

    Requires: Organization admin role
    """
    from models.event import Event, EventStatus

    # Create event
    event = Event(
        org_id=org_id,
        name=body.name,
        description=body.description,
        event_date=body.event_date,
        venue_name=body.location.venue_name if body.location else None,
        venue_address=body.location.venue_address if body.location else None,
        city=body.location.city if body.location else None,
        province=body.location.province if body.location else None,
        lanes=body.lanes,
        use_points=body.use_points,
        status=EventStatus.DRAFT,
        settings=body.settings.model_dump() if body.settings else {},
    )

    db.add(event)
    await db.commit()
    await db.refresh(event)

    return APIResponse(data=EventResponse.model_validate(event))


@router.get(
    "",
    response_model=PaginatedResponse[EventListResponse],
)
async def list_events(
    org_id: Annotated[str, Path(description="Organization ID")],
    user: AuthenticatedUser,
    db: DBSession,
    _: None = Depends(require_org_member()),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
) -> PaginatedResponse[EventListResponse]:
    """
    List events for an organization.

    Requires: Organization member role
    """
    from models.event import Event
    from models.racer import Racer, RacerClass

    # Base query
    query = select(Event).where(Event.org_id == org_id, Event.deleted_at.is_(None))

    if status_filter:
        query = query.where(Event.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated results
    query = query.order_by(Event.event_date.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    events = result.scalars().all()

    # Get counts for each event
    event_list = []
    for event in events:
        # Count racers
        racer_count = (await db.execute(
            select(func.count()).where(Racer.event_id == event.id)
        )).scalar() or 0

        # Count classes
        class_count = (await db.execute(
            select(func.count()).where(RacerClass.event_id == event.id)
        )).scalar() or 0

        event_list.append(EventListResponse(
            id=event.id,
            name=event.name,
            event_date=event.event_date,
            city=event.city,
            status=event.status.value,
            is_public=event.is_public,
            racer_count=racer_count,
            class_count=class_count,
        ))

    return PaginatedResponse(
        data=event_list,
        meta=PaginationMeta.from_query(total, page, per_page),
    )


@router.get(
    "/{event_id}",
    response_model=APIResponse[EventResponse],
)
async def get_event(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    user: OptionalUser,
    db: DBSession,
) -> APIResponse[EventResponse]:
    """
    Get event details.

    Public events can be accessed without authentication.
    Private events require organization membership.
    """
    from models.event import Event

    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
        Event.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise NotFoundError("Event")

    # Check access
    if not event.is_public:
        if user is None:
            raise NotFoundError("Event")  # Don't reveal existence
        if not user.is_system_admin and not user.is_org_member(org_id):
            raise NotFoundError("Event")

    return APIResponse(data=EventResponse.model_validate(event))


@router.patch(
    "/{event_id}",
    response_model=APIResponse[EventResponse],
)
async def update_event(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    body: EventUpdate,
    user: AuthenticatedUser,
    db: DBSession,
    _: None = Depends(require_org_admin()),
) -> APIResponse[EventResponse]:
    """
    Update event details.

    Requires: Organization admin role
    """
    from models.event import Event

    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
        Event.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise NotFoundError("Event")

    # Update fields
    update_data = body.model_dump(exclude_unset=True)

    if "location" in update_data and update_data["location"]:
        loc = update_data.pop("location")
        event.venue_name = loc.get("venue_name", event.venue_name)
        event.venue_address = loc.get("venue_address", event.venue_address)
        event.city = loc.get("city", event.city)
        event.province = loc.get("province", event.province)

    if "settings" in update_data and update_data["settings"]:
        # Merge settings
        current_settings = event.settings or {}
        current_settings.update(update_data.pop("settings"))
        event.settings = current_settings

    for field, value in update_data.items():
        if hasattr(event, field):
            setattr(event, field, value)

    event.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(event)

    return APIResponse(data=EventResponse.model_validate(event))


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_event(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    user: AuthenticatedUser,
    db: DBSession,
    _: None = Depends(require_org_admin()),
) -> None:
    """
    Soft delete an event (archive).

    Requires: Organization admin role
    """
    from models.event import Event

    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
        Event.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise NotFoundError("Event")

    event.deleted_at = datetime.utcnow()
    await db.commit()


@router.post(
    "/{event_id}/publish",
    response_model=APIResponse[EventResponse],
)
async def publish_event(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    body: EventPublishRequest,
    user: AuthenticatedUser,
    db: DBSession,
    _: None = Depends(require_org_admin()),
) -> APIResponse[EventResponse]:
    """
    Publish or unpublish an event.

    When published, the event becomes visible to the public.
    Also changes status from DRAFT to PUBLISHED.

    Requires: Organization admin role
    """
    from models.event import Event, EventStatus

    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
        Event.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise NotFoundError("Event")

    event.is_public = body.is_public

    if body.is_public and event.status == EventStatus.DRAFT:
        event.status = EventStatus.PUBLISHED

    event.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(event)

    return APIResponse(data=EventResponse.model_validate(event))


@router.post(
    "/{event_id}/sync",
    response_model=APIResponse[SyncStatusResponse],
)
async def sync_event_data(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    body: EventSyncData,
    device: AuthenticatedDevice,
    db: DBSession,
) -> APIResponse[SyncStatusResponse]:
    """
    Sync race data from a DerbyPi device.

    This endpoint receives data from the on-premise DerbyNet installation
    and updates the cloud database.

    Requires: Authenticated DerbyPi device
    """
    from models.event import Event
    from models.racer import Racer, RacerClass
    from models.race import Round, Heat, RaceResult, RoundStatus, HeatStatus

    # Verify device belongs to org
    if device.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device not authorized for this organization",
        )

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

    try:
        # Sync classes
        class_id_map = {}  # derbynet_id -> our_id
        for class_data in body.classes:
            # Find existing or create
            stmt = select(RacerClass).where(
                RacerClass.event_id == event_id,
                RacerClass.derbynet_class_id == class_data.derbynet_class_id,
            )
            result = await db.execute(stmt)
            racer_class = result.scalar_one_or_none()

            if racer_class is None:
                racer_class = RacerClass(
                    event_id=event_id,
                    derbynet_class_id=class_data.derbynet_class_id,
                    name=class_data.name,
                    sort_order=class_data.sort_order,
                )
                db.add(racer_class)
                await db.flush()
            else:
                racer_class.name = class_data.name
                racer_class.sort_order = class_data.sort_order

            class_id_map[class_data.derbynet_class_id] = racer_class.id

        # Sync racers
        racer_id_map = {}  # derbynet_id -> our_id
        for racer_data in body.racers:
            stmt = select(Racer).where(
                Racer.event_id == event_id,
                Racer.derbynet_racer_id == racer_data.derbynet_racer_id,
            )
            result = await db.execute(stmt)
            racer = result.scalar_one_or_none()

            class_id = class_id_map.get(racer_data.derbynet_class_id) if racer_data.derbynet_class_id else None

            if racer is None:
                racer = Racer(
                    event_id=event_id,
                    class_id=class_id,
                    derbynet_racer_id=racer_data.derbynet_racer_id,
                    first_name=racer_data.first_name,
                    last_name=racer_data.last_name,
                    car_number=racer_data.car_number,
                    car_name=racer_data.car_name,
                )
                db.add(racer)
                await db.flush()
            else:
                racer.class_id = class_id
                racer.first_name = racer_data.first_name
                racer.last_name = racer_data.last_name
                racer.car_number = racer_data.car_number
                racer.car_name = racer_data.car_name

            racer_id_map[racer_data.derbynet_racer_id] = racer.id

        # Sync rounds
        round_id_map = {}  # derbynet_id -> our_id
        for round_data in body.rounds:
            stmt = select(Round).where(
                Round.event_id == event_id,
                Round.derbynet_round_id == round_data.derbynet_round_id,
            )
            result = await db.execute(stmt)
            round_obj = result.scalar_one_or_none()

            class_id = class_id_map.get(round_data.derbynet_class_id) if round_data.derbynet_class_id else None

            if round_obj is None:
                round_obj = Round(
                    event_id=event_id,
                    class_id=class_id,
                    derbynet_round_id=round_data.derbynet_round_id,
                    name=round_data.name,
                    round_number=round_data.round_number,
                    status=RoundStatus.PENDING,
                )
                db.add(round_obj)
                await db.flush()
            else:
                round_obj.class_id = class_id
                round_obj.name = round_data.name
                round_obj.round_number = round_data.round_number

            round_id_map[round_data.derbynet_round_id] = round_obj.id

        # Sync heats
        heat_id_map = {}  # (derbynet_round_id, heat_number) -> our_id
        for heat_data in body.heats:
            round_id = round_id_map.get(heat_data.derbynet_round_id)
            if not round_id:
                continue

            stmt = select(Heat).where(
                Heat.round_id == round_id,
                Heat.heat_number == heat_data.heat_number,
            )
            result = await db.execute(stmt)
            heat = result.scalar_one_or_none()

            if heat is None:
                heat = Heat(
                    round_id=round_id,
                    heat_number=heat_data.heat_number,
                    is_current=heat_data.is_current,
                    status=HeatStatus.SCHEDULED,
                )
                db.add(heat)
                await db.flush()
            else:
                heat.is_current = heat_data.is_current

            heat_id_map[(heat_data.derbynet_round_id, heat_data.heat_number)] = heat.id

            # Clear is_current from other heats if this one is current
            if heat_data.is_current:
                await db.execute(
                    select(Heat)
                    .where(Heat.id != heat.id, Heat.is_current == True)
                )

        # Sync results
        for result_data in body.results:
            heat_key = (result_data.derbynet_round_id, result_data.heat_number)
            heat_id = heat_id_map.get(heat_key)
            racer_id = racer_id_map.get(result_data.derbynet_racer_id)

            if not heat_id or not racer_id:
                continue

            stmt = select(RaceResult).where(
                RaceResult.heat_id == heat_id,
                RaceResult.racer_id == racer_id,
            )
            result = await db.execute(stmt)
            race_result = result.scalar_one_or_none()

            if race_result is None:
                race_result = RaceResult(
                    heat_id=heat_id,
                    racer_id=racer_id,
                    lane=result_data.lane,
                    finish_time=result_data.finish_time,
                    finish_place=result_data.finish_place,
                    synced_at=datetime.utcnow(),
                )
                db.add(race_result)
            else:
                race_result.lane = result_data.lane
                race_result.finish_time = result_data.finish_time
                race_result.finish_place = result_data.finish_place
                race_result.synced_at = datetime.utcnow()

        # Update event sync metadata
        event.derbynet_db_hash = body.db_hash
        event.last_sync_at = datetime.utcnow()
        event.synced_by_device = device.device_id

        await db.commit()

        # Get counts for response
        racer_count = (await db.execute(
            select(func.count()).where(Racer.event_id == event_id)
        )).scalar() or 0
        class_count = (await db.execute(
            select(func.count()).where(RacerClass.event_id == event_id)
        )).scalar() or 0
        round_count = (await db.execute(
            select(func.count()).where(Round.event_id == event_id)
        )).scalar() or 0
        heat_count = (await db.execute(
            select(func.count()).select_from(Heat).join(Round).where(Round.event_id == event_id)
        )).scalar() or 0
        result_count = (await db.execute(
            select(func.count()).select_from(RaceResult).join(Heat).join(Round).where(Round.event_id == event_id)
        )).scalar() or 0

        return APIResponse(data=SyncStatusResponse(
            event_id=event_id,
            last_sync_at=event.last_sync_at,
            synced_by_device=event.synced_by_device,
            db_hash=event.derbynet_db_hash,
            racer_count=racer_count,
            class_count=class_count,
            round_count=round_count,
            heat_count=heat_count,
            result_count=result_count,
        ))

    except Exception as e:
        await db.rollback()
        await alert_manager.device_sync_error(
            device_id=device.device_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )


@router.get(
    "/{event_id}/sync-status",
    response_model=APIResponse[SyncStatusResponse],
)
async def get_sync_status(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    user: AuthenticatedUser,
    db: DBSession,
    _: None = Depends(require_org_admin()),
) -> APIResponse[SyncStatusResponse]:
    """
    Get the sync status of an event.

    Shows when data was last synced from a DerbyPi device.

    Requires: Organization admin role
    """
    from models.event import Event
    from models.racer import Racer, RacerClass
    from models.race import Round, Heat, RaceResult

    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
        Event.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise NotFoundError("Event")

    # Get counts
    racer_count = (await db.execute(
        select(func.count()).where(Racer.event_id == event_id)
    )).scalar() or 0
    class_count = (await db.execute(
        select(func.count()).where(RacerClass.event_id == event_id)
    )).scalar() or 0
    round_count = (await db.execute(
        select(func.count()).where(Round.event_id == event_id)
    )).scalar() or 0
    heat_count = (await db.execute(
        select(func.count()).select_from(Heat).join(Round).where(Round.event_id == event_id)
    )).scalar() or 0
    result_count = (await db.execute(
        select(func.count()).select_from(RaceResult).join(Heat).join(Round).where(Round.event_id == event_id)
    )).scalar() or 0

    return APIResponse(data=SyncStatusResponse(
        event_id=event_id,
        last_sync_at=event.last_sync_at,
        synced_by_device=event.synced_by_device,
        db_hash=event.derbynet_db_hash,
        racer_count=racer_count,
        class_count=class_count,
        round_count=round_count,
        heat_count=heat_count,
        result_count=result_count,
    ))
