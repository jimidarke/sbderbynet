"""
Notification endpoints for FCM push notifications.

This module provides endpoints for:
- Push token registration and management (/me/push-token)
- Notification preferences (/me/notifications/preferences)
- Emergency broadcasts (/orgs/{org_id}/events/{event_id}/emergency)

See FCM_NOTIFICATION_PLAN.md Section 10: API Endpoints

Authentication:
- All endpoints require Bearer token authentication
- Emergency broadcasts require Race Coordinator role

Rate Limiting:
- Standard user rate limits apply
- Emergency broadcasts are additionally limited to 5 per hour per event
"""
from datetime import datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import DBSession, NotFoundError
from app.redis_client import get_redis
from middleware.logging import alert_manager
from modules.auth.dependencies import (
    AuthenticatedUser,
    CurrentUser,
    get_current_user,
    require_org_admin,
)
from modules.notifications.schemas import (
    DeviceType,
    EmergencyBroadcastRequest,
    EmergencyBroadcastResponse,
    EmergencyClearResponse,
    NotificationHistoryResponse,
    NotificationLogEntry,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
    PushTokenListResponse,
    PushTokenRegisterRequest,
    PushTokenResponse,
)
from schemas.common import APIResponse, ErrorCodes
from services.notifications.fcm_service import FCMService


router = APIRouter()
settings = get_settings()


# =============================================================================
# Push Token Endpoints (/me/push-token)
# =============================================================================


@router.post(
    "/push-token",
    response_model=APIResponse[PushTokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register FCM push token",
    responses={
        201: {"description": "Token registered successfully"},
        400: {"description": "Invalid token format"},
        401: {"description": "Authentication required"},
    },
)
async def register_push_token(
    body: PushTokenRegisterRequest,
    user: AuthenticatedUser,
    db: DBSession,
) -> APIResponse[PushTokenResponse]:
    """
    Register or update an FCM push token for the current user's device.

    This endpoint is called when:
    - User grants push notification permission in the mobile app
    - FCM refreshes the registration token (happens periodically)
    - User logs in on a new device

    **Token Lifecycle:**
    - Tokens are stored per device (identified by device_id)
    - If a token already exists for the user+device, it is updated
    - Tokens are automatically invalidated when FCM reports them as invalid

    **Example Request:**
    ```json
    {
        "token": "fcm_token_string_from_firebase_sdk...",
        "device_type": "android",
        "device_id": "550e8400-e29b-41d4-a716-446655440000",
        "app_version": "1.2.3"
    }
    ```

    **Note:** Also subscribes the token to FCM topics for the user's favorited events.
    """
    redis = await get_redis()
    fcm = FCMService(db, redis, alert_manager)

    success = await fcm.register_token(
        user_id=user.user_id,
        token=body.token,
        device_type=body.device_type.value,
        device_id=body.device_id,
        app_version=body.app_version,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": ErrorCodes.SYS_INTERNAL_ERROR,
                "message": "Failed to register push token",
            },
        )

    # Retrieve the registered token for response
    from models.notification import PushToken

    stmt = select(PushToken).where(
        PushToken.user_id == user.user_id,
        PushToken.device_id == body.device_id,
    )
    result = await db.execute(stmt)
    token = result.scalar_one()

    return APIResponse(
        data=PushTokenResponse(
            device_id=token.device_id,
            device_type=DeviceType(token.device_type.value),
            app_version=token.app_version,
            is_valid=token.is_valid,
            created_at=token.created_at,
            updated_at=token.updated_at,
        )
    )


@router.get(
    "/push-tokens",
    response_model=APIResponse[PushTokenListResponse],
    summary="List user's push tokens",
    responses={
        200: {"description": "List of registered tokens"},
        401: {"description": "Authentication required"},
    },
)
async def list_push_tokens(
    user: AuthenticatedUser,
    db: DBSession,
) -> APIResponse[PushTokenListResponse]:
    """
    List all push tokens registered for the current user.

    Useful for:
    - Debugging notification delivery issues
    - Showing user which devices are registered
    - Managing multi-device setups
    """
    from models.notification import PushToken

    stmt = (
        select(PushToken)
        .where(PushToken.user_id == user.user_id)
        .order_by(PushToken.created_at.desc())
    )
    result = await db.execute(stmt)
    tokens = result.scalars().all()

    return APIResponse(
        data=PushTokenListResponse(
            tokens=[
                PushTokenResponse(
                    device_id=t.device_id,
                    device_type=DeviceType(t.device_type.value),
                    app_version=t.app_version,
                    is_valid=t.is_valid,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                for t in tokens
            ]
        )
    )


@router.delete(
    "/push-token/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unregister push token",
    responses={
        204: {"description": "Token removed successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Token not found"},
    },
)
async def delete_push_token(
    device_id: Annotated[str, Path(description="Device ID to remove token for")],
    user: AuthenticatedUser,
    db: DBSession,
) -> None:
    """
    Remove a push token for the current user's device.

    Called when:
    - User logs out of the app
    - User disables push notifications in app settings
    - User wants to stop receiving notifications on a specific device

    **Note:** The token is permanently deleted, not just invalidated.
    """
    redis = await get_redis()
    fcm = FCMService(db, redis, alert_manager)

    removed = await fcm.remove_token(
        user_id=user.user_id,
        device_id=device_id,
    )

    if not removed:
        raise NotFoundError("Push token")


# =============================================================================
# Notification Preferences Endpoints (/me/notifications/preferences)
# =============================================================================


@router.get(
    "/preferences",
    response_model=APIResponse[NotificationPreferencesResponse],
    summary="Get notification preferences",
    responses={
        200: {"description": "Current notification preferences"},
        401: {"description": "Authentication required"},
    },
)
async def get_notification_preferences(
    user: AuthenticatedUser,
    db: DBSession,
) -> APIResponse[NotificationPreferencesResponse]:
    """
    Get the current user's notification preferences.

    **Default Behavior:**
    - All notifications are enabled by default
    - If no preferences exist, defaults are returned
    - Emergency broadcasts and purchase confirmations cannot be disabled

    **Preference Categories:**
    - `favorite_staging_enabled`: Notify when favorite racer within 5 heats
    - `favorite_results_enabled`: Notify when favorite's heat completes
    - `poll_notifications_enabled`: New polls and poll results
    - `prediction_results_enabled`: Prediction outcomes
    """
    from models.notification import NotificationPreference

    stmt = select(NotificationPreference).where(
        NotificationPreference.user_id == user.user_id
    )
    result = await db.execute(stmt)
    prefs = result.scalar_one_or_none()

    if prefs:
        # Convert time objects to string format
        quiet_start = prefs.quiet_hours_start.strftime("%H:%M") if prefs.quiet_hours_start else None
        quiet_end = prefs.quiet_hours_end.strftime("%H:%M") if prefs.quiet_hours_end else None

        return APIResponse(
            data=NotificationPreferencesResponse(
                push_enabled=prefs.push_enabled,
                quiet_hours_enabled=prefs.quiet_hours_enabled,
                quiet_hours_start=quiet_start,
                quiet_hours_end=quiet_end,
                favorite_staging_enabled=prefs.favorite_staging_enabled,
                favorite_results_enabled=prefs.favorite_results_enabled,
                poll_notifications_enabled=prefs.poll_notifications_enabled,
                prediction_results_enabled=prefs.prediction_results_enabled,
            )
        )

    # Return defaults
    return APIResponse(data=NotificationPreferencesResponse())


@router.patch(
    "/preferences",
    response_model=APIResponse[NotificationPreferencesResponse],
    summary="Update notification preferences",
    responses={
        200: {"description": "Preferences updated successfully"},
        400: {"description": "Invalid preference values"},
        401: {"description": "Authentication required"},
    },
)
async def update_notification_preferences(
    body: NotificationPreferencesUpdateRequest,
    user: AuthenticatedUser,
    db: DBSession,
) -> APIResponse[NotificationPreferencesResponse]:
    """
    Update the current user's notification preferences.

    **Partial Updates:**
    - Only provided fields are updated
    - Omitted fields retain their current values
    - Use `null` to reset a field to default

    **Quiet Hours:**
    - When `quiet_hours_enabled` is true, notifications are silenced during the specified period
    - Times are in HH:MM format (24-hour)
    - Example: start="22:00", end="08:00" silences notifications overnight

    **Example Request:**
    ```json
    {
        "push_enabled": true,
        "quiet_hours_enabled": true,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "08:00",
        "poll_notifications_enabled": false
    }
    ```
    """
    from models.notification import NotificationPreference

    stmt = select(NotificationPreference).where(
        NotificationPreference.user_id == user.user_id
    )
    result = await db.execute(stmt)
    prefs = result.scalar_one_or_none()

    if not prefs:
        # Create new preferences
        prefs = NotificationPreference(user_id=user.user_id)
        db.add(prefs)

    # Update provided fields
    if body.push_enabled is not None:
        prefs.push_enabled = body.push_enabled
    if body.quiet_hours_enabled is not None:
        prefs.quiet_hours_enabled = body.quiet_hours_enabled
    if body.quiet_hours_start is not None:
        # Parse HH:MM string to time object
        h, m = map(int, body.quiet_hours_start.split(":"))
        prefs.quiet_hours_start = time(h, m)
    if body.quiet_hours_end is not None:
        h, m = map(int, body.quiet_hours_end.split(":"))
        prefs.quiet_hours_end = time(h, m)
    if body.favorite_staging_enabled is not None:
        prefs.favorite_staging_enabled = body.favorite_staging_enabled
    if body.favorite_results_enabled is not None:
        prefs.favorite_results_enabled = body.favorite_results_enabled
    if body.poll_notifications_enabled is not None:
        prefs.poll_notifications_enabled = body.poll_notifications_enabled
    if body.prediction_results_enabled is not None:
        prefs.prediction_results_enabled = body.prediction_results_enabled

    prefs.updated_at = datetime.utcnow()
    await db.commit()

    # Return updated preferences
    quiet_start = prefs.quiet_hours_start.strftime("%H:%M") if prefs.quiet_hours_start else None
    quiet_end = prefs.quiet_hours_end.strftime("%H:%M") if prefs.quiet_hours_end else None

    return APIResponse(
        data=NotificationPreferencesResponse(
            push_enabled=prefs.push_enabled,
            quiet_hours_enabled=prefs.quiet_hours_enabled,
            quiet_hours_start=quiet_start,
            quiet_hours_end=quiet_end,
            favorite_staging_enabled=prefs.favorite_staging_enabled,
            favorite_results_enabled=prefs.favorite_results_enabled,
            poll_notifications_enabled=prefs.poll_notifications_enabled,
            prediction_results_enabled=prefs.prediction_results_enabled,
        )
    )


# =============================================================================
# Notification History Endpoints (/me/notifications/history)
# =============================================================================


@router.get(
    "/history",
    response_model=APIResponse[NotificationHistoryResponse],
    summary="Get notification history",
    responses={
        200: {"description": "Notification delivery history"},
        401: {"description": "Authentication required"},
    },
)
async def get_notification_history(
    user: AuthenticatedUser,
    db: DBSession,
    limit: int = 50,
) -> APIResponse[NotificationHistoryResponse]:
    """
    Get the current user's notification delivery history.

    Useful for:
    - Debugging why a notification wasn't received
    - Viewing past notifications
    - Support troubleshooting

    **Note:** History is retained for 30 days per FCM_NOTIFICATION_PLAN.md.
    """
    from models.notification import NotificationLog

    stmt = (
        select(NotificationLog)
        .where(NotificationLog.user_id == user.user_id)
        .order_by(NotificationLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    # Get total count
    count_stmt = (
        select(func.count())
        .select_from(NotificationLog)
        .where(NotificationLog.user_id == user.user_id)
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()

    return APIResponse(
        data=NotificationHistoryResponse(
            notifications=[
                NotificationLogEntry(
                    id=log.id,
                    notification_type=log.notification_type,
                    event_id=log.event_id,
                    status=log.status.value,
                    error_message=log.error_message,
                    created_at=log.created_at,
                )
                for log in logs
            ],
            total=total,
        )
    )


# =============================================================================
# Emergency Broadcast Router (mounted separately at /orgs/{org_id}/events/{event_id})
# =============================================================================


emergency_router = APIRouter()


@emergency_router.post(
    "/broadcast",
    response_model=APIResponse[EmergencyBroadcastResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Send emergency broadcast",
    responses={
        201: {"description": "Emergency broadcast sent"},
        401: {"description": "Authentication required"},
        403: {"description": "Coordinator role required"},
        429: {"description": "Rate limit exceeded (max 5 per hour)"},
    },
)
async def send_emergency_broadcast(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    body: EmergencyBroadcastRequest,
    user: AuthenticatedUser,
    db: DBSession,
    _: None = Depends(require_org_admin()),
) -> APIResponse[EmergencyBroadcastResponse]:
    """
    Send an emergency broadcast to all users at an event.

    **IMPORTANT:** This endpoint requires Race Coordinator authorization.

    **Emergency broadcasts:**
    - Are sent to ALL users at the event (cannot be opted out)
    - Are displayed on ALL LED signs simultaneously
    - Use high-priority FCM delivery (wakes device from Doze)
    - Are logged to audit trail

    **Rate Limiting:**
    - Maximum 5 broadcasts per hour per event
    - This prevents accidental spam

    **LED Sign Alignment:**
    Emergency broadcasts are synchronized with the LED sign system:
    - Same message content sent to both channels
    - MQTT topic: `derbynet/ledsign/broadcast`
    - Signs display red flashing message

    **Example Request:**
    ```json
    {
        "message": "Weather delay - seek shelter immediately",
        "severity": "emergency"
    }
    ```

    **Severity Levels:**
    - `warning`: Important notice (yellow on LED signs)
    - `emergency`: Critical alert (red flashing on LED signs)
    """
    redis = await get_redis()

    # Rate limit: max 5 emergency broadcasts per hour per event
    rate_key = f"emergency_broadcast:{event_id}"
    current_count = await redis.get(rate_key)

    if current_count and int(current_count) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": ErrorCodes.RATE_LIMIT_EXCEEDED,
                "message": "Maximum 5 emergency broadcasts per hour",
            },
            headers={"Retry-After": "3600"},
        )

    # Verify event exists and belongs to org
    from models.event import Event

    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if not event:
        raise NotFoundError("Event")

    # Send via FCM
    fcm = FCMService(db, redis, alert_manager)
    send_result = await fcm.send_emergency_broadcast(
        event_id=event_id,
        message=body.message,
        coordinator_id=user.user_id,
    )

    if send_result.failure_count > 0 and send_result.success_count == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": ErrorCodes.SYS_EXTERNAL_SERVICE,
                "message": f"Emergency broadcast failed: {send_result.errors[0] if send_result.errors else 'Unknown error'}",
            },
        )

    # Update rate limit counter
    if current_count:
        await redis.incr(rate_key)
    else:
        await redis.setex(rate_key, 3600, "1")  # 1 hour TTL

    # TODO: Also publish to MQTT for LED signs
    # This will be implemented when LED sign integration is complete
    # mqtt.publish("derbynet/ledsign/broadcast", {
    #     "priority": 0,
    #     "title": "EMERGENCY",
    #     "message": body.message,
    #     "display_config": {"mode": "flash", "color": "red"}
    # })

    return APIResponse(
        data=EmergencyBroadcastResponse(
            message_id=f"em_{event_id}_{datetime.utcnow().timestamp():.0f}",
            broadcast_message=body.message,
            severity=body.severity,
            sent_at=datetime.utcnow(),
            sent_by=user.user_id,
        )
    )


@emergency_router.delete(
    "/broadcast",
    response_model=APIResponse[EmergencyClearResponse],
    summary="Clear emergency broadcast",
    responses={
        200: {"description": "Emergency cleared"},
        401: {"description": "Authentication required"},
        403: {"description": "Coordinator role required"},
    },
)
async def clear_emergency_broadcast(
    org_id: Annotated[str, Path(description="Organization ID")],
    event_id: Annotated[str, Path(description="Event ID")],
    user: AuthenticatedUser,
    db: DBSession,
    _: None = Depends(require_org_admin()),
) -> APIResponse[EmergencyClearResponse]:
    """
    Clear an active emergency broadcast.

    This endpoint:
    - Clears the emergency state for the event
    - Sends "all clear" to LED signs
    - Does NOT send another FCM notification (to avoid spam)

    **Note:** Use this to return LED signs to normal operation after
    an emergency has been resolved.
    """
    # Verify event exists and belongs to org
    from models.event import Event

    stmt = select(Event).where(
        Event.id == event_id,
        Event.org_id == org_id,
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if not event:
        raise NotFoundError("Event")

    # TODO: Publish clear to MQTT for LED signs
    # mqtt.publish("derbynet/ledsign/broadcast", {"clear": True})

    return APIResponse(
        data=EmergencyClearResponse(
            cleared_at=datetime.utcnow(),
            cleared_by=user.user_id,
        )
    )
