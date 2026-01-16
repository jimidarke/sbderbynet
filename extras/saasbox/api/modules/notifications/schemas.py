"""
Pydantic schemas for notification endpoints.

Defines request/response models for:
- Push token registration
- Notification preferences
- Emergency broadcasts

See FCM_NOTIFICATION_PLAN.md Section 10: API Endpoints
"""
from datetime import datetime, time
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------


class DeviceType(str, Enum):
    """Supported device platforms for push notifications."""
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"


class EmergencySeverity(str, Enum):
    """Severity levels for emergency broadcasts."""
    WARNING = "warning"
    EMERGENCY = "emergency"


# -----------------------------------------------------------------------------
# Push Token Schemas
# -----------------------------------------------------------------------------


class PushTokenRegisterRequest(BaseModel):
    """
    Request to register an FCM push token.

    Called when:
    - User grants push permission in Flutter app
    - FCM refreshes the registration token
    """
    token: str = Field(
        ...,
        description="FCM registration token from Firebase SDK",
        min_length=100,  # FCM tokens are typically 150+ chars
        max_length=500,
    )
    device_type: DeviceType = Field(
        ...,
        description="Platform type (android, ios, web)",
    )
    device_id: str = Field(
        ...,
        description="Client-generated UUID for this device",
        min_length=36,
        max_length=100,
    )
    app_version: str | None = Field(
        None,
        description="App version for debugging (e.g., '1.2.3')",
        max_length=20,
    )


class PushTokenResponse(BaseModel):
    """Response after registering a push token."""
    model_config = ConfigDict(from_attributes=True)

    device_id: str
    device_type: DeviceType
    app_version: str | None
    is_valid: bool
    created_at: datetime
    updated_at: datetime | None


class PushTokenListResponse(BaseModel):
    """List of user's registered push tokens."""
    tokens: list[PushTokenResponse]


# -----------------------------------------------------------------------------
# Notification Preference Schemas
# -----------------------------------------------------------------------------


class NotificationPreferencesResponse(BaseModel):
    """
    User's notification preferences.

    All notification types default to True (opt-in by default).
    Emergency broadcasts and purchase confirmations cannot be disabled.
    """
    model_config = ConfigDict(from_attributes=True)

    # Global toggle
    push_enabled: bool = Field(
        True,
        description="Master toggle - disables all opt-outable notifications",
    )

    # Quiet hours (optional)
    quiet_hours_enabled: bool = Field(
        False,
        description="Enable quiet hours (no notifications during specified time)",
    )
    quiet_hours_start: str | None = Field(
        None,
        description="Start of quiet period in HH:MM format (e.g., '22:00')",
    )
    quiet_hours_end: str | None = Field(
        None,
        description="End of quiet period in HH:MM format (e.g., '08:00')",
    )

    # Per-category toggles
    favorite_staging_enabled: bool = Field(
        True,
        description="Notify when favorite racer is within 5 heats of racing",
    )
    favorite_results_enabled: bool = Field(
        True,
        description="Notify when favorite racer's heat completes",
    )
    poll_notifications_enabled: bool = Field(
        True,
        description="Notify about new polls and poll results",
    )
    prediction_results_enabled: bool = Field(
        True,
        description="Notify when your prediction is resolved",
    )


class NotificationPreferencesUpdateRequest(BaseModel):
    """
    Request to update notification preferences.

    All fields are optional - only provided fields are updated.
    """
    # Global toggle
    push_enabled: bool | None = None

    # Quiet hours
    quiet_hours_enabled: bool | None = None
    quiet_hours_start: str | None = Field(
        None,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="Start of quiet period in HH:MM format",
    )
    quiet_hours_end: str | None = Field(
        None,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="End of quiet period in HH:MM format",
    )

    # Per-category toggles
    favorite_staging_enabled: bool | None = None
    favorite_results_enabled: bool | None = None
    poll_notifications_enabled: bool | None = None
    prediction_results_enabled: bool | None = None


# -----------------------------------------------------------------------------
# Emergency Broadcast Schemas
# -----------------------------------------------------------------------------


class EmergencyBroadcastRequest(BaseModel):
    """
    Request to send an emergency broadcast.

    Emergency broadcasts:
    - Are sent to ALL users at the event (cannot be opted out)
    - Are displayed on ALL LED signs simultaneously
    - Require Race Coordinator authorization
    - Are rate limited (max 5 per hour)
    """
    message: str = Field(
        ...,
        description="Emergency message text",
        min_length=5,
        max_length=200,
    )
    severity: EmergencySeverity = Field(
        EmergencySeverity.EMERGENCY,
        description="Severity level (warning or emergency)",
    )


class EmergencyBroadcastResponse(BaseModel):
    """Response after sending an emergency broadcast."""
    message_id: str = Field(
        ...,
        description="FCM message ID for tracking",
    )
    broadcast_message: str = Field(
        ...,
        description="The message that was broadcast",
    )
    severity: EmergencySeverity
    sent_at: datetime
    sent_by: str = Field(
        ...,
        description="User ID of coordinator who sent the broadcast",
    )


class EmergencyClearResponse(BaseModel):
    """Response after clearing an emergency broadcast."""
    cleared_at: datetime
    cleared_by: str


# -----------------------------------------------------------------------------
# Notification History Schemas (for debugging/support)
# -----------------------------------------------------------------------------


class NotificationLogEntry(BaseModel):
    """Single notification log entry."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    notification_type: str
    event_id: str | None
    status: str  # sent, failed, skipped
    error_message: str | None
    created_at: datetime


class NotificationHistoryResponse(BaseModel):
    """User's notification history (for debugging)."""
    notifications: list[NotificationLogEntry]
    total: int
