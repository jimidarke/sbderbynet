"""
FCM Service Module for SoapboxDerbyNet Push Notifications.

This module provides a high-level interface for sending Firebase Cloud Messaging
notifications to mobile app users. It wraps the firebase-admin SDK and handles:
- Token management and validation
- Multicast message batching (up to 500 tokens per call)
- Delivery failure handling and invalid token cleanup
- Rate limiting and deduplication
- Alert Manager integration for error logging

Architecture Notes:
- Uses FCM HTTP v1 API (legacy APIs deprecated July 2024)
- Multicast via send_each_for_multicast() for batched delivery
- High priority for time-sensitive notifications (staging, emergency)
- Normal priority for results and engagement notifications

References:
- FCM HTTP v1 API: https://firebase.google.com/docs/cloud-messaging/send/v1-api
- firebase-admin SDK: https://firebase.google.com/docs/cloud-messaging/send/admin-sdk
- FCM_NOTIFICATION_PLAN.md: Full architecture documentation
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

if TYPE_CHECKING:
    from aioredis import Redis


logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """
    Enumeration of all notification types supported by the system.

    Each type maps to specific:
    - FCM priority level (high/normal)
    - User preference flag for opt-out
    - Deep link target in Flutter app
    - Template for title/body generation
    """
    FAVORITE_STAGING = "favorite_staging"
    FAVORITE_RESULT = "favorite_result"
    POLL_NEW = "poll_new"
    POLL_RESULT = "poll_result"
    PREDICTION_RESULT = "prediction_result"
    PURCHASE_CONFIRM = "purchase_confirm"
    EMERGENCY = "emergency"


@dataclass
class NotificationConfig:
    """
    Configuration for a notification type.

    Attributes:
        priority: FCM message priority ('high' or 'normal')
        preference_field: Database column for user opt-out (None = cannot opt out)
        android_channel: Android notification channel ID
        ttl_seconds: Time-to-live for FCM message delivery attempts
        collapse_key: Key for collapsing multiple notifications (optional)
    """
    priority: str
    preference_field: str | None
    android_channel: str
    ttl_seconds: int
    collapse_key: str | None = None


# Notification type configurations
NOTIFICATION_CONFIGS: dict[NotificationType, NotificationConfig] = {
    NotificationType.FAVORITE_STAGING: NotificationConfig(
        priority="high",
        preference_field="favorite_staging_enabled",
        android_channel="race_alerts",
        ttl_seconds=300,  # 5 minutes - time sensitive
        collapse_key="staging",
    ),
    NotificationType.FAVORITE_RESULT: NotificationConfig(
        priority="normal",
        preference_field="favorite_results_enabled",
        android_channel="race_results",
        ttl_seconds=3600,  # 1 hour
        collapse_key="results",
    ),
    NotificationType.POLL_NEW: NotificationConfig(
        priority="normal",
        preference_field="poll_notifications_enabled",
        android_channel="engagement",
        ttl_seconds=3600,
    ),
    NotificationType.POLL_RESULT: NotificationConfig(
        priority="normal",
        preference_field="poll_notifications_enabled",
        android_channel="engagement",
        ttl_seconds=3600,
    ),
    NotificationType.PREDICTION_RESULT: NotificationConfig(
        priority="normal",
        preference_field="prediction_results_enabled",
        android_channel="engagement",
        ttl_seconds=3600,
    ),
    NotificationType.PURCHASE_CONFIRM: NotificationConfig(
        priority="high",
        preference_field=None,  # Cannot opt out
        android_channel="transactions",
        ttl_seconds=86400,  # 24 hours
    ),
    NotificationType.EMERGENCY: NotificationConfig(
        priority="high",
        preference_field=None,  # Cannot opt out
        android_channel="emergency",
        ttl_seconds=3600,
    ),
}


@dataclass
class SendResult:
    """
    Result of a notification send operation.

    Attributes:
        success_count: Number of successfully sent messages
        failure_count: Number of failed sends
        invalid_tokens: List of tokens that should be removed from database
        errors: List of error messages for logging
    """
    success_count: int
    failure_count: int
    invalid_tokens: list[str]
    errors: list[str]


class FCMService:
    """
    Firebase Cloud Messaging service for sending push notifications.

    This service provides methods for:
    - Sending notifications to specific users by user ID
    - Sending to FCM topics for broadcast scenarios
    - Managing push token lifecycle (registration, validation, cleanup)
    - Respecting user notification preferences

    The service initializes Firebase Admin SDK on first use and maintains
    a singleton connection throughout the application lifecycle.

    Example:
        ```python
        fcm = FCMService(db_session, redis_client)

        # Send to specific users
        result = await fcm.send_to_users(
            user_ids=["usr_abc123"],
            notification_type=NotificationType.FAVORITE_STAGING,
            title="Jane S. is racing soon!",
            body="Heat 12, Lane 1 - Starting in ~5 heats",
            data={"event_id": "evt_xyz", "screen": "heat_detail"}
        )

        # Send emergency broadcast
        await fcm.send_emergency_broadcast(
            event_id="evt_xyz",
            message="Weather delay - seek shelter"
        )
        ```

    Thread Safety:
        This service is thread-safe. Firebase Admin SDK handles connection
        pooling internally. Database operations use async sessions.

    Rate Limiting:
        - Deduplication: Same notification type + user + entity within 5 minutes
        - FCM limits: 500 tokens per multicast call (handled internally)
        - Topic messages: No practical limit for this use case
    """

    _initialized = False
    _firebase_app = None

    def __init__(
        self,
        db: AsyncSession,
        redis: "Redis | None" = None,
        alert_manager: Any | None = None,
    ):
        """
        Initialize FCM service with database and cache connections.

        Args:
            db: Async SQLAlchemy session for database operations
            redis: Redis client for rate limiting and deduplication (optional)
            alert_manager: Optional Alert Manager client for error logging
        """
        self.db = db
        self.redis = redis
        self.alert_manager = alert_manager
        self.settings = get_settings()
        self._ensure_initialized()

    @classmethod
    def _ensure_initialized(cls) -> None:
        """
        Initialize Firebase Admin SDK if not already done.

        Uses service account credentials from settings.firebase_credentials_path.
        This is a one-time initialization per process.
        """
        if cls._initialized:
            return

        settings = get_settings()
        if not settings.fcm_enabled:
            logger.info("FCM disabled via settings")
            return

        if settings.firebase_credentials_path:
            try:
                import firebase_admin
                from firebase_admin import credentials

                cred = credentials.Certificate(settings.firebase_credentials_path)
                cls._firebase_app = firebase_admin.initialize_app(cred)
                cls._initialized = True
                logger.info("Firebase Admin SDK initialized for FCM")
            except Exception as e:
                logger.warning(f"Firebase initialization failed: {e}")
        else:
            logger.warning("Firebase credentials not configured - FCM disabled")

    async def send_to_users(
        self,
        user_ids: list[str],
        notification_type: NotificationType,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
        image_url: str | None = None,
        dedup_key: str | None = None,
    ) -> SendResult:
        """
        Send a notification to multiple users by their user IDs.

        This method:
        1. Filters users by notification preferences (respects opt-outs)
        2. Retrieves valid push tokens for remaining users
        3. Applies deduplication to prevent spam
        4. Batches into groups of 500 (FCM limit)
        5. Sends via FCM multicast API
        6. Handles failures and cleans up invalid tokens

        Args:
            user_ids: List of user IDs to notify
            notification_type: Type of notification (determines priority, channel)
            title: Notification title (visible on lock screen)
            body: Notification body text
            data: Optional data payload for deep linking (all values must be strings)
            image_url: Optional image URL for rich notifications
            dedup_key: Optional key for deduplication (default: notification_type)

        Returns:
            SendResult with success/failure counts and invalid tokens

        Note:
            - Title should not contain child last names (PII protection)
            - Data values must be strings (FCM requirement)
            - High priority notifications may wake device from Doze mode
        """
        if not self._initialized or not self.settings.fcm_enabled:
            logger.warning("FCM not initialized - skipping notification")
            return SendResult(0, len(user_ids), [], ["FCM not initialized"])

        config = NOTIFICATION_CONFIGS.get(notification_type)
        if not config:
            raise ValueError(f"Unknown notification type: {notification_type}")

        # Filter by user preferences
        eligible_user_ids = await self._filter_by_preferences(
            user_ids, config.preference_field
        )

        if not eligible_user_ids:
            logger.debug(f"No eligible users for {notification_type}")
            return SendResult(0, 0, [], [])

        # Apply deduplication if Redis is available
        if self.redis:
            dedup_key = dedup_key or notification_type.value
            eligible_user_ids = await self._apply_deduplication(
                eligible_user_ids, dedup_key
            )

            if not eligible_user_ids:
                logger.debug(f"All users deduplicated for {notification_type}")
                return SendResult(0, 0, [], [])

        # Get push tokens
        tokens = await self._get_tokens_for_users(eligible_user_ids)

        if not tokens:
            logger.debug(f"No valid tokens for {notification_type}")
            return SendResult(0, 0, [], [])

        # Build and send FCM message
        return await self._send_multicast_batched(
            tokens=tokens,
            title=title,
            body=body,
            data=data,
            image_url=image_url,
            config=config,
            notification_type=notification_type,
        )

    async def send_emergency_broadcast(
        self,
        event_id: str,
        message: str,
        coordinator_id: str,
    ) -> SendResult:
        """
        Send emergency broadcast to all users at an event.

        Emergency broadcasts:
        - Cannot be opted out of by users
        - Use FCM topic for efficient delivery
        - Are logged to audit trail
        - Align with LED sign emergency broadcasts

        Args:
            event_id: Event ID for topic targeting
            message: Emergency message text
            coordinator_id: User ID of coordinator (for audit)

        Returns:
            SendResult indicating delivery status

        Security:
            Authorization check must be performed by caller.
            Only Race Coordinators should call this method.
        """
        if not self._initialized or not self.settings.fcm_enabled:
            return SendResult(0, 0, [], ["FCM not initialized"])

        try:
            from firebase_admin import messaging

            topic = f"event_{event_id}"

            fcm_message = messaging.Message(
                notification=messaging.Notification(
                    title="EMERGENCY ALERT",
                    body=message,
                ),
                data={
                    "type": NotificationType.EMERGENCY.value,
                    "event_id": event_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                topic=topic,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        channel_id="emergency",
                        priority="max",
                        default_vibrate_timings=True,
                        default_light_settings=True,
                    ),
                ),
            )

            message_id = messaging.send(fcm_message)
            logger.info(
                f"Emergency broadcast sent: {message_id} "
                f"topic={topic} coordinator={coordinator_id}"
            )

            # Log to notification_log for audit
            await self._log_notification(
                user_id=None,  # Topic message
                notification_type=NotificationType.EMERGENCY,
                event_id=event_id,
                payload={"message": message, "topic": topic},
                fcm_message_id=message_id,
                status="sent",
            )

            return SendResult(1, 0, [], [])

        except Exception as e:
            error_msg = f"Emergency broadcast failed: {e}"
            logger.error(error_msg)

            if self.alert_manager:
                await self.alert_manager.system_error(
                    error=error_msg,
                    request_id=None,
                    traceback=str(e),
                )

            return SendResult(0, 1, [], [error_msg])

    async def register_token(
        self,
        user_id: str,
        token: str,
        device_type: str,
        device_id: str,
        app_version: str | None = None,
    ) -> bool:
        """
        Register or update a push token for a user's device.

        Tokens are stored per device (identified by device_id) to support
        multiple devices per user. If a token already exists for the
        user+device combination, it is updated.

        Args:
            user_id: User ID registering the token
            token: FCM registration token from client
            device_type: Platform type ('android', 'ios', 'web')
            device_id: Client-generated device UUID
            app_version: Optional app version for debugging

        Returns:
            True if registration successful, False otherwise
        """
        from models.notification import PushToken

        try:
            # Check if token exists for this user+device
            stmt = select(PushToken).where(
                PushToken.user_id == user_id,
                PushToken.device_id == device_id,
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing token
                existing.token = token
                existing.device_type = device_type
                existing.app_version = app_version
                existing.is_valid = True
                existing.updated_at = datetime.utcnow()
            else:
                # Create new token
                new_token = PushToken(
                    user_id=user_id,
                    token=token,
                    device_type=device_type,
                    device_id=device_id,
                    app_version=app_version,
                    is_valid=True,
                )
                self.db.add(new_token)

            await self.db.commit()

            # Subscribe to event topics for user's favorites
            if self._initialized:
                await self._subscribe_to_favorite_events(user_id, token)

            logger.info(f"Push token registered: user={user_id} device={device_id}")
            return True

        except Exception as e:
            logger.error(f"Token registration failed: {e}")
            await self.db.rollback()
            return False

    async def remove_token(
        self,
        user_id: str,
        device_id: str,
    ) -> bool:
        """
        Remove a push token for a user's device.

        Called when:
        - User logs out
        - User disables push notifications in app
        - App is uninstalled (if detectable)

        Args:
            user_id: User ID
            device_id: Device ID to remove token for

        Returns:
            True if token was removed, False if not found
        """
        from models.notification import PushToken

        try:
            stmt = select(PushToken).where(
                PushToken.user_id == user_id,
                PushToken.device_id == device_id,
            )
            result = await self.db.execute(stmt)
            token = result.scalar_one_or_none()

            if token:
                await self.db.delete(token)
                await self.db.commit()
                logger.info(f"Push token removed: user={user_id} device={device_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Token removal failed: {e}")
            await self.db.rollback()
            return False

    async def remove_invalid_tokens(self, tokens: list[str]) -> int:
        """
        Mark tokens as invalid in the database.

        Called when FCM returns NOT_FOUND or UNREGISTERED errors,
        indicating the token is no longer valid (app uninstalled,
        token refreshed, etc.).

        Args:
            tokens: List of FCM tokens to invalidate

        Returns:
            Number of tokens marked invalid
        """
        if not tokens:
            return 0

        from models.notification import PushToken

        result = await self.db.execute(
            update(PushToken)
            .where(PushToken.token.in_(tokens))
            .values(is_valid=False, updated_at=datetime.utcnow())
        )
        await self.db.commit()

        count = result.rowcount
        logger.info(f"Marked {count} tokens as invalid")
        return count

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    async def _filter_by_preferences(
        self,
        user_ids: list[str],
        preference_field: str | None,
    ) -> list[str]:
        """Filter users who have opted out of this notification type."""
        if preference_field is None:
            # Cannot opt out (emergency, transactions)
            return user_ids

        from models.notification import NotificationPreference

        # Get users with preferences that allow this notification
        stmt = select(NotificationPreference.user_id).where(
            NotificationPreference.user_id.in_(user_ids),
            NotificationPreference.push_enabled == True,
            getattr(NotificationPreference, preference_field) == True,
        )
        result = await self.db.execute(stmt)
        enabled_users = {row[0] for row in result.fetchall()}

        # Also include users without preferences (default enabled)
        from models.user import User
        stmt2 = select(User.id).where(
            User.id.in_(user_ids),
            ~User.id.in_(
                select(NotificationPreference.user_id)
            ),
        )
        result2 = await self.db.execute(stmt2)
        default_users = {row[0] for row in result2.fetchall()}

        return list(enabled_users | default_users)

    async def _apply_deduplication(
        self,
        user_ids: list[str],
        dedup_key: str,
        window_seconds: int | None = None,
    ) -> list[str]:
        """
        Deduplicate notifications within time window.

        Uses Redis to track recent notifications per user+key.
        Default window is from settings.fcm_dedup_window_seconds.
        """
        if not self.redis:
            return user_ids

        window_seconds = window_seconds or self.settings.fcm_dedup_window_seconds
        eligible = []
        now = datetime.utcnow().timestamp()

        for user_id in user_ids:
            cache_key = f"fcm:dedup:{user_id}:{dedup_key}"
            last_sent = await self.redis.get(cache_key)

            if last_sent is None:
                # Not sent recently
                await self.redis.setex(cache_key, window_seconds, str(now))
                eligible.append(user_id)
            else:
                logger.debug(f"Dedup: skipping {user_id} for {dedup_key}")

        return eligible

    async def _get_tokens_for_users(
        self,
        user_ids: list[str],
    ) -> dict[str, str]:
        """
        Get valid push tokens for users.

        Returns:
            Dict mapping token -> user_id
        """
        from models.notification import PushToken

        stmt = select(PushToken.token, PushToken.user_id).where(
            PushToken.user_id.in_(user_ids),
            PushToken.is_valid == True,
        )
        result = await self.db.execute(stmt)
        return {row[0]: row[1] for row in result.fetchall()}

    async def _send_multicast_batched(
        self,
        tokens: dict[str, str],
        title: str,
        body: str,
        data: dict[str, str] | None,
        image_url: str | None,
        config: NotificationConfig,
        notification_type: NotificationType,
    ) -> SendResult:
        """
        Send multicast message in batches of 500.

        FCM limits multicast to 500 tokens per request.
        This method handles batching and aggregates results.
        """
        try:
            from firebase_admin import messaging
        except ImportError:
            return SendResult(0, len(tokens), [], ["firebase-admin not installed"])

        token_list = list(tokens.keys())
        batch_size = self.settings.fcm_batch_size

        total_success = 0
        total_failure = 0
        invalid_tokens = []
        errors = []

        for i in range(0, len(token_list), batch_size):
            batch_tokens = token_list[i:i + batch_size]

            android_config = messaging.AndroidConfig(
                priority=config.priority,
                ttl=timedelta(seconds=config.ttl_seconds),
                notification=messaging.AndroidNotification(
                    channel_id=config.android_channel,
                    priority="high" if config.priority == "high" else "default",
                ),
                collapse_key=config.collapse_key,
            )

            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url,
            )

            batch_message = messaging.MulticastMessage(
                tokens=batch_tokens,
                notification=notification,
                data=data or {},
                android=android_config,
            )

            try:
                response = messaging.send_each_for_multicast(batch_message)

                for idx, send_response in enumerate(response.responses):
                    token = batch_tokens[idx]
                    user_id = tokens[token]

                    if send_response.success:
                        total_success += 1
                        await self._log_notification(
                            user_id=user_id,
                            notification_type=notification_type,
                            event_id=data.get("event_id") if data else None,
                            payload={"title": title},
                            fcm_message_id=send_response.message_id,
                            status="sent",
                        )
                    else:
                        total_failure += 1
                        error = send_response.exception

                        # Check for invalid token errors
                        error_str = str(error) if error else ""
                        if "NOT_FOUND" in error_str or "UNREGISTERED" in error_str:
                            invalid_tokens.append(token)

                        errors.append(f"Token {token[:20]}...: {error_str}")

                        await self._log_notification(
                            user_id=user_id,
                            notification_type=notification_type,
                            event_id=data.get("event_id") if data else None,
                            payload={"title": title},
                            fcm_message_id=None,
                            status="failed",
                            error_message=error_str,
                        )

            except Exception as e:
                error_msg = f"Batch send failed: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                total_failure += len(batch_tokens)

                # Log to Alert Manager for batch failures
                if self.alert_manager:
                    await self.alert_manager.system_error(
                        error=error_msg,
                        request_id=None,
                        traceback=str(e),
                    )

        # Clean up invalid tokens
        if invalid_tokens:
            await self.remove_invalid_tokens(invalid_tokens)

        logger.info(
            f"FCM send complete: type={notification_type.value} "
            f"success={total_success} failed={total_failure} "
            f"invalid_tokens={len(invalid_tokens)}"
        )

        return SendResult(
            success_count=total_success,
            failure_count=total_failure,
            invalid_tokens=invalid_tokens,
            errors=errors,
        )

    async def _subscribe_to_favorite_events(
        self,
        user_id: str,
        token: str,
    ) -> None:
        """Subscribe token to FCM topics for user's favorited events."""
        if not self._initialized:
            return

        try:
            from firebase_admin import messaging
            from models.engagement import UserFavorite
            from models.racer import Racer

            # Get unique event IDs from user's favorites
            stmt = (
                select(Racer.event_id)
                .join(UserFavorite, UserFavorite.racer_id == Racer.id)
                .where(UserFavorite.user_id == user_id)
                .distinct()
            )
            result = await self.db.execute(stmt)
            event_ids = [row[0] for row in result.fetchall()]

            for event_id in event_ids:
                topic = f"event_{event_id}"
                try:
                    messaging.subscribe_to_topic([token], topic)
                    logger.debug(f"Subscribed {user_id} to topic {topic}")
                except Exception as e:
                    logger.warning(f"Topic subscription failed: {e}")

        except Exception as e:
            logger.warning(f"Failed to subscribe to favorite events: {e}")

    async def _log_notification(
        self,
        user_id: str | None,
        notification_type: NotificationType,
        event_id: str | None,
        payload: dict,
        fcm_message_id: str | None,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Log notification to database for debugging and audit."""
        try:
            from models.notification import NotificationLog, NotificationStatus

            log_entry = NotificationLog(
                user_id=user_id,
                notification_type=notification_type.value,
                event_id=event_id,
                payload=payload,
                fcm_message_id=fcm_message_id,
                status=NotificationStatus(status),
                error_message=error_message,
            )
            self.db.add(log_entry)
            # Don't commit here - let caller manage transaction

        except Exception as e:
            logger.warning(f"Failed to log notification: {e}")
