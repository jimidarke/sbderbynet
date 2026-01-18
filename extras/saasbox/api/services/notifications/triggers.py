"""
Notification Triggers - Event-based notification dispatch.

This module contains the business logic for determining when and to whom
notifications should be sent. Triggers are called from:
- Sync handlers (when DerbyPi pushes race data)
- API endpoints (when users interact with polls, predictions)
- Background tasks (scheduled notifications)

Design Principles:
- Triggers are stateless - all state comes from database
- Triggers respect user preferences via FCMService
- Triggers handle their own deduplication logic
- Triggers are idempotent - safe to call multiple times

Usage:
    triggers = NotificationTriggers(db, redis, fcm_service)

    # Called from sync handler when heat schedule changes
    await triggers.on_heat_schedule_updated(event_id, current_heat_number, scheduled_heats)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from services.notifications.fcm_service import FCMService, NotificationType

if TYPE_CHECKING:
    from aioredis import Redis


logger = logging.getLogger(__name__)


@dataclass
class TriggerResult:
    """
    Result of a notification trigger operation.

    Attributes:
        sent: Number of notifications successfully sent
        skipped: Number of notifications skipped (dedupe, preference, error)
        errors: List of error messages if any
    """
    sent: int
    skipped: int
    errors: list[str] | None = None


class NotificationTriggers:
    """
    Event-based notification triggers for race events.

    This class encapsulates the business logic for:
    - Determining which users should receive notifications
    - Building notification content from event data
    - Coordinating with FCMService for delivery

    All triggers are idempotent and handle deduplication internally.
    """

    def __init__(
        self,
        db: AsyncSession,
        redis: "Redis | None" = None,
        fcm: FCMService | None = None,
        alert_manager: Any | None = None,
    ):
        """
        Initialize notification triggers.

        Args:
            db: Async SQLAlchemy session for database operations
            redis: Redis client for caching (optional)
            fcm: FCMService instance (will create if not provided)
            alert_manager: Alert Manager for error logging (optional)
        """
        self.db = db
        self.redis = redis
        self.alert_manager = alert_manager
        self.settings = get_settings()

        # Create FCMService if not provided
        if fcm is None:
            self.fcm = FCMService(db, redis, alert_manager)
        else:
            self.fcm = fcm

        self.staging_lookahead = self.settings.fcm_staging_lookahead_heats

    async def on_heat_schedule_updated(
        self,
        event_id: str,
        current_heat_number: int,
        scheduled_heats: list[dict],
    ) -> TriggerResult:
        """
        Trigger notifications when heat schedule is updated.

        Called by sync handler when DerbyPi pushes new schedule data.
        Sends staging notifications to users whose favorites are in
        the upcoming heats (current + next STAGING_LOOKAHEAD).

        Args:
            event_id: Event being updated
            current_heat_number: Currently active heat number
            scheduled_heats: List of heat dicts with racer assignments
                [{"heat_number": 5, "racers": [{"id": "rcr_x", "lane": 1}, ...]}]

        Returns:
            TriggerResult with notification counts
        """
        if not self.settings.fcm_enabled:
            return TriggerResult(sent=0, skipped=0)

        # Find heats within lookahead window
        lookahead_heats = [
            h for h in scheduled_heats
            if current_heat_number <= h["heat_number"] <= current_heat_number + self.staging_lookahead
        ]

        if not lookahead_heats:
            return TriggerResult(sent=0, skipped=0)

        # Collect racer IDs and their heat info
        racer_heat_map: dict[str, dict] = {}
        for heat in lookahead_heats:
            for racer in heat.get("racers", []):
                racer_id = racer["id"]
                if racer_id not in racer_heat_map:
                    racer_heat_map[racer_id] = {
                        "heat_number": heat["heat_number"],
                        "lane": racer["lane"],
                    }

        if not racer_heat_map:
            return TriggerResult(sent=0, skipped=0)

        # Find users who favorited these racers with staging notifications enabled
        from models.engagement import UserFavorite
        from models.racer import Racer

        racer_ids = list(racer_heat_map.keys())

        stmt = (
            select(UserFavorite, Racer)
            .join(Racer, UserFavorite.racer_id == Racer.id)
            .where(
                UserFavorite.racer_id.in_(racer_ids),
                UserFavorite.notify_upcoming == True,
            )
        )
        result = await self.db.execute(stmt)
        favorites = result.all()

        sent = 0
        skipped = 0
        errors = []

        # Group notifications by user
        user_notifications: dict[str, list[dict]] = {}
        for favorite, racer in favorites:
            heat_info = racer_heat_map.get(racer.id)
            if not heat_info:
                continue

            if favorite.user_id not in user_notifications:
                user_notifications[favorite.user_id] = []

            # PII protection: last initial only
            name = format_racer_name(racer.first_name, racer.last_name)

            user_notifications[favorite.user_id].append({
                "racer_id": racer.id,
                "name": name,
                "heat_number": heat_info["heat_number"],
                "lane": heat_info["lane"],
            })

        # Send notifications
        for user_id, racers in user_notifications.items():
            for racer_info in racers:
                try:
                    # Build notification content
                    heats_away = racer_info["heat_number"] - current_heat_number
                    title, body = build_staging_message(
                        racer_info["name"],
                        heats_away,
                        racer_info["lane"],
                    )

                    send_result = await self.fcm.send_to_users(
                        user_ids=[user_id],
                        notification_type=NotificationType.FAVORITE_STAGING,
                        title=title,
                        body=body,
                        data={
                            "event_id": event_id,
                            "heat_number": str(racer_info["heat_number"]),
                            "racer_id": racer_info["racer_id"],
                            "screen": "heat_detail",
                        },
                        dedup_key=f"staging_{racer_info['racer_id']}",
                    )

                    sent += send_result.success_count
                    skipped += send_result.failure_count

                    if send_result.errors:
                        errors.extend(send_result.errors)

                except Exception as e:
                    logger.error(f"Staging notification failed: {e}")
                    errors.append(str(e))
                    skipped += 1

        logger.info(
            f"Staging notifications: event={event_id} "
            f"sent={sent} skipped={skipped}"
        )
        return TriggerResult(sent=sent, skipped=skipped, errors=errors if errors else None)

    async def on_heat_completed(
        self,
        event_id: str,
        heat_id: str,
        results: list[dict],
    ) -> TriggerResult:
        """
        Trigger notifications when a heat completes with results.

        Sends result notifications to users who favorited racers in this heat.

        Args:
            event_id: Event ID
            heat_id: Completed heat ID
            results: List of result dicts
                [{"racer_id": "rcr_x", "place": 1, "time": 30.134}, ...]

        Returns:
            TriggerResult with notification counts
        """
        if not self.settings.fcm_enabled:
            return TriggerResult(sent=0, skipped=0)

        if not results:
            return TriggerResult(sent=0, skipped=0)

        from models.engagement import UserFavorite
        from models.racer import Racer

        racer_ids = [r["racer_id"] for r in results]
        result_map = {r["racer_id"]: r for r in results}

        # Find users who favorited these racers with result notifications enabled
        stmt = (
            select(UserFavorite, Racer)
            .join(Racer, UserFavorite.racer_id == Racer.id)
            .where(
                UserFavorite.racer_id.in_(racer_ids),
                UserFavorite.notify_results == True,
            )
        )
        result = await self.db.execute(stmt)
        favorites = result.all()

        sent = 0
        skipped = 0
        errors = []

        for favorite, racer in favorites:
            try:
                race_result = result_map.get(racer.id)
                if not race_result:
                    continue

                place = race_result.get("place")
                time_val = race_result.get("time")
                name = format_racer_name(racer.first_name, racer.last_name)

                title, body = build_result_message(name, place, time_val)

                send_result = await self.fcm.send_to_users(
                    user_ids=[favorite.user_id],
                    notification_type=NotificationType.FAVORITE_RESULT,
                    title=title,
                    body=body,
                    data={
                        "event_id": event_id,
                        "heat_id": heat_id,
                        "racer_id": racer.id,
                        "screen": "results",
                    },
                    dedup_key=f"result_{heat_id}_{racer.id}",
                )

                sent += send_result.success_count
                skipped += send_result.failure_count

                if send_result.errors:
                    errors.extend(send_result.errors)

            except Exception as e:
                logger.error(f"Result notification failed: {e}")
                errors.append(str(e))
                skipped += 1

        logger.info(
            f"Result notifications: event={event_id} heat={heat_id} "
            f"sent={sent} skipped={skipped}"
        )
        return TriggerResult(sent=sent, skipped=skipped, errors=errors if errors else None)

    async def on_poll_activated(
        self,
        event_id: str,
        poll_id: str,
        question: str,
    ) -> TriggerResult:
        """
        Trigger notification when a new poll is activated.

        Sends to all users who have favorites at this event.
        """
        if not self.settings.fcm_enabled:
            return TriggerResult(sent=0, skipped=0)

        from models.engagement import UserFavorite
        from models.racer import Racer

        # Get users at this event (have favorites in this event)
        stmt = (
            select(UserFavorite.user_id)
            .join(Racer, UserFavorite.racer_id == Racer.id)
            .where(Racer.event_id == event_id)
            .distinct()
        )
        result = await self.db.execute(stmt)
        user_ids = [row[0] for row in result.fetchall()]

        if not user_ids:
            return TriggerResult(sent=0, skipped=0)

        title, body = build_poll_new_message(question)

        send_result = await self.fcm.send_to_users(
            user_ids=user_ids,
            notification_type=NotificationType.POLL_NEW,
            title=title,
            body=body,
            data={
                "event_id": event_id,
                "poll_id": poll_id,
                "screen": "poll_vote",
            },
        )

        logger.info(
            f"Poll activation notifications: event={event_id} poll={poll_id} "
            f"sent={send_result.success_count} skipped={send_result.failure_count}"
        )
        return TriggerResult(
            sent=send_result.success_count,
            skipped=send_result.failure_count,
            errors=send_result.errors if send_result.errors else None,
        )

    async def on_poll_closed(
        self,
        event_id: str,
        poll_id: str,
        question: str,
        winner_label: str,
    ) -> TriggerResult:
        """
        Trigger notification when poll results are available.

        Notifies users who voted in this poll.
        """
        if not self.settings.fcm_enabled:
            return TriggerResult(sent=0, skipped=0)

        from models.engagement import PollVote

        # Notify users who voted in this poll
        stmt = (
            select(PollVote.user_id)
            .where(PollVote.poll_id == poll_id)
            .distinct()
        )
        result = await self.db.execute(stmt)
        user_ids = [row[0] for row in result.fetchall()]

        if not user_ids:
            return TriggerResult(sent=0, skipped=0)

        title, body = build_poll_result_message(winner_label)

        send_result = await self.fcm.send_to_users(
            user_ids=user_ids,
            notification_type=NotificationType.POLL_RESULT,
            title=title,
            body=body,
            data={
                "event_id": event_id,
                "poll_id": poll_id,
                "screen": "poll_results",
            },
        )

        logger.info(
            f"Poll result notifications: event={event_id} poll={poll_id} "
            f"sent={send_result.success_count} skipped={send_result.failure_count}"
        )
        return TriggerResult(
            sent=send_result.success_count,
            skipped=send_result.failure_count,
            errors=send_result.errors if send_result.errors else None,
        )

    async def on_prediction_resolved(
        self,
        user_id: str,
        event_id: str,
        heat_id: str,
        was_correct: bool,
        points_earned: int,
    ) -> TriggerResult:
        """
        Trigger notification when user's prediction is resolved.
        """
        if not self.settings.fcm_enabled:
            return TriggerResult(sent=0, skipped=0)

        title, body = build_prediction_result_message(was_correct, points_earned)

        send_result = await self.fcm.send_to_users(
            user_ids=[user_id],
            notification_type=NotificationType.PREDICTION_RESULT,
            title=title,
            body=body,
            data={
                "event_id": event_id,
                "heat_id": heat_id,
                "screen": "prediction_stats",
            },
        )

        logger.info(
            f"Prediction notification: user={user_id} heat={heat_id} "
            f"correct={was_correct} sent={send_result.success_count}"
        )
        return TriggerResult(
            sent=send_result.success_count,
            skipped=send_result.failure_count,
            errors=send_result.errors if send_result.errors else None,
        )

    async def on_purchase_completed(
        self,
        user_id: str,
        purchase_type: str,
        amount: str,
        receipt_id: str,
    ) -> TriggerResult:
        """
        Trigger purchase confirmation notification.

        Cannot be opted out of - transactional notification.
        """
        if not self.settings.fcm_enabled:
            return TriggerResult(sent=0, skipped=0)

        title, body = build_purchase_message(purchase_type, amount)

        send_result = await self.fcm.send_to_users(
            user_ids=[user_id],
            notification_type=NotificationType.PURCHASE_CONFIRM,
            title=title,
            body=body,
            data={
                "receipt_id": receipt_id,
                "screen": "receipt",
            },
        )

        logger.info(
            f"Purchase notification: user={user_id} type={purchase_type} "
            f"sent={send_result.success_count}"
        )
        return TriggerResult(
            sent=send_result.success_count,
            skipped=send_result.failure_count,
            errors=send_result.errors if send_result.errors else None,
        )


# -----------------------------------------------------------------------------
# Message Template Functions
# -----------------------------------------------------------------------------

# Character limits per FCM_NOTIFICATION_PLAN.md Section 6.2
MAX_TITLE_CHARS = 50
MAX_BODY_CHARS = 100


def format_racer_name(first_name: str, last_name: str) -> str:
    """
    Format racer name for PII protection.

    Per FCM_NOTIFICATION_PLAN.md Section 1.3, notifications must not
    contain child last names visible on lock screens.

    Returns format: "FirstName L." (e.g., "Jane S.")
    """
    if not last_name:
        return first_name
    return f"{first_name} {last_name[0]}."


def format_time(seconds: float | None) -> str:
    """Format race time as mm:ss.nnn or 'DNF'."""
    if seconds is None:
        return "DNF"
    if seconds >= 99.999:
        return "DNF"
    minutes = int(seconds // 60)
    remaining = seconds % 60
    return f"{minutes:02d}:{remaining:06.3f}"


def truncate(text: str, max_len: int) -> str:
    """Truncate text to max length with ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def build_staging_message(name: str, heats_away: int, lane: int) -> tuple[str, str]:
    """
    Build staging notification title and body.

    Returns:
        Tuple of (title, body)
    """
    if heats_away == 0:
        title = f"{name} is racing NOW!"
        body = f"Lane {lane}"
    elif heats_away == 1:
        title = f"{name} is racing soon!"
        body = f"Up next! Lane {lane}"
    else:
        title = f"{name} is racing soon!"
        body = f"~{heats_away} heats away - Lane {lane}"

    return truncate(title, MAX_TITLE_CHARS), truncate(body, MAX_BODY_CHARS)


def build_result_message(
    name: str, place: int | None, time_val: float | None
) -> tuple[str, str]:
    """
    Build result notification title and body.

    Returns:
        Tuple of (title, body)
    """
    time_str = format_time(time_val)

    if place == 1:
        title = f"{name} won!"
        body = f"1st place - {time_str}"
    elif place == 2:
        title = f"{name} finished 2nd"
        body = f"2nd place - {time_str}"
    elif place == 3:
        title = f"{name} finished 3rd"
        body = f"3rd place - {time_str}"
    else:
        title = f"{name} finished"
        body = f"Time: {time_str}"

    return truncate(title, MAX_TITLE_CHARS), truncate(body, MAX_BODY_CHARS)


def build_poll_new_message(question: str) -> tuple[str, str]:
    """Build new poll notification title and body."""
    title = "New Poll Available!"
    body = truncate(question, MAX_BODY_CHARS)
    return title, body


def build_poll_result_message(winner_label: str) -> tuple[str, str]:
    """Build poll result notification title and body."""
    title = "Poll Results Are In!"
    body = truncate(f"Winner: {winner_label}", MAX_BODY_CHARS)
    return title, body


def build_prediction_result_message(
    was_correct: bool, points_earned: int
) -> tuple[str, str]:
    """Build prediction result notification title and body."""
    if was_correct:
        title = "Prediction Correct!"
        body = f"You earned {points_earned} points!"
    else:
        title = "Better luck next time!"
        body = "Keep predicting to climb the leaderboard"

    return truncate(title, MAX_TITLE_CHARS), truncate(body, MAX_BODY_CHARS)


def build_purchase_message(purchase_type: str, amount: str) -> tuple[str, str]:
    """Build purchase confirmation notification title and body."""
    title = "Purchase Confirmed"
    body = truncate(f"{purchase_type} - {amount}", MAX_BODY_CHARS)
    return title, body
