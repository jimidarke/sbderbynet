# FCM Push Notification Architecture Plan

**Version:** 1.2.0
**Date:** 2026-01-16
**Status:** Phases 1, 2, 3 Complete - Ready for Flutter Integration (Phase 4)
**Parent Document:** [ENTERPRISE_ROADMAP.md](/ENTERPRISE_ROADMAP.md)

---

## Executive Summary

This document defines the Firebase Cloud Messaging (FCM) push notification architecture for the SoapboxDerbyNet premium SaaS service. The system enables real-time engagement with race event attendees through targeted, privacy-conscious notifications.

### Scope

| Item | Status |
|------|--------|
| **Platform** | Android (Phase 1), iOS (Phase 2 - next year) |
| **Deployment** | Cloud-only (premium SaaS feature) |
| **Integration** | Aligns with LED sign emergency broadcasts |
| **Advertising** | None - no promotional content |

### Key Design Decisions (Per Stakeholder Input)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Staging notification timing** | When racer is within 5 heats | Gives parents time to move to viewing area |
| **Emergency broadcast authority** | Race Coordinator only | Single authority, aligns with LED sign system |
| **Notification scope** | Favorites only | Reduces noise, respects user attention |
| **Alert Manager integration** | Errors only | Log failures for troubleshooting, not every send |

---

## Table of Contents

1. [Notification Categories](#1-notification-categories)
2. [System Architecture](#2-system-architecture)
3. [Database Schema](#3-database-schema)
4. [FCM Service Design](#4-fcm-service-design)
5. [Notification Triggers](#5-notification-triggers)
6. [Message Templates](#6-message-templates)
7. [User Preferences](#7-user-preferences)
8. [Flutter Client Integration](#8-flutter-client-integration)
9. [Emergency Broadcast System](#9-emergency-broadcast-system)
10. [API Endpoints](#10-api-endpoints)
11. [Implementation Roadmap](#11-implementation-roadmap) ⬅️ **Current Progress**
12. [Testing Strategy](#12-testing-strategy)
13. [References](#13-references)
14. [SaaS API Context](#14-saas-api-context)

---

## 1. Notification Categories

### 1.1 Notification Type Matrix

| ID | Category | Trigger | Priority | User Opt-out | Deep Link Target |
|----|----------|---------|----------|--------------|------------------|
| `NTF-FAV-STAGING` | Favorite Racer Staging | Racer within 5 heats | HIGH | Yes | Heat detail screen |
| `NTF-FAV-RESULT` | Favorite Racer Result | Heat completes | NORMAL | Yes | Results screen |
| `NTF-POLL-NEW` | New Poll Available | Poll activated | NORMAL | Yes | Poll voting screen |
| `NTF-POLL-RESULT` | Poll Results Ready | Poll closes | NORMAL | Yes | Poll results screen |
| `NTF-PRED-RESULT` | Prediction Outcome | Heat resolves | NORMAL | Yes | Prediction stats |
| `NTF-PURCHASE` | Purchase Confirmation | Payment succeeds | HIGH | No | Receipt screen |
| `NTF-EMERGENCY` | Emergency Broadcast | Coordinator action | HIGH | No | Alert modal |

### 1.2 Priority Definitions

| Priority | FCM Setting | Battery Impact | Use Case |
|----------|-------------|----------------|----------|
| **HIGH** | `high` | Wakes device from Doze | Time-sensitive: staging, emergency, payments |
| **NORMAL** | `normal` | Batched delivery | Results, polls, predictions |

### 1.3 PII Protection Rules

**CRITICAL**: Notifications must not contain child PII that could be visible on lock screens.

| Data | In Notification | In Data Payload | Notes |
|------|-----------------|-----------------|-------|
| Racer first name | Yes (parent opted-in) | Yes | User favorited this racer |
| Racer last name | **NO** (last initial only) | Yes | "JohnS" format |
| Pinny number | Yes | Yes | Public identifier |
| Race times | Yes | Yes | Public data |
| Full name | **NO** | **NO** | Never in notifications |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        FCM NOTIFICATION ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌────────────────┐                                                             │
│   │  DerbyPi       │                                                             │
│   │  (On-Premise)  │                                                             │
│   └───────┬────────┘                                                             │
│           │ Sync race data                                                       │
│           ▼                                                                      │
│   ┌────────────────────────────────────────────────────────────────────────┐    │
│   │                    SaaS API Server (FastAPI)                            │    │
│   │                                                                         │    │
│   │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │    │
│   │  │  Sync Handler   │  │  Event Triggers │  │  FCM Service    │        │    │
│   │  │  (Device Auth)  │──│  (Heat staged,  │──│  (firebase-admin│        │    │
│   │  │                 │  │   results, etc) │  │   SDK)          │        │    │
│   │  └─────────────────┘  └─────────────────┘  └────────┬────────┘        │    │
│   │                                                      │                 │    │
│   │  ┌─────────────────┐  ┌─────────────────┐           │                 │    │
│   │  │  PostgreSQL     │  │  Redis          │           │                 │    │
│   │  │  - push_tokens  │  │  - rate limits  │           │                 │    │
│   │  │  - preferences  │  │  - dedup cache  │           │                 │    │
│   │  │  - favorites    │  │                 │           │                 │    │
│   │  └─────────────────┘  └─────────────────┘           │                 │    │
│   │                                                      │                 │    │
│   └──────────────────────────────────────────────────────┼─────────────────┘    │
│                                                          │                       │
│                                                          ▼                       │
│   ┌────────────────────────────────────────────────────────────────────────┐    │
│   │                    Firebase Cloud Messaging                             │    │
│   │                    (FCM HTTP v1 API)                                    │    │
│   └────────────────────────────────────────────────────────────────────────┘    │
│                              │                                                   │
│              ┌───────────────┼───────────────┐                                  │
│              ▼               ▼               ▼                                  │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                         │
│   │   Android    │  │   Android    │  │   iOS        │                         │
│   │   Device 1   │  │   Device 2   │  │   (Phase 2)  │                         │
│   │   (Flutter)  │  │   (Flutter)  │  │              │                         │
│   └──────────────┘  └──────────────┘  └──────────────┘                         │
│                                                                                  │
│   ┌────────────────────────────────────────────────────────────────────────┐    │
│   │  Alert Manager (Errors Only)                                            │    │
│   │  - FCM delivery failures                                                │    │
│   │  - Invalid token cleanup events                                         │    │
│   │  - Rate limit violations                                                │    │
│   └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow: Favorite Racer Staging Notification

```
1. DerbyPi syncs heat schedule to SaaS API
   POST /v1/orgs/{orgId}/events/{eventId}/sync

2. SyncHandler detects new heat staged
   → Extracts racer IDs in upcoming heats (current + next 5)

3. NotificationTrigger queries favorites
   SELECT user_id, push_token FROM user_favorites
   JOIN push_tokens ON user_favorites.user_id = push_tokens.user_id
   WHERE racer_id IN (...) AND notify_upcoming = true

4. FCMService builds multicast message
   → Groups by event, respects user preferences
   → Applies deduplication (Redis: 5-min window per user+racer)

5. FCMService sends via firebase-admin SDK
   messaging.send_each_for_multicast(message)

6. Handle responses
   → Log failures to Alert Manager
   → Remove invalid tokens
   → Update delivery stats
```

### 2.3 Integration with LED Sign Emergency Broadcasts

Emergency broadcasts align with the [LED Sign Integration Plan](/extras/ledsign/LED_SIGN_INTEGRATION_PLAN.md):

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    EMERGENCY BROADCAST INTEGRATION                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   Race Coordinator                                                               │
│   (Web Interface)                                                                │
│        │                                                                         │
│        │ POST /v1/emergency/broadcast                                            │
│        │ {message: "...", severity: "emergency"}                                 │
│        │                                                                         │
│        ▼                                                                         │
│   ┌────────────────────────────────────────────────────────────────────────┐    │
│   │                    EmergencyBroadcastService                            │    │
│   │                                                                         │    │
│   │  ┌─────────────────────────────────────────────────────────────────┐   │    │
│   │  │ 1. Validate coordinator role (JWT check)                        │   │    │
│   │  │ 2. Log to audit trail                                           │   │    │
│   │  │ 3. Dispatch to both channels:                                   │   │    │
│   │  └─────────────────────────────────────────────────────────────────┘   │    │
│   │              │                              │                           │    │
│   │              ▼                              ▼                           │    │
│   │   ┌─────────────────────┐      ┌─────────────────────┐                 │    │
│   │   │  MQTT Publish       │      │  FCM Topic Message  │                 │    │
│   │   │  derbynet/ledsign/  │      │  Topic: emergency_  │                 │    │
│   │   │  broadcast          │      │  {org_id}_{event_id}│                 │    │
│   │   └─────────────────────┘      └─────────────────────┘                 │    │
│   │              │                              │                           │    │
│   │              ▼                              ▼                           │    │
│   │   ┌─────────────────────┐      ┌─────────────────────┐                 │    │
│   │   │  ALL LED Signs      │      │  ALL App Users      │                 │    │
│   │   │  (On-premise)       │      │  (At event)         │                 │    │
│   │   │                     │      │                     │                 │    │
│   │   │  Red flash,         │      │  High priority,     │                 │    │
│   │   │  full screen        │      │  heads-up display   │                 │    │
│   │   └─────────────────────┘      └─────────────────────┘                 │    │
│   │                                                                         │    │
│   └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│   Note: Emergency broadcasts cannot be opted out of by users                     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Database Schema

### 3.1 New Tables

```sql
-- Push token registration table
CREATE TABLE push_tokens (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    device_type VARCHAR(20) NOT NULL CHECK (device_type IN ('android', 'ios', 'web')),
    device_id VARCHAR(100) NOT NULL,  -- Client-generated UUID for device
    app_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    is_valid BOOLEAN DEFAULT TRUE,

    CONSTRAINT unique_user_device UNIQUE (user_id, device_id)
);

CREATE INDEX idx_push_tokens_user ON push_tokens(user_id);
CREATE INDEX idx_push_tokens_valid ON push_tokens(is_valid) WHERE is_valid = TRUE;

-- User notification preferences
CREATE TABLE notification_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,

    -- Global settings
    push_enabled BOOLEAN DEFAULT TRUE,
    quiet_hours_enabled BOOLEAN DEFAULT FALSE,
    quiet_hours_start TIME,  -- e.g., 22:00
    quiet_hours_end TIME,    -- e.g., 08:00

    -- Category settings
    favorite_staging_enabled BOOLEAN DEFAULT TRUE,
    favorite_results_enabled BOOLEAN DEFAULT TRUE,
    poll_notifications_enabled BOOLEAN DEFAULT TRUE,
    prediction_results_enabled BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Notification delivery log (for debugging, retained 30 days)
CREATE TABLE notification_log (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(20),
    notification_type VARCHAR(50) NOT NULL,
    event_id VARCHAR(20),
    payload JSONB,
    fcm_message_id VARCHAR(100),
    status VARCHAR(20) NOT NULL CHECK (status IN ('sent', 'failed', 'skipped')),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notification_log_user ON notification_log(user_id, created_at DESC);
CREATE INDEX idx_notification_log_status ON notification_log(status, created_at DESC);

-- Partition by month for efficient cleanup
-- (Implementation detail: add partition management)
```

### 3.2 Updates to Existing Tables

```sql
-- Add FCM topic subscription tracking to users
ALTER TABLE users ADD COLUMN fcm_topics JSONB DEFAULT '[]';
-- Example: ["event_evt_abc123", "emergency_org_xyz"]

-- Add notification_sent_at to track last notification per favorite
ALTER TABLE user_favorites ADD COLUMN last_staging_notified_at TIMESTAMP;
ALTER TABLE user_favorites ADD COLUMN last_result_notified_at TIMESTAMP;
```

---

## 4. FCM Service Design

### 4.1 Module Structure

```
extras/saasbox/api/
├── services/
│   └── notifications/
│       ├── __init__.py
│       ├── fcm_service.py      # Core FCM client wrapper
│       ├── notification_types.py    # Notification type definitions
│       ├── templates.py        # Message templates
│       ├── triggers.py         # Event-based triggers
│       └── preferences.py      # User preference handling
```

### 4.2 FCM Service Implementation

```python
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

Usage:
    from services.notifications.fcm_service import FCMService

    fcm = FCMService()
    await fcm.send_to_users(
        user_ids=["usr_abc", "usr_xyz"],
        notification_type=NotificationType.FAVORITE_STAGING,
        title="John S. is racing soon!",
        body="Heat 5 - Lane 2",
        data={"event_id": "evt_123", "heat_id": "ht_456"}
    )

References:
- FCM HTTP v1 API: https://firebase.google.com/docs/cloud-messaging/send/v1-api
- firebase-admin SDK: https://firebase.google.com/docs/cloud-messaging/send/admin-sdk
- Migration guide: https://firebase.google.com/docs/cloud-messaging/migrate-v1
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from middleware.logging import AlertManager


logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """
    Enumeration of all notification types supported by the system.

    Each type maps to specific:
    - FCM priority level (high/normal)
    - User preference flag for opt-out
    - Deep link target in Flutter app
    - Template for title/body generation

    Attributes:
        FAVORITE_STAGING: Favorite racer within 5 heats of racing
        FAVORITE_RESULT: Favorite racer's heat completed with results
        POLL_NEW: New audience poll activated
        POLL_RESULT: Poll voting closed, results available
        PREDICTION_RESULT: User's heat prediction resolved
        PURCHASE_CONFIRM: Digital purchase confirmation
        EMERGENCY: Emergency broadcast from coordinator
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

    def __init__(
        self,
        db: AsyncSession,
        redis: Any,  # aioredis.Redis
        alert_manager: AlertManager | None = None,
    ):
        """
        Initialize FCM service with database and cache connections.

        Args:
            db: Async SQLAlchemy session for database operations
            redis: Redis client for rate limiting and deduplication
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
        if settings.firebase_credentials_path:
            cred = credentials.Certificate(settings.firebase_credentials_path)
            firebase_admin.initialize_app(cred)
            cls._initialized = True
            logger.info("Firebase Admin SDK initialized for FCM")
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

        Raises:
            ValueError: If notification_type is invalid

        Example:
            ```python
            result = await fcm.send_to_users(
                user_ids=["usr_abc", "usr_xyz"],
                notification_type=NotificationType.FAVORITE_STAGING,
                title="Jane S. is racing soon!",
                body="Heat 12, Lane 1",
                data={
                    "screen": "heat_detail",
                    "event_id": "evt_123",
                    "heat_id": "ht_456",
                },
                dedup_key="staging_rcr_789",  # Dedupe per racer
            )

            if result.invalid_tokens:
                await fcm.remove_invalid_tokens(result.invalid_tokens)
            ```

        Note:
            - Title should not contain child last names (PII protection)
            - Data values must be strings (FCM requirement)
            - High priority notifications may wake device from Doze mode
        """
        if not self._initialized:
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

        # Apply deduplication
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

        # Build FCM message
        message = self._build_multicast_message(
            tokens=list(tokens.keys()),
            title=title,
            body=body,
            data=data,
            image_url=image_url,
            config=config,
        )

        # Send in batches of 500
        return await self._send_multicast_batched(message, tokens, notification_type)

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

        Example:
            ```python
            result = await fcm.send_emergency_broadcast(
                event_id="evt_xyz",
                message="Weather delay - seek shelter immediately",
                coordinator_id="usr_coordinator",
            )
            ```

        Security:
            Authorization check must be performed by caller.
            Only Race Coordinators should call this method.
        """
        if not self._initialized:
            return SendResult(0, 0, [], ["FCM not initialized"])

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

        try:
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
                await self.alert_manager.send_alert(
                    level="critical",
                    category="application",
                    title="FCM Emergency Broadcast Failed",
                    message=error_msg,
                    metadata={
                        "event_id": event_id,
                        "coordinator_id": coordinator_id,
                    },
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

        Example:
            ```python
            success = await fcm.register_token(
                user_id="usr_abc123",
                token="fcm_token_here...",
                device_type="android",
                device_id="device-uuid-1234",
                app_version="1.2.3",
            )
            ```

        Note:
            Also subscribes user to event topics for their favorited events.
        """
        from models.engagement import PushToken  # Avoid circular import

        try:
            stmt = """
                INSERT INTO push_tokens
                (user_id, token, device_type, device_id, app_version, updated_at)
                VALUES (:user_id, :token, :device_type, :device_id, :app_version, NOW())
                ON CONFLICT (user_id, device_id)
                DO UPDATE SET
                    token = :token,
                    device_type = :device_type,
                    app_version = :app_version,
                    updated_at = NOW(),
                    is_valid = TRUE
            """
            await self.db.execute(
                stmt,
                {
                    "user_id": user_id,
                    "token": token,
                    "device_type": device_type,
                    "device_id": device_id,
                    "app_version": app_version,
                },
            )
            await self.db.commit()

            # Subscribe to event topics for user's favorites
            await self._subscribe_to_favorite_events(user_id, token)

            logger.info(f"Push token registered: user={user_id} device={device_id}")
            return True

        except Exception as e:
            logger.error(f"Token registration failed: {e}")
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

        # Query users with push_enabled=True AND specific preference=True
        stmt = f"""
            SELECT user_id FROM notification_preferences
            WHERE user_id = ANY(:user_ids)
            AND push_enabled = TRUE
            AND {preference_field} = TRUE
        """
        result = await self.db.execute(stmt, {"user_ids": user_ids})
        enabled_users = {row[0] for row in result.fetchall()}

        # Also include users without preferences (default enabled)
        stmt2 = """
            SELECT id FROM users
            WHERE id = ANY(:user_ids)
            AND id NOT IN (SELECT user_id FROM notification_preferences)
        """
        result2 = await self.db.execute(stmt2, {"user_ids": user_ids})
        default_users = {row[0] for row in result2.fetchall()}

        return list(enabled_users | default_users)

    async def _apply_deduplication(
        self,
        user_ids: list[str],
        dedup_key: str,
        window_seconds: int = 300,
    ) -> list[str]:
        """
        Deduplicate notifications within time window.

        Uses Redis to track recent notifications per user+key.
        Default window is 5 minutes.
        """
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
        stmt = """
            SELECT token, user_id FROM push_tokens
            WHERE user_id = ANY(:user_ids)
            AND is_valid = TRUE
        """
        result = await self.db.execute(stmt, {"user_ids": user_ids})
        return {row[0]: row[1] for row in result.fetchall()}

    def _build_multicast_message(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: dict[str, str] | None,
        image_url: str | None,
        config: NotificationConfig,
    ) -> messaging.MulticastMessage:
        """Build FCM multicast message with platform-specific config."""

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

        return messaging.MulticastMessage(
            tokens=tokens,
            notification=notification,
            data=data or {},
            android=android_config,
        )

    async def _send_multicast_batched(
        self,
        message: messaging.MulticastMessage,
        token_user_map: dict[str, str],
        notification_type: NotificationType,
    ) -> SendResult:
        """
        Send multicast message in batches of 500.

        FCM limits multicast to 500 tokens per request.
        This method handles batching and aggregates results.
        """
        tokens = list(token_user_map.keys())
        batch_size = 500

        total_success = 0
        total_failure = 0
        invalid_tokens = []
        errors = []

        for i in range(0, len(tokens), batch_size):
            batch_tokens = tokens[i:i + batch_size]
            batch_message = messaging.MulticastMessage(
                tokens=batch_tokens,
                notification=message.notification,
                data=message.data,
                android=message.android,
            )

            try:
                response = messaging.send_each_for_multicast(batch_message)

                for idx, send_response in enumerate(response.responses):
                    token = batch_tokens[idx]
                    user_id = token_user_map[token]

                    if send_response.success:
                        total_success += 1
                        await self._log_notification(
                            user_id=user_id,
                            notification_type=notification_type,
                            event_id=message.data.get("event_id"),
                            payload={"title": message.notification.title},
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
                            event_id=message.data.get("event_id"),
                            payload={"title": message.notification.title},
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
                    await self.alert_manager.send_alert(
                        level="warning",
                        category="application",
                        title="FCM Batch Send Failed",
                        message=error_msg,
                        metadata={
                            "notification_type": notification_type.value,
                            "batch_size": len(batch_tokens),
                        },
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
        # Get unique event IDs from user's favorites
        stmt = """
            SELECT DISTINCT r.event_id
            FROM user_favorites uf
            JOIN racers r ON uf.racer_id = r.id
            WHERE uf.user_id = :user_id
        """
        result = await self.db.execute(stmt, {"user_id": user_id})
        event_ids = [row[0] for row in result.fetchall()]

        for event_id in event_ids:
            topic = f"event_{event_id}"
            try:
                messaging.subscribe_to_topic([token], topic)
                logger.debug(f"Subscribed {user_id} to topic {topic}")
            except Exception as e:
                logger.warning(f"Topic subscription failed: {e}")

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
            stmt = """
                INSERT INTO notification_log
                (user_id, notification_type, event_id, payload,
                 fcm_message_id, status, error_message, created_at)
                VALUES (:user_id, :notification_type, :event_id, :payload,
                        :fcm_message_id, :status, :error_message, NOW())
            """
            await self.db.execute(
                stmt,
                {
                    "user_id": user_id,
                    "notification_type": notification_type.value,
                    "event_id": event_id,
                    "payload": payload,
                    "fcm_message_id": fcm_message_id,
                    "status": status,
                    "error_message": error_message,
                },
            )
            # Don't commit here - let caller manage transaction
        except Exception as e:
            logger.warning(f"Failed to log notification: {e}")
```

---

## 5. Notification Triggers

### 5.1 Trigger Module

```python
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
    await triggers.on_heat_schedule_updated(event_id, scheduled_heats)
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from services.notifications.fcm_service import FCMService, NotificationType


class NotificationTriggers:
    """
    Event-based notification triggers for race events.

    This class encapsulates the business logic for:
    - Determining which users should receive notifications
    - Building notification content from event data
    - Coordinating with FCMService for delivery

    Attributes:
        STAGING_LOOKAHEAD: Number of heats to look ahead for staging notifications
    """

    STAGING_LOOKAHEAD = 5  # Notify when racer within 5 heats

    def __init__(
        self,
        db: AsyncSession,
        redis: Any,
        fcm: FCMService,
    ):
        self.db = db
        self.redis = redis
        self.fcm = fcm

    async def on_heat_schedule_updated(
        self,
        event_id: str,
        current_heat_number: int,
        scheduled_heats: list[dict],
    ) -> dict[str, int]:
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
            Dict with notification counts: {"sent": N, "skipped": M}

        Example:
            ```python
            result = await triggers.on_heat_schedule_updated(
                event_id="evt_abc",
                current_heat_number=10,
                scheduled_heats=[
                    {"heat_number": 11, "racers": [...]},
                    {"heat_number": 12, "racers": [...]},
                ]
            )
            ```
        """
        # Find heats within lookahead window
        lookahead_heats = [
            h for h in scheduled_heats
            if current_heat_number <= h["heat_number"] <= current_heat_number + self.STAGING_LOOKAHEAD
        ]

        if not lookahead_heats:
            return {"sent": 0, "skipped": 0}

        # Collect racer IDs and their heat info
        racer_heat_map = {}
        for heat in lookahead_heats:
            for racer in heat.get("racers", []):
                racer_id = racer["id"]
                if racer_id not in racer_heat_map:
                    racer_heat_map[racer_id] = {
                        "heat_number": heat["heat_number"],
                        "lane": racer["lane"],
                    }

        if not racer_heat_map:
            return {"sent": 0, "skipped": 0}

        # Find users who favorited these racers with staging notifications enabled
        racer_ids = list(racer_heat_map.keys())
        stmt = """
            SELECT uf.user_id, uf.racer_id, r.first_name, r.last_name
            FROM user_favorites uf
            JOIN racers r ON uf.racer_id = r.id
            WHERE uf.racer_id = ANY(:racer_ids)
            AND uf.notify_upcoming = TRUE
        """
        result = await self.db.execute(stmt, {"racer_ids": racer_ids})
        favorites = result.fetchall()

        sent = 0
        skipped = 0

        # Group by user to potentially batch notifications
        user_notifications = {}
        for user_id, racer_id, first_name, last_name in favorites:
            heat_info = racer_heat_map[racer_id]

            if user_id not in user_notifications:
                user_notifications[user_id] = []

            user_notifications[user_id].append({
                "racer_id": racer_id,
                "name": f"{first_name} {last_name[0]}.",  # Privacy: last initial only
                "heat_number": heat_info["heat_number"],
                "lane": heat_info["lane"],
            })

        # Send individual notifications (could optimize to batch later)
        for user_id, racers in user_notifications.items():
            for racer in racers:
                # Build notification
                heats_away = racer["heat_number"] - current_heat_number
                if heats_away == 0:
                    body = f"Racing NOW - Lane {racer['lane']}"
                elif heats_away == 1:
                    body = f"Up next! Lane {racer['lane']}"
                else:
                    body = f"~{heats_away} heats away - Lane {racer['lane']}"

                send_result = await self.fcm.send_to_users(
                    user_ids=[user_id],
                    notification_type=NotificationType.FAVORITE_STAGING,
                    title=f"{racer['name']} is racing soon!",
                    body=body,
                    data={
                        "event_id": event_id,
                        "heat_number": str(racer["heat_number"]),
                        "racer_id": racer["racer_id"],
                        "screen": "heat_detail",
                    },
                    dedup_key=f"staging_{racer['racer_id']}",
                )

                sent += send_result.success_count
                skipped += send_result.failure_count

        return {"sent": sent, "skipped": skipped}

    async def on_heat_completed(
        self,
        event_id: str,
        heat_id: str,
        results: list[dict],
    ) -> dict[str, int]:
        """
        Trigger notifications when a heat completes with results.

        Sends result notifications to users who favorited racers in this heat.

        Args:
            event_id: Event ID
            heat_id: Completed heat ID
            results: List of result dicts
                [{"racer_id": "rcr_x", "place": 1, "time": 30.134}, ...]

        Returns:
            Dict with notification counts
        """
        if not results:
            return {"sent": 0, "skipped": 0}

        racer_ids = [r["racer_id"] for r in results]

        # Create lookup for results
        result_map = {r["racer_id"]: r for r in results}

        # Find users who favorited these racers
        stmt = """
            SELECT uf.user_id, uf.racer_id, r.first_name, r.last_name
            FROM user_favorites uf
            JOIN racers r ON uf.racer_id = r.id
            WHERE uf.racer_id = ANY(:racer_ids)
            AND uf.notify_results = TRUE
        """
        result = await self.db.execute(stmt, {"racer_ids": racer_ids})
        favorites = result.fetchall()

        sent = 0
        skipped = 0

        for user_id, racer_id, first_name, last_name in favorites:
            race_result = result_map[racer_id]
            place = race_result.get("place")
            time_val = race_result.get("time")

            # Build notification
            name = f"{first_name} {last_name[0]}."

            if place == 1:
                title = f"{name} won! 🏆"
                body = f"1st place - {self._format_time(time_val)}"
            elif place == 2:
                title = f"{name} finished 2nd"
                body = f"2nd place - {self._format_time(time_val)}"
            elif place == 3:
                title = f"{name} finished 3rd"
                body = f"3rd place - {self._format_time(time_val)}"
            else:
                title = f"{name} finished"
                body = f"Time: {self._format_time(time_val)}"

            send_result = await self.fcm.send_to_users(
                user_ids=[user_id],
                notification_type=NotificationType.FAVORITE_RESULT,
                title=title,
                body=body,
                data={
                    "event_id": event_id,
                    "heat_id": heat_id,
                    "racer_id": racer_id,
                    "screen": "results",
                },
                dedup_key=f"result_{heat_id}_{racer_id}",
            )

            sent += send_result.success_count
            skipped += send_result.failure_count

        return {"sent": sent, "skipped": skipped}

    async def on_poll_activated(
        self,
        event_id: str,
        poll_id: str,
        question: str,
    ) -> dict[str, int]:
        """
        Trigger notification when a new poll is activated.

        Sends to all users subscribed to the event topic.
        """
        # Get users at this event (have favorites in this event)
        stmt = """
            SELECT DISTINCT uf.user_id
            FROM user_favorites uf
            JOIN racers r ON uf.racer_id = r.id
            WHERE r.event_id = :event_id
        """
        result = await self.db.execute(stmt, {"event_id": event_id})
        user_ids = [row[0] for row in result.fetchall()]

        if not user_ids:
            return {"sent": 0, "skipped": 0}

        send_result = await self.fcm.send_to_users(
            user_ids=user_ids,
            notification_type=NotificationType.POLL_NEW,
            title="New Poll Available!",
            body=question[:100],  # Truncate long questions
            data={
                "event_id": event_id,
                "poll_id": poll_id,
                "screen": "poll_vote",
            },
        )

        return {
            "sent": send_result.success_count,
            "skipped": send_result.failure_count,
        }

    async def on_poll_closed(
        self,
        event_id: str,
        poll_id: str,
        question: str,
        winner_label: str,
    ) -> dict[str, int]:
        """
        Trigger notification when poll results are available.
        """
        # Notify users who voted in this poll
        stmt = """
            SELECT DISTINCT pv.user_id
            FROM poll_votes pv
            WHERE pv.poll_id = :poll_id
        """
        result = await self.db.execute(stmt, {"poll_id": poll_id})
        user_ids = [row[0] for row in result.fetchall()]

        if not user_ids:
            return {"sent": 0, "skipped": 0}

        send_result = await self.fcm.send_to_users(
            user_ids=user_ids,
            notification_type=NotificationType.POLL_RESULT,
            title="Poll Results Are In!",
            body=f"Winner: {winner_label}",
            data={
                "event_id": event_id,
                "poll_id": poll_id,
                "screen": "poll_results",
            },
        )

        return {
            "sent": send_result.success_count,
            "skipped": send_result.failure_count,
        }

    async def on_prediction_resolved(
        self,
        user_id: str,
        event_id: str,
        heat_id: str,
        was_correct: bool,
        points_earned: int,
    ) -> dict[str, int]:
        """
        Trigger notification when user's prediction is resolved.
        """
        if was_correct:
            title = "Prediction Correct! 🎯"
            body = f"You earned {points_earned} points!"
        else:
            title = "Better luck next time!"
            body = "Keep predicting to climb the leaderboard"

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

        return {
            "sent": send_result.success_count,
            "skipped": send_result.failure_count,
        }

    async def on_purchase_completed(
        self,
        user_id: str,
        purchase_type: str,
        amount: str,
        receipt_id: str,
    ) -> dict[str, int]:
        """
        Trigger purchase confirmation notification.

        Cannot be opted out of - transactional notification.
        """
        send_result = await self.fcm.send_to_users(
            user_ids=[user_id],
            notification_type=NotificationType.PURCHASE_CONFIRM,
            title="Purchase Confirmed",
            body=f"{purchase_type} - {amount}",
            data={
                "receipt_id": receipt_id,
                "screen": "receipt",
            },
        )

        return {
            "sent": send_result.success_count,
            "skipped": send_result.failure_count,
        }

    def _format_time(self, seconds: float | None) -> str:
        """Format race time as mm:ss.nnn."""
        if seconds is None:
            return "DNF"
        if seconds >= 99.999:
            return "DNF"
        minutes = int(seconds // 60)
        remaining = seconds % 60
        return f"{minutes:02d}:{remaining:06.3f}"
```

---

## 6. Message Templates

### 6.1 Template Constants

| Notification Type | Title Template | Body Template |
|-------------------|----------------|---------------|
| Favorite Staging (NOW) | `{name} is racing NOW!` | `Lane {lane}` |
| Favorite Staging (soon) | `{name} is racing soon!` | `~{heats_away} heats away - Lane {lane}` |
| Favorite Result (1st) | `{name} won! 🏆` | `1st place - {time}` |
| Favorite Result (other) | `{name} finished` | `{place} place - {time}` |
| Poll New | `New Poll Available!` | `{question}` |
| Poll Result | `Poll Results Are In!` | `Winner: {winner}` |
| Prediction Correct | `Prediction Correct! 🎯` | `You earned {points} points!` |
| Prediction Wrong | `Better luck next time!` | `Keep predicting to climb the leaderboard` |
| Purchase | `Purchase Confirmed` | `{type} - {amount}` |
| Emergency | `EMERGENCY ALERT` | `{message}` |

### 6.2 Character Limits

| Field | Android Limit | iOS Limit | Our Target |
|-------|---------------|-----------|------------|
| Title | 65 chars visible | 50 chars visible | 50 chars |
| Body | 240 chars visible | 100 chars visible | 100 chars |

---

## 7. User Preferences

### 7.1 Preference Schema

```python
class NotificationPreferences(BaseModel):
    """User notification preferences schema."""

    # Global toggle
    push_enabled: bool = True

    # Quiet hours (optional)
    quiet_hours_enabled: bool = False
    quiet_hours_start: str | None = None  # "22:00"
    quiet_hours_end: str | None = None    # "08:00"

    # Per-category toggles
    favorite_staging_enabled: bool = True
    favorite_results_enabled: bool = True
    poll_notifications_enabled: bool = True
    prediction_results_enabled: bool = True
```

### 7.2 Default Behavior

- New users: All notifications enabled by default
- Quiet hours: Disabled by default
- Emergency notifications: Cannot be disabled
- Purchase confirmations: Cannot be disabled

---

## 8. Flutter Client Integration

### 8.1 Required Flutter Packages

```yaml
dependencies:
  firebase_core: ^2.24.0
  firebase_messaging: ^14.7.0
  flutter_local_notifications: ^16.0.0
```

### 8.2 Android Notification Channels

```kotlin
// Create channels on app startup
val channels = listOf(
    NotificationChannel("race_alerts", "Race Alerts", IMPORTANCE_HIGH),
    NotificationChannel("race_results", "Race Results", IMPORTANCE_DEFAULT),
    NotificationChannel("engagement", "Engagement", IMPORTANCE_DEFAULT),
    NotificationChannel("transactions", "Transactions", IMPORTANCE_HIGH),
    NotificationChannel("emergency", "Emergency", IMPORTANCE_MAX),
)
```

### 8.3 Deep Link Routing

```dart
// Handle notification tap
void handleNotificationTap(RemoteMessage message) {
  final screen = message.data['screen'];
  final eventId = message.data['event_id'];

  switch (screen) {
    case 'heat_detail':
      Navigator.pushNamed(context, '/heat/${message.data['heat_id']}');
      break;
    case 'results':
      Navigator.pushNamed(context, '/event/$eventId/results');
      break;
    case 'poll_vote':
      Navigator.pushNamed(context, '/poll/${message.data['poll_id']}');
      break;
    // ... etc
  }
}
```

---

## 9. Emergency Broadcast System

### 9.1 Authorization Flow

```
1. Coordinator clicks "Emergency Broadcast" in web UI
2. UI confirms action with coordinator
3. POST /v1/orgs/{orgId}/events/{eventId}/emergency/broadcast
   Authorization: Bearer {coordinator_jwt}
   {
     "message": "Weather delay - seek shelter",
     "severity": "emergency"
   }
4. API validates:
   - JWT has coordinator role for this event
   - Rate limit: max 5 broadcasts per hour
5. EmergencyBroadcastService dispatches to:
   - FCM topic: event_{eventId}
   - MQTT topic: derbynet/ledsign/broadcast
6. Response includes message_id for tracking
```

### 9.2 LED Sign Alignment

Emergency broadcasts use identical message format for both FCM and LED signs:

```python
{
    "priority": 0,  # Highest
    "title": "EMERGENCY",
    "message": message,
    "display_config": {
        "mode": "flash",
        "color": "red",
    }
}
```

---

## 10. API Endpoints

### 10.1 Push Token Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/v1/me/push-token` | Bearer | Register FCM token |
| DELETE | `/v1/me/push-token/{deviceId}` | Bearer | Unregister token |
| GET | `/v1/me/notifications/preferences` | Bearer | Get preferences |
| PATCH | `/v1/me/notifications/preferences` | Bearer | Update preferences |

### 10.2 Emergency Broadcast

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/v1/orgs/{orgId}/events/{eventId}/emergency/broadcast` | Coordinator | Send emergency |
| DELETE | `/v1/orgs/{orgId}/events/{eventId}/emergency/broadcast` | Coordinator | Clear emergency |

---

## 11. Implementation Roadmap

### Phase 1: Foundation ✅ COMPLETE

| Task | Description | Files | Status |
|------|-------------|-------|--------|
| 1.1 | Create SQLAlchemy models | `models/notification.py` | ✅ Done |
| 1.2 | Create SQL migration | `migrations/002_fcm_notifications.sql` | ✅ Done |
| 1.3 | Update UserFavorite model | `models/engagement.py` | ✅ Done |
| 1.4 | Add config settings | `app/config.py` | ✅ Done |
| 1.5 | Implement FCMService class | `services/notifications/fcm_service.py` | ✅ Done |
| 1.6 | Write unit tests | `tests/test_fcm_service.py` | 🔲 Pending |

**Files Created (Phase 1):**
```
extras/saasbox/api/
├── models/notification.py          # PushToken, NotificationPreference, NotificationLog
├── migrations/002_fcm_notifications.sql  # Full schema with indexes, constraints
├── services/
│   ├── __init__.py
│   └── notifications/
│       ├── __init__.py
│       └── fcm_service.py          # Full FCMService implementation
└── app/config.py                   # Added: fcm_enabled, fcm_staging_lookahead_heats,
                                    #        fcm_dedup_window_seconds, fcm_batch_size
```

**Models Updated:**
- `models/engagement.py` - Added `last_staging_notified_at`, `last_result_notified_at` to UserFavorite
- `models/user.py` - Added `push_tokens`, `notification_preferences` relationships

### Phase 2: Triggers & Templates ✅ COMPLETE

| Task | Description | Files | Status |
|------|-------------|-------|--------|
| 2.1 | Implement NotificationTriggers | `services/notifications/triggers.py` | ✅ Done |
| 2.2 | Create message templates | `services/notifications/triggers.py` (embedded) | ✅ Done |
| 2.3 | Integrate with sync handler | `modules/events/routes.py` | ✅ Done |
| 2.4 | Write integration tests | `tests/test_notifications.py` | ✅ Done |

**Files Created (Phase 2):**
```
extras/saasbox/api/
├── services/notifications/
│   ├── __init__.py                 # Updated: exports NotificationTriggers
│   └── triggers.py                 # NotificationTriggers class + message templates
└── modules/events/
    └── routes.py                   # Updated: _trigger_sync_notifications()
```

**Trigger Methods Implemented:**
| Method | Trigger Event | Notification Type |
|--------|---------------|-------------------|
| `on_heat_schedule_updated()` | Race sync with current heat | FAVORITE_STAGING |
| `on_heat_completed()` | Race results synced | FAVORITE_RESULT |
| `on_poll_activated()` | Poll status changes to active | POLL_NEW |
| `on_poll_closed()` | Poll status changes to closed | POLL_RESULT |
| `on_prediction_resolved()` | Heat finishes with predictions | PREDICTION_RESULT |
| `on_purchase_completed()` | Payment confirmed | PURCHASE_CONFIRM |

**Message Templates:**
- PII-safe racer names (first name + last initial only)
- Character limits: 50 chars title, 100 chars body
- Dynamic content based on race position, heats remaining

### Phase 3: API & Preferences ✅ COMPLETE

| Task | Description | Files | Status |
|------|-------------|-------|--------|
| 3.1 | Push token registration endpoint | `modules/notifications/routes.py` | ✅ Done |
| 3.2 | Preferences endpoints | `modules/notifications/routes.py` | ✅ Done |
| 3.3 | Emergency broadcast endpoint | `modules/notifications/routes.py` | ✅ Done |
| 3.4 | Alert Manager integration | `middleware/logging.py` | ✅ Done |

**Files Created (Phase 3):**
```
extras/saasbox/api/
├── modules/notifications/
│   ├── __init__.py
│   ├── schemas.py                  # Request/response Pydantic models
│   └── routes.py                   # All notification endpoints
└── app/main.py                     # Updated: registered notification routes
```

**Endpoints Implemented:**
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/me/notifications/push-token` | Register FCM token |
| GET | `/v1/me/notifications/push-tokens` | List user's tokens |
| DELETE | `/v1/me/notifications/push-token/{deviceId}` | Remove token |
| GET | `/v1/me/notifications/preferences` | Get preferences |
| PATCH | `/v1/me/notifications/preferences` | Update preferences |
| GET | `/v1/me/notifications/history` | Get notification history |
| POST | `/v1/orgs/{orgId}/events/{eventId}/emergency/broadcast` | Send emergency |
| DELETE | `/v1/orgs/{orgId}/events/{eventId}/emergency/broadcast` | Clear emergency |

### Phase 4: Flutter Integration (Week 4)

| Task | Description | Notes |
|------|-------------|-------|
| 4.1 | Configure firebase_messaging | Android setup |
| 4.2 | Create notification channels | 5 channels |
| 4.3 | Implement deep link routing | All screens |
| 4.4 | Handle foreground/background | All app states |

### Phase 5: Testing & Launch (Week 5)

| Task | Description | Notes |
|------|-------------|-------|
| 5.1 | End-to-end testing | Real devices |
| 5.2 | Load testing | Multicast batching |
| 5.3 | Documentation | API docs |
| 5.4 | Soft launch | Single event |

---

## 12. Testing Strategy

### 12.1 Unit Tests

```python
# test_fcm_service.py
async def test_send_to_users_filters_by_preferences():
    """Users who opted out should not receive notifications."""

async def test_send_to_users_applies_deduplication():
    """Same notification within window should be deduplicated."""

async def test_multicast_batches_over_500():
    """Messages to >500 users should batch correctly."""

async def test_invalid_tokens_cleaned_up():
    """NOT_FOUND tokens should be marked invalid."""
```

### 12.2 Integration Tests

```python
# test_triggers.py
async def test_staging_notification_within_5_heats():
    """Users notified when favorite within 5 heats."""

async def test_staging_notification_not_sent_outside_window():
    """No notification if favorite >5 heats away."""

async def test_emergency_broadcast_reaches_all_users():
    """Emergency bypasses preferences and reaches everyone."""
```

### 12.3 Manual Test Checklist

- [ ] Android notification appears when app in foreground
- [ ] Android notification appears when app in background
- [ ] Android notification appears when app terminated
- [ ] Tapping notification opens correct screen
- [ ] Emergency notification shows as high priority
- [ ] Quiet hours respected
- [ ] Opt-out preferences respected

---

## 13. References

### FCM Documentation

- [FCM Architecture Overview](https://firebase.google.com/docs/cloud-messaging/fcm-architecture)
- [FCM HTTP v1 API](https://firebase.google.com/docs/cloud-messaging/send/v1-api)
- [Firebase Admin SDK (Python)](https://firebase.google.com/docs/cloud-messaging/send/admin-sdk)
- [Migration from Legacy APIs](https://firebase.google.com/docs/cloud-messaging/migrate-v1)

### Best Practices

- [Ensure FCM Notifications Reach Users on Android](https://firebase.blog/posts/2025/04/fcm-on-android/)
- [Mastering Push Notifications in Flutter (2025)](https://medium.com/@AlexCodeX/mastering-push-notifications-in-flutter-a-complete-2025-guide-to-firebase-cloud-messaging-fcm-589e1e16e144)
- [Flutter FCM Navigation](https://medium.com/@akhil-ge0rge/flutter-push-notifications-navigate-to-target-screens-using-fcm-firebase-cloud-messaging-9179171d1ea7)

### Related SBDerbyNet Documents

- [ENTERPRISE_ROADMAP.md](/ENTERPRISE_ROADMAP.md) - Master roadmap
- [LED_SIGN_INTEGRATION_PLAN.md](/extras/ledsign/LED_SIGN_INTEGRATION_PLAN.md) - Emergency broadcast alignment

---

## 14. SaaS API Context

### Tech Stack (for reference)

| Component | Technology | Notes |
|-----------|------------|-------|
| Backend | Python 3.11+ / FastAPI | Async, type hints |
| Database | PostgreSQL 15+ | Row-Level Security for multi-tenant |
| Cache | Redis 7+ | Deduplication, rate limiting |
| ORM | SQLAlchemy 2.0 | Async with `Mapped` type annotations |
| Auth | Firebase Authentication | Google OAuth |
| Push | Firebase Cloud Messaging | `firebase-admin` SDK |
| Logging | Alert Manager | Errors only (not every notification) |

### Key Patterns

**ID Generation:** All models use prefixed IDs via `generate_prefixed_id()`:
- `usr_abc123` (users), `prd_xyz789` (predictions), etc.

**Timestamps:** Models use `TimestampMixin` for `created_at`/`updated_at`.

**Multi-Tenant:** PostgreSQL RLS with `app.current_org_id` session variable.

**Config:** Settings via `pydantic-settings` from environment or `.env` file.

### Existing Models Referenced

```python
# User model (models/user.py) - relationships added
class User:
    push_tokens: Mapped[list["PushToken"]]
    notification_preferences: Mapped["NotificationPreference | None"]

# UserFavorite (models/engagement.py) - columns added
class UserFavorite:
    notify_upcoming: bool  # Existing
    notify_results: bool   # Existing
    last_staging_notified_at: datetime | None  # NEW
    last_result_notified_at: datetime | None   # NEW
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-16 | Claude Code | Initial FCM notification plan |
| 1.1.0 | 2026-01-16 | Claude Code | Phase 1 DB models complete. Added implementation status, file paths, SaaS context section. Removed federated-drifting dependency. |
| 1.2.0 | 2026-01-16 | Claude Code | **Phase 1 & 3 Complete**: Implemented FCMService class with full functionality (token management, multicast batching, deduplication, preference filtering). Created notification module with all API endpoints (push token CRUD, preferences GET/PATCH, notification history, emergency broadcast). Registered routes in main.py. |
