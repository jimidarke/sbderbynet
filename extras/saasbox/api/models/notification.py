"""
FCM Push Notification models.

Implements the database schema from FCM_NOTIFICATION_PLAN.md:
- PushToken: FCM token registration per device
- NotificationPreference: User notification settings
- NotificationLog: Delivery logging for debugging

References:
- FCM_NOTIFICATION_PLAN.md Section 3: Database Schema
- ENTERPRISE_ROADMAP.md Phase 5: FCM Push Notifications
"""
from datetime import datetime, time
from enum import Enum as PyEnum

from sqlalchemy import (
    Enum, String, Text, Integer, Index, ForeignKey, Boolean, Time, JSON,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, generate_prefixed_id


class DeviceType(str, PyEnum):
    """Supported device platforms for push notifications."""
    ANDROID = "android"  # Phase 1
    IOS = "ios"          # Phase 2 (next year)
    WEB = "web"          # Future consideration


class NotificationStatus(str, PyEnum):
    """Delivery status for notification log entries."""
    SENT = "sent"        # Successfully delivered to FCM
    FAILED = "failed"    # FCM delivery failed
    SKIPPED = "skipped"  # Skipped due to preferences/dedup


class PushToken(Base, TimestampMixin):
    """
    FCM push token registration.

    Stores FCM registration tokens per user device. Supports multiple
    devices per user via the device_id field (client-generated UUID).

    Token lifecycle:
    - Created when user grants push permission in Flutter app
    - Updated when FCM refreshes the token
    - Marked invalid when FCM returns NOT_FOUND/UNREGISTERED

    Per FCM_NOTIFICATION_PLAN.md Section 3.1:
    - UNIQUE constraint on (user_id, device_id)
    - Index on is_valid for efficient token queries
    """

    __tablename__ = "push_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # FCM registration token (can be quite long)
    token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Device identification
    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    device_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Client-generated UUID for device",
    )

    # Optional metadata for debugging
    app_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Token validity tracking
    is_valid: Mapped[bool] = mapped_column(
        default=True,
        comment="Set to False when FCM returns NOT_FOUND/UNREGISTERED",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Last successful notification delivery",
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="push_tokens")

    __table_args__ = (
        # One token per device per user
        Index(
            "ix_push_tokens_user_device",
            "user_id", "device_id",
            unique=True,
        ),
        # Efficient lookup of valid tokens
        Index(
            "ix_push_tokens_valid",
            "is_valid",
            postgresql_where="is_valid = TRUE",
        ),
        # Constraint for device_type values
        CheckConstraint(
            "device_type IN ('android', 'ios', 'web')",
            name="ck_push_tokens_device_type",
        ),
    )


class NotificationPreference(Base, TimestampMixin):
    """
    User notification preferences.

    Controls which notifications a user receives. All settings default
    to True (opt-in by default) per FCM_NOTIFICATION_PLAN.md Section 7.2.

    Note: Emergency broadcasts and purchase confirmations cannot be
    disabled - they are handled in the FCMService layer, not here.

    Per FCM_NOTIFICATION_PLAN.md Section 3.1:
    - One row per user (UNIQUE on user_id)
    - Quiet hours optional
    """

    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Global toggle - disables all opt-outable notifications
    push_enabled: Mapped[bool] = mapped_column(default=True)

    # Quiet hours (optional)
    quiet_hours_enabled: Mapped[bool] = mapped_column(default=False)
    quiet_hours_start: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        comment="Start of quiet period, e.g., 22:00",
    )
    quiet_hours_end: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        comment="End of quiet period, e.g., 08:00",
    )

    # Per-category settings (all default to True)
    favorite_staging_enabled: Mapped[bool] = mapped_column(
        default=True,
        comment="Notify when favorite racer is within 5 heats",
    )
    favorite_results_enabled: Mapped[bool] = mapped_column(
        default=True,
        comment="Notify when favorite racer's heat completes",
    )
    poll_notifications_enabled: Mapped[bool] = mapped_column(
        default=True,
        comment="Notify about new polls and poll results",
    )
    prediction_results_enabled: Mapped[bool] = mapped_column(
        default=True,
        comment="Notify when prediction is resolved",
    )

    # Relationship
    user: Mapped["User"] = relationship(back_populates="notification_preferences")


class NotificationLog(Base):
    """
    Notification delivery log for debugging and audit.

    Records every notification attempt with status and any errors.
    Used for:
    - Troubleshooting delivery failures
    - Audit trail for emergency broadcasts
    - Metrics and analytics

    Per FCM_NOTIFICATION_PLAN.md Section 3.1:
    - Retained for 30 days (cleanup handled by background task)
    - Indexed for user lookup and status filtering
    - Consider partitioning by month for large scale

    Note: Does not use TimestampMixin - has only created_at (no updates).
    """

    __tablename__ = "notification_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # User may be null for topic-based notifications (e.g., emergency broadcasts)
    user_id: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    # Notification details
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type ID from NotificationType enum",
    )
    event_id: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    # Full payload for debugging (PII-safe content only)
    payload: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Notification content (title, body, data)",
    )

    # FCM response
    fcm_message_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="FCM message ID on success",
    )

    # Delivery status
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error details on failure",
    )

    # Timestamp (no updated_at - logs are immutable)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default="NOW()",
    )

    __table_args__ = (
        # User lookup with time filtering
        Index("ix_notification_log_user", "user_id", "created_at"),
        # Status monitoring
        Index("ix_notification_log_status", "status", "created_at"),
        # Event lookup for debugging
        Index("ix_notification_log_event", "event_id", "created_at"),
        # Constraint for status values
        CheckConstraint(
            "status IN ('sent', 'failed', 'skipped')",
            name="ck_notification_log_status",
        ),
    )


# Forward references
from models.user import User
