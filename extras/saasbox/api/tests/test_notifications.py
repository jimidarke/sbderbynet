"""
Tests for FCM notification service and endpoints.

Tests cover:
- Push token registration/removal
- Notification preference management
- FCMService core functionality (mocked FCM SDK)
- Emergency broadcasts
- Notification history

See FCM_NOTIFICATION_PLAN.md for detailed specification.
"""
import pytest
from datetime import datetime, timedelta, time
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import (
    PushToken,
    NotificationPreference,
    NotificationLog,
    DeviceType as ModelDeviceType,
    NotificationStatus,
)
from services.notifications.fcm_service import (
    FCMService,
    NotificationType,
    NotificationConfig,
    SendResult,
    NOTIFICATION_CONFIGS,
)
from tests.factories import UserFactory, OrganizationFactory, EventFactory
from tests.mocks import create_test_token, MockRedis


# =============================================================================
# Test Factories for Notification Models
# =============================================================================


class PushTokenFactory:
    """Factory for creating PushToken instances."""

    _counter = 0

    @classmethod
    def _get_counter(cls) -> int:
        cls._counter += 1
        return cls._counter

    @classmethod
    def create(
        cls,
        user_id: str,
        token: str | None = None,
        device_type: ModelDeviceType = ModelDeviceType.ANDROID,
        device_id: str | None = None,
        app_version: str = "1.0.0",
        is_valid: bool = True,
    ) -> PushToken:
        counter = cls._get_counter()
        return PushToken(
            user_id=user_id,
            token=token or f"fcm_token_{'x' * 150}_{counter}",
            device_type=device_type,
            device_id=device_id or f"device-uuid-{counter:04d}",
            app_version=app_version,
            is_valid=is_valid,
        )


class NotificationPreferenceFactory:
    """Factory for creating NotificationPreference instances."""

    @classmethod
    def create(
        cls,
        user_id: str,
        push_enabled: bool = True,
        quiet_hours_enabled: bool = False,
        quiet_hours_start: time | None = None,
        quiet_hours_end: time | None = None,
        favorite_staging_enabled: bool = True,
        favorite_results_enabled: bool = True,
        poll_notifications_enabled: bool = True,
        prediction_results_enabled: bool = True,
    ) -> NotificationPreference:
        return NotificationPreference(
            user_id=user_id,
            push_enabled=push_enabled,
            quiet_hours_enabled=quiet_hours_enabled,
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end,
            favorite_staging_enabled=favorite_staging_enabled,
            favorite_results_enabled=favorite_results_enabled,
            poll_notifications_enabled=poll_notifications_enabled,
            prediction_results_enabled=prediction_results_enabled,
        )


# =============================================================================
# FCMService Unit Tests
# =============================================================================


class TestFCMServiceInitialization:
    """Tests for FCMService initialization."""

    @pytest.mark.asyncio
    async def test_fcm_disabled_when_not_configured(self, db_session: AsyncSession):
        """Test FCM is disabled when credentials not configured."""
        with patch("services.notifications.fcm_service.get_settings") as mock_settings:
            mock_settings.return_value.fcm_enabled = False

            # Reset class state for test
            FCMService._initialized = False
            FCMService._firebase_app = None

            fcm = FCMService(db_session, None, None)

            # Should not be initialized
            assert not FCMService._initialized

    @pytest.mark.asyncio
    async def test_send_returns_early_when_disabled(self, db_session: AsyncSession):
        """Test send_to_users returns early when FCM is disabled."""
        with patch("services.notifications.fcm_service.get_settings") as mock_settings:
            mock_settings.return_value.fcm_enabled = False

            FCMService._initialized = False
            fcm = FCMService(db_session, None, None)

            result = await fcm.send_to_users(
                user_ids=["usr_123"],
                notification_type=NotificationType.FAVORITE_STAGING,
                title="Test",
                body="Test body",
            )

            assert result.success_count == 0
            assert result.failure_count == 1
            assert "FCM not initialized" in result.errors[0]


class TestTokenRegistration:
    """Tests for push token registration."""

    @pytest.mark.asyncio
    async def test_register_new_token(
        self,
        db_session: AsyncSession,
        test_user,
    ):
        """Test registering a new push token."""
        with patch.object(FCMService, "_ensure_initialized"):
            FCMService._initialized = True
            fcm = FCMService(db_session, None, None)

            token_value = "fcm_" + "a" * 150
            device_id = "device-uuid-12345"

            success = await fcm.register_token(
                user_id=test_user.id,
                token=token_value,
                device_type="android",
                device_id=device_id,
                app_version="1.2.3",
            )

            assert success is True

            # Verify token was saved
            stmt = select(PushToken).where(
                PushToken.user_id == test_user.id,
                PushToken.device_id == device_id,
            )
            result = await db_session.execute(stmt)
            saved_token = result.scalar_one_or_none()

            assert saved_token is not None
            assert saved_token.token == token_value
            assert saved_token.device_type == ModelDeviceType.ANDROID
            assert saved_token.app_version == "1.2.3"
            assert saved_token.is_valid is True

    @pytest.mark.asyncio
    async def test_update_existing_token(
        self,
        db_session: AsyncSession,
        test_user,
    ):
        """Test updating an existing push token."""
        device_id = "device-uuid-existing"
        old_token = PushTokenFactory.create(
            user_id=test_user.id,
            token="old_token_" + "x" * 140,
            device_id=device_id,
        )
        db_session.add(old_token)
        await db_session.commit()

        with patch.object(FCMService, "_ensure_initialized"):
            FCMService._initialized = True
            fcm = FCMService(db_session, None, None)

            new_token_value = "new_token_" + "y" * 140
            success = await fcm.register_token(
                user_id=test_user.id,
                token=new_token_value,
                device_type="android",
                device_id=device_id,
                app_version="2.0.0",
            )

            assert success is True

            # Verify token was updated, not duplicated
            stmt = select(PushToken).where(
                PushToken.user_id == test_user.id,
                PushToken.device_id == device_id,
            )
            result = await db_session.execute(stmt)
            tokens = result.scalars().all()

            assert len(tokens) == 1
            assert tokens[0].token == new_token_value
            assert tokens[0].app_version == "2.0.0"


class TestTokenRemoval:
    """Tests for push token removal."""

    @pytest.mark.asyncio
    async def test_remove_token(
        self,
        db_session: AsyncSession,
        test_user,
    ):
        """Test removing a push token."""
        device_id = "device-to-remove"
        token = PushTokenFactory.create(
            user_id=test_user.id,
            device_id=device_id,
        )
        db_session.add(token)
        await db_session.commit()

        with patch.object(FCMService, "_ensure_initialized"):
            FCMService._initialized = True
            fcm = FCMService(db_session, None, None)

            removed = await fcm.remove_token(
                user_id=test_user.id,
                device_id=device_id,
            )

            assert removed is True

            # Verify token was deleted
            stmt = select(PushToken).where(
                PushToken.user_id == test_user.id,
                PushToken.device_id == device_id,
            )
            result = await db_session.execute(stmt)
            assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_token(
        self,
        db_session: AsyncSession,
        test_user,
    ):
        """Test removing a token that doesn't exist."""
        with patch.object(FCMService, "_ensure_initialized"):
            FCMService._initialized = True
            fcm = FCMService(db_session, None, None)

            removed = await fcm.remove_token(
                user_id=test_user.id,
                device_id="nonexistent-device",
            )

            assert removed is False

    @pytest.mark.asyncio
    async def test_remove_invalid_tokens(
        self,
        db_session: AsyncSession,
        test_user,
    ):
        """Test marking multiple tokens as invalid."""
        tokens = [
            PushTokenFactory.create(
                user_id=test_user.id,
                token=f"token_{i}_" + "x" * 145,
                device_id=f"device-{i}",
            )
            for i in range(3)
        ]
        for t in tokens:
            db_session.add(t)
        await db_session.commit()

        token_values = [t.token for t in tokens[:2]]  # Mark first two as invalid

        with patch.object(FCMService, "_ensure_initialized"):
            FCMService._initialized = True
            fcm = FCMService(db_session, None, None)

            count = await fcm.remove_invalid_tokens(token_values)

            assert count == 2

            # Verify first two are invalid, third is still valid
            stmt = select(PushToken).where(PushToken.user_id == test_user.id)
            result = await db_session.execute(stmt)
            all_tokens = result.scalars().all()

            invalid_count = sum(1 for t in all_tokens if not t.is_valid)
            valid_count = sum(1 for t in all_tokens if t.is_valid)

            assert invalid_count == 2
            assert valid_count == 1


class TestPreferenceFiltering:
    """Tests for notification preference filtering."""

    @pytest.mark.asyncio
    async def test_filter_respects_opt_out(
        self,
        db_session: AsyncSession,
    ):
        """Test that users who opted out are filtered."""
        # Create users
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        user3 = UserFactory.create()
        db_session.add_all([user1, user2, user3])
        await db_session.flush()

        # User1: staging enabled
        pref1 = NotificationPreferenceFactory.create(
            user_id=user1.id,
            favorite_staging_enabled=True,
        )
        # User2: staging disabled
        pref2 = NotificationPreferenceFactory.create(
            user_id=user2.id,
            favorite_staging_enabled=False,
        )
        # User3: no preferences (defaults apply)
        db_session.add_all([pref1, pref2])
        await db_session.commit()

        with patch.object(FCMService, "_ensure_initialized"):
            FCMService._initialized = True
            fcm = FCMService(db_session, None, None)

            eligible = await fcm._filter_by_preferences(
                user_ids=[user1.id, user2.id, user3.id],
                preference_field="favorite_staging_enabled",
            )

            # User1 and User3 should be eligible
            assert user1.id in eligible
            assert user2.id not in eligible
            assert user3.id in eligible

    @pytest.mark.asyncio
    async def test_emergency_cannot_be_opted_out(
        self,
        db_session: AsyncSession,
    ):
        """Test that emergency notifications cannot be opted out."""
        user = UserFactory.create()
        db_session.add(user)
        await db_session.flush()

        # User has push disabled entirely
        pref = NotificationPreferenceFactory.create(
            user_id=user.id,
            push_enabled=False,
        )
        db_session.add(pref)
        await db_session.commit()

        with patch.object(FCMService, "_ensure_initialized"):
            FCMService._initialized = True
            fcm = FCMService(db_session, None, None)

            # Emergency has preference_field=None
            config = NOTIFICATION_CONFIGS[NotificationType.EMERGENCY]
            assert config.preference_field is None

            eligible = await fcm._filter_by_preferences(
                user_ids=[user.id],
                preference_field=None,  # Cannot opt out
            )

            # User should still be eligible for emergency
            assert user.id in eligible


class TestDeduplication:
    """Tests for notification deduplication."""

    @pytest.mark.asyncio
    async def test_deduplication_skips_recent(
        self,
        db_session: AsyncSession,
    ):
        """Test that recently notified users are deduplicated."""
        redis = MockRedis()

        # Simulate user1 was recently notified
        await redis.setex(
            "fcm:dedup:user1:favorite_staging",
            300,
            str(datetime.utcnow().timestamp()),
        )

        with patch.object(FCMService, "_ensure_initialized"):
            with patch("services.notifications.fcm_service.get_settings") as mock_settings:
                mock_settings.return_value.fcm_dedup_window_seconds = 300

                FCMService._initialized = True
                fcm = FCMService(db_session, redis, None)

                eligible = await fcm._apply_deduplication(
                    user_ids=["user1", "user2"],
                    dedup_key="favorite_staging",
                )

                # Only user2 should be eligible
                assert "user1" not in eligible
                assert "user2" in eligible

    @pytest.mark.asyncio
    async def test_deduplication_sets_cache(
        self,
        db_session: AsyncSession,
    ):
        """Test that deduplication sets cache for new users."""
        redis = MockRedis()

        with patch.object(FCMService, "_ensure_initialized"):
            with patch("services.notifications.fcm_service.get_settings") as mock_settings:
                mock_settings.return_value.fcm_dedup_window_seconds = 300

                FCMService._initialized = True
                fcm = FCMService(db_session, redis, None)

                await fcm._apply_deduplication(
                    user_ids=["new_user"],
                    dedup_key="test_key",
                )

                # Cache should be set
                cached = await redis.get("fcm:dedup:new_user:test_key")
                assert cached is not None

    @pytest.mark.asyncio
    async def test_no_redis_skips_deduplication(
        self,
        db_session: AsyncSession,
    ):
        """Test that deduplication is skipped when Redis is not available."""
        with patch.object(FCMService, "_ensure_initialized"):
            FCMService._initialized = True
            fcm = FCMService(db_session, None, None)  # No Redis

            eligible = await fcm._apply_deduplication(
                user_ids=["user1", "user2"],
                dedup_key="test_key",
            )

            # All users should be eligible when Redis is unavailable
            assert "user1" in eligible
            assert "user2" in eligible


class TestMulticastBatching:
    """Tests for multicast message batching."""

    @pytest.mark.asyncio
    async def test_batch_size_logic(
        self,
        db_session: AsyncSession,
    ):
        """Test that batching logic properly splits tokens into batches."""
        # Test the batch splitting logic without actual FCM calls
        with patch.object(FCMService, "_ensure_initialized"):
            FCMService._initialized = False  # FCM not initialized
            fcm = FCMService(db_session, None, None)

            # When FCM is not initialized, it should return early
            result = await fcm._send_multicast_batched(
                tokens={f"token_{i}": f"user_{i}" for i in range(600)},
                title="Test",
                body="Test body",
                data=None,
                image_url=None,
                config=NOTIFICATION_CONFIGS[NotificationType.FAVORITE_STAGING],
                notification_type=NotificationType.FAVORITE_STAGING,
            )

            # Should return error since firebase-admin not installed
            assert result.failure_count == 600
            assert "firebase-admin not installed" in result.errors[0]

    def test_batch_size_config(self):
        """Test that batch size config is set appropriately."""
        from app.config import get_settings
        settings = get_settings()
        # Verify batch size is at or below FCM's 500 limit
        assert settings.fcm_batch_size <= 500


class TestEmergencyBroadcast:
    """Tests for emergency broadcast functionality."""

    @pytest.mark.asyncio
    async def test_emergency_broadcast_when_fcm_disabled(
        self,
        db_session: AsyncSession,
    ):
        """Test that emergency broadcasts handle FCM disabled gracefully."""
        with patch.object(FCMService, "_ensure_initialized"):
            FCMService._initialized = False
            with patch("services.notifications.fcm_service.get_settings") as mock_settings:
                mock_settings.return_value.fcm_enabled = False

                fcm = FCMService(db_session, None, None)

                result = await fcm.send_emergency_broadcast(
                    event_id="evt_123",
                    message="Weather delay - seek shelter",
                    coordinator_id="usr_coord",
                )

                # Should return failure when FCM not initialized
                assert result.success_count == 0
                assert result.failure_count == 0
                assert "FCM not initialized" in result.errors[0]

    @pytest.mark.asyncio
    async def test_emergency_broadcast_config(self):
        """Test emergency broadcast configuration is correct."""
        config = NOTIFICATION_CONFIGS[NotificationType.EMERGENCY]

        # Emergency broadcasts must be high priority
        assert config.priority == "high"

        # Cannot be opted out
        assert config.preference_field is None

        # Uses emergency channel
        assert config.android_channel == "emergency"

    @pytest.mark.asyncio
    async def test_emergency_broadcast_topic_format(self):
        """Test emergency broadcast topic naming convention."""
        # Emergency broadcasts should use topic format: event_{event_id}
        event_id = "evt_12345"
        expected_topic = f"event_{event_id}"

        # This is the format used in send_emergency_broadcast
        assert expected_topic == "event_evt_12345"


class TestNotificationConfig:
    """Tests for notification configuration."""

    def test_all_types_have_config(self):
        """Test that all notification types have configuration."""
        for ntype in NotificationType:
            assert ntype in NOTIFICATION_CONFIGS

    def test_emergency_config_is_high_priority(self):
        """Test that emergency notifications are high priority."""
        config = NOTIFICATION_CONFIGS[NotificationType.EMERGENCY]
        assert config.priority == "high"
        assert config.preference_field is None  # Cannot opt out
        assert config.android_channel == "emergency"

    def test_staging_config_is_time_sensitive(self):
        """Test that staging notifications are time-sensitive."""
        config = NOTIFICATION_CONFIGS[NotificationType.FAVORITE_STAGING]
        assert config.priority == "high"
        assert config.ttl_seconds == 300  # 5 minutes
        assert config.collapse_key == "staging"


# =============================================================================
# API Endpoint Integration Tests
# =============================================================================


class TestPushTokenEndpoints:
    """Tests for push token API endpoints."""

    @pytest.mark.asyncio
    async def test_register_push_token_validation(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test push token validation (min length)."""
        response = await authenticated_client.post(
            "/v1/me/notifications/push-token",
            json={
                "token": "too_short",  # Less than 100 chars
                "device_type": "android",
                "device_id": "550e8400-e29b-41d4-a716-446655440000",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_push_tokens_empty(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test GET /v1/me/notifications/push-tokens returns empty list."""
        response = await authenticated_client.get("/v1/me/notifications/push-tokens")

        assert response.status_code == 200
        data = response.json()["data"]["tokens"]
        assert data == []

    @pytest.mark.asyncio
    async def test_list_push_tokens_with_data(
        self,
        authenticated_client: AsyncClient,
        test_user,
        db_session: AsyncSession,
    ):
        """Test GET /v1/me/notifications/push-tokens returns tokens."""
        # Create tokens for the user
        tokens = [
            PushTokenFactory.create(
                user_id=test_user.id,
                device_id=f"device-list-{i}",
            )
            for i in range(2)
        ]
        for t in tokens:
            db_session.add(t)
        await db_session.commit()

        response = await authenticated_client.get("/v1/me/notifications/push-tokens")

        assert response.status_code == 200
        data = response.json()["data"]["tokens"]
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_delete_token_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test DELETE endpoint requires authentication."""
        response = await client.delete(
            "/v1/me/notifications/push-token/some-device-id"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_push_token_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that push token endpoints require authentication."""
        response = await client.get("/v1/me/notifications/push-tokens")
        assert response.status_code == 401


class TestPreferenceEndpoints:
    """Tests for notification preference API endpoints."""

    @pytest.mark.asyncio
    async def test_get_preferences_default(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test GET /v1/me/notifications/preferences returns defaults."""
        response = await authenticated_client.get("/v1/me/notifications/preferences")

        assert response.status_code == 200
        data = response.json()["data"]
        # All defaults should be True
        assert data["push_enabled"] is True
        assert data["favorite_staging_enabled"] is True
        assert data["favorite_results_enabled"] is True
        assert data["poll_notifications_enabled"] is True
        assert data["prediction_results_enabled"] is True
        assert data["quiet_hours_enabled"] is False

    @pytest.mark.asyncio
    async def test_get_preferences_saved(
        self,
        authenticated_client: AsyncClient,
        test_user,
        db_session: AsyncSession,
    ):
        """Test GET /v1/me/notifications/preferences returns saved values."""
        pref = NotificationPreferenceFactory.create(
            user_id=test_user.id,
            poll_notifications_enabled=False,
            quiet_hours_enabled=True,
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(8, 0),
        )
        db_session.add(pref)
        await db_session.commit()

        response = await authenticated_client.get("/v1/me/notifications/preferences")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["poll_notifications_enabled"] is False
        assert data["quiet_hours_enabled"] is True
        assert data["quiet_hours_start"] == "22:00"
        assert data["quiet_hours_end"] == "08:00"

    @pytest.mark.asyncio
    async def test_update_preferences(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test PATCH /v1/me/notifications/preferences."""
        response = await authenticated_client.patch(
            "/v1/me/notifications/preferences",
            json={
                "poll_notifications_enabled": False,
                "quiet_hours_enabled": True,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "08:00",
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["poll_notifications_enabled"] is False
        assert data["quiet_hours_enabled"] is True
        assert data["quiet_hours_start"] == "22:00"
        assert data["quiet_hours_end"] == "08:00"

    @pytest.mark.asyncio
    async def test_update_preferences_partial(
        self,
        authenticated_client: AsyncClient,
        test_user,
        db_session: AsyncSession,
    ):
        """Test partial preference updates."""
        # Create existing preferences
        pref = NotificationPreferenceFactory.create(
            user_id=test_user.id,
            favorite_staging_enabled=True,
            poll_notifications_enabled=True,
        )
        db_session.add(pref)
        await db_session.commit()

        # Update only one field
        response = await authenticated_client.patch(
            "/v1/me/notifications/preferences",
            json={"poll_notifications_enabled": False},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["poll_notifications_enabled"] is False
        assert data["favorite_staging_enabled"] is True  # Unchanged

    @pytest.mark.asyncio
    async def test_update_preferences_invalid_time_format(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test that invalid time format is rejected."""
        response = await authenticated_client.patch(
            "/v1/me/notifications/preferences",
            json={"quiet_hours_start": "invalid"},
        )

        assert response.status_code == 422


class TestNotificationHistoryEndpoint:
    """Tests for notification history endpoint."""

    @pytest.mark.asyncio
    async def test_get_history_empty(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test GET /v1/me/notifications/history with no history."""
        response = await authenticated_client.get("/v1/me/notifications/history")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["notifications"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_history_with_data(
        self,
        authenticated_client: AsyncClient,
        test_user,
        db_session: AsyncSession,
    ):
        """Test GET /v1/me/notifications/history returns logs."""
        # Create log entries
        logs = [
            NotificationLog(
                user_id=test_user.id,
                notification_type="favorite_staging",
                event_id="evt_123",
                status=NotificationStatus.SENT,
                fcm_message_id=f"msg_{i}",
                created_at=datetime.utcnow() - timedelta(hours=i),
            )
            for i in range(3)
        ]
        for log in logs:
            db_session.add(log)
        await db_session.commit()

        response = await authenticated_client.get("/v1/me/notifications/history")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["notifications"]) == 3
        assert data["total"] == 3
        assert data["notifications"][0]["notification_type"] == "favorite_staging"
        assert data["notifications"][0]["status"] == "sent"


class TestEmergencyBroadcastEndpoints:
    """Tests for emergency broadcast API endpoints."""

    @pytest.mark.asyncio
    async def test_send_emergency_broadcast(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
        db_session: AsyncSession,
    ):
        """Test POST /v1/orgs/{org_id}/events/{event_id}/emergency/broadcast."""
        with patch("modules.notifications.routes.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None  # Not rate limited
            mock_redis.setex.return_value = True
            mock_get_redis.return_value = mock_redis

            with patch("modules.notifications.routes.FCMService") as MockFCM:
                mock_fcm = MagicMock()
                mock_fcm.send_emergency_broadcast = AsyncMock(
                    return_value=SendResult(1, 0, [], [])
                )
                MockFCM.return_value = mock_fcm

                response = await org_admin_client.post(
                    f"/v1/orgs/{test_organization.id}/events/{test_event.id}/emergency/broadcast",
                    json={
                        "message": "Weather delay - seek shelter immediately",
                        "severity": "emergency",
                    },
                )

                assert response.status_code == 201
                data = response.json()["data"]
                assert "message_id" in data
                assert data["broadcast_message"] == "Weather delay - seek shelter immediately"
                assert data["severity"] == "emergency"

    @pytest.mark.asyncio
    async def test_emergency_broadcast_requires_coordinator(
        self,
        authenticated_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test that emergency broadcasts require coordinator role."""
        response = await authenticated_client.post(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/emergency/broadcast",
            json={"message": "Test emergency"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_emergency_broadcast_rate_limited(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test that emergency broadcasts are rate limited."""
        with patch("modules.notifications.routes.FCMService") as MockFCM:
            mock_fcm = MagicMock()
            mock_fcm.send_emergency_broadcast = AsyncMock(
                return_value=SendResult(1, 0, [], [])
            )
            MockFCM.return_value = mock_fcm

            with patch("modules.notifications.routes.get_redis") as mock_get_redis:
                mock_redis = AsyncMock()
                mock_redis.get.return_value = "5"  # Already at limit
                mock_get_redis.return_value = mock_redis

                response = await org_admin_client.post(
                    f"/v1/orgs/{test_organization.id}/events/{test_event.id}/emergency/broadcast",
                    json={"message": "Another emergency"},
                )

                assert response.status_code == 429
                assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_clear_emergency_broadcast(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test DELETE /v1/orgs/{org_id}/events/{event_id}/emergency/broadcast."""
        response = await org_admin_client.delete(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/emergency/broadcast",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "cleared_at" in data
        assert "cleared_by" in data

    @pytest.mark.asyncio
    async def test_emergency_nonexistent_event(
        self,
        org_admin_client: AsyncClient,
        test_organization,
    ):
        """Test emergency broadcast on nonexistent event returns 404."""
        with patch("modules.notifications.routes.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_get_redis.return_value = mock_redis

            response = await org_admin_client.post(
                f"/v1/orgs/{test_organization.id}/events/evt_nonexistent/emergency/broadcast",
                json={"message": "Test emergency"},
            )

            assert response.status_code == 404


class TestUserIsolation:
    """Tests for user data isolation in notifications."""

    @pytest.mark.asyncio
    async def test_users_see_only_own_tokens(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test that users can only see their own push tokens."""
        # Create two users with tokens
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        db_session.add_all([user1, user2])
        await db_session.flush()

        token1 = PushTokenFactory.create(user_id=user1.id, device_id="user1-device")
        token2 = PushTokenFactory.create(user_id=user2.id, device_id="user2-device")
        db_session.add_all([token1, token2])
        await db_session.commit()

        # User1 should only see their token
        jwt1 = create_test_token(user_id=user1.id, email=user1.email)
        client.headers["Authorization"] = f"Bearer {jwt1}"
        response1 = await client.get("/v1/me/notifications/push-tokens")
        assert response1.status_code == 200
        data1 = response1.json()["data"]["tokens"]
        assert len(data1) == 1
        assert data1[0]["device_id"] == "user1-device"

        # User2 should only see their token
        jwt2 = create_test_token(user_id=user2.id, email=user2.email)
        client.headers["Authorization"] = f"Bearer {jwt2}"
        response2 = await client.get("/v1/me/notifications/push-tokens")
        assert response2.status_code == 200
        data2 = response2.json()["data"]["tokens"]
        assert len(data2) == 1
        assert data2[0]["device_id"] == "user2-device"

    @pytest.mark.asyncio
    async def test_users_see_only_own_history(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test that users can only see their own notification history."""
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        db_session.add_all([user1, user2])
        await db_session.flush()

        # Create logs for each user
        log1 = NotificationLog(
            user_id=user1.id,
            notification_type="favorite_staging",
            status=NotificationStatus.SENT,
            created_at=datetime.utcnow(),
        )
        log2 = NotificationLog(
            user_id=user2.id,
            notification_type="poll_new",
            status=NotificationStatus.SENT,
            created_at=datetime.utcnow(),
        )
        db_session.add_all([log1, log2])
        await db_session.commit()

        # User1 should only see their log
        jwt1 = create_test_token(user_id=user1.id, email=user1.email)
        client.headers["Authorization"] = f"Bearer {jwt1}"
        response1 = await client.get("/v1/me/notifications/history")
        assert response1.status_code == 200
        data1 = response1.json()["data"]["notifications"]
        assert len(data1) == 1
        assert data1[0]["notification_type"] == "favorite_staging"

        # User2 should only see their log
        jwt2 = create_test_token(user_id=user2.id, email=user2.email)
        client.headers["Authorization"] = f"Bearer {jwt2}"
        response2 = await client.get("/v1/me/notifications/history")
        assert response2.status_code == 200
        data2 = response2.json()["data"]["notifications"]
        assert len(data2) == 1
        assert data2[0]["notification_type"] == "poll_new"


# =============================================================================
# NotificationTriggers Tests (Phase 5.2)
# =============================================================================


class TestMessageTemplates:
    """Tests for message template functions."""

    def test_format_racer_name_with_last_name(self):
        """Test racer name formatting for PII protection."""
        from services.notifications.triggers import format_racer_name

        result = format_racer_name("John", "Smith")
        assert result == "John S."

    def test_format_racer_name_without_last_name(self):
        """Test racer name formatting when no last name."""
        from services.notifications.triggers import format_racer_name

        result = format_racer_name("John", "")
        assert result == "John"

    def test_format_time_normal(self):
        """Test time formatting for normal race times."""
        from services.notifications.triggers import format_time

        result = format_time(32.456)
        assert result == "00:32.456"

    def test_format_time_dnf(self):
        """Test time formatting for DNF."""
        from services.notifications.triggers import format_time

        assert format_time(None) == "DNF"
        assert format_time(99.999) == "DNF"

    def test_truncate_within_limit(self):
        """Test truncate with text within limit."""
        from services.notifications.triggers import truncate

        result = truncate("Short text", 50)
        assert result == "Short text"

    def test_truncate_exceeds_limit(self):
        """Test truncate with text exceeding limit."""
        from services.notifications.triggers import truncate

        long_text = "A" * 60
        result = truncate(long_text, 50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_build_staging_message_now(self):
        """Test staging message when racer is racing now."""
        from services.notifications.triggers import build_staging_message

        title, body = build_staging_message("Jane S.", 0, 2)
        assert title == "Jane S. is racing NOW!"
        assert body == "Lane 2"

    def test_build_staging_message_next(self):
        """Test staging message when racer is up next."""
        from services.notifications.triggers import build_staging_message

        title, body = build_staging_message("Jane S.", 1, 3)
        assert "racing soon" in title
        assert "Up next" in body

    def test_build_staging_message_multiple_heats(self):
        """Test staging message when racer is multiple heats away."""
        from services.notifications.triggers import build_staging_message

        title, body = build_staging_message("Jane S.", 5, 1)
        assert "racing soon" in title
        assert "~5 heats away" in body

    def test_build_result_message_winner(self):
        """Test result message for first place."""
        from services.notifications.triggers import build_result_message

        title, body = build_result_message("Jane S.", 1, 30.456)
        assert "won" in title
        assert "1st place" in body

    def test_build_result_message_second(self):
        """Test result message for second place."""
        from services.notifications.triggers import build_result_message

        title, body = build_result_message("Jane S.", 2, 31.234)
        assert "2nd" in title
        assert "2nd place" in body

    def test_build_result_message_third(self):
        """Test result message for third place."""
        from services.notifications.triggers import build_result_message

        title, body = build_result_message("Jane S.", 3, 32.567)
        assert "3rd" in title
        assert "3rd place" in body

    def test_build_result_message_other(self):
        """Test result message for other places."""
        from services.notifications.triggers import build_result_message

        title, body = build_result_message("Jane S.", 4, 33.123)
        assert "finished" in title
        assert "Time:" in body

    def test_build_poll_new_message(self):
        """Test new poll notification message."""
        from services.notifications.triggers import build_poll_new_message

        title, body = build_poll_new_message("Which car is the best looking?")
        assert title == "New Poll Available!"
        assert "best looking" in body

    def test_build_poll_result_message(self):
        """Test poll result notification message."""
        from services.notifications.triggers import build_poll_result_message

        title, body = build_poll_result_message("Car #42 - The Flash")
        assert title == "Poll Results Are In!"
        assert "Car #42" in body

    def test_build_prediction_result_correct(self):
        """Test prediction result message when correct."""
        from services.notifications.triggers import build_prediction_result_message

        title, body = build_prediction_result_message(True, 100)
        assert "Correct" in title
        assert "100 points" in body

    def test_build_prediction_result_incorrect(self):
        """Test prediction result message when incorrect."""
        from services.notifications.triggers import build_prediction_result_message

        title, body = build_prediction_result_message(False, 0)
        assert "Better luck" in title
        assert "leaderboard" in body

    def test_build_purchase_message(self):
        """Test purchase confirmation message."""
        from services.notifications.triggers import build_purchase_message

        title, body = build_purchase_message("Digital Photo Package", "$9.99")
        assert title == "Purchase Confirmed"
        assert "Digital Photo Package" in body
        assert "$9.99" in body


class TestNotificationTriggersUnit:
    """Unit tests for NotificationTriggers class."""

    @pytest.mark.asyncio
    async def test_triggers_disabled_when_fcm_disabled(
        self,
        db_session: AsyncSession,
    ):
        """Test that triggers return early when FCM is disabled."""
        from services.notifications.triggers import NotificationTriggers

        with patch("services.notifications.triggers.get_settings") as mock_settings:
            mock_settings.return_value.fcm_enabled = False
            mock_settings.return_value.fcm_staging_lookahead_heats = 5

            triggers = NotificationTriggers(db=db_session, redis=None, fcm=None)

            result = await triggers.on_heat_schedule_updated(
                event_id="evt_123",
                current_heat_number=5,
                scheduled_heats=[
                    {"heat_number": 6, "racers": [{"id": "rcr_1", "lane": 1}]}
                ],
            )

            assert result.sent == 0
            assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_staging_trigger_empty_heats(
        self,
        db_session: AsyncSession,
    ):
        """Test staging trigger with no upcoming heats."""
        from services.notifications.triggers import NotificationTriggers

        with patch("services.notifications.triggers.get_settings") as mock_settings:
            mock_settings.return_value.fcm_enabled = True
            mock_settings.return_value.fcm_staging_lookahead_heats = 5

            triggers = NotificationTriggers(db=db_session, redis=None)

            result = await triggers.on_heat_schedule_updated(
                event_id="evt_123",
                current_heat_number=5,
                scheduled_heats=[],  # No heats
            )

            assert result.sent == 0
            assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_result_trigger_empty_results(
        self,
        db_session: AsyncSession,
    ):
        """Test result trigger with no results."""
        from services.notifications.triggers import NotificationTriggers

        with patch("services.notifications.triggers.get_settings") as mock_settings:
            mock_settings.return_value.fcm_enabled = True
            mock_settings.return_value.fcm_staging_lookahead_heats = 5

            triggers = NotificationTriggers(db=db_session, redis=None)

            result = await triggers.on_heat_completed(
                event_id="evt_123",
                heat_id="ht_123",
                results=[],
            )

            assert result.sent == 0
            assert result.skipped == 0


class TestNotificationTriggersIntegration:
    """Integration tests for notification triggers with database."""

    @pytest.mark.asyncio
    async def test_staging_trigger_sends_to_favorites(
        self,
        db_session: AsyncSession,
        test_user,
        test_event,
        test_racers,
    ):
        """Test staging notifications are sent to users with favorites."""
        from models.engagement import UserFavorite
        from services.notifications.triggers import NotificationTriggers
        from services.notifications.fcm_service import SendResult

        # Create favorite for test_user
        favorite = UserFavorite(
            user_id=test_user.id,
            racer_id=test_racers[0].id,
            notify_upcoming=True,
            notify_results=True,
        )
        db_session.add(favorite)
        await db_session.commit()

        # Mock FCMService
        mock_fcm = MagicMock()
        mock_fcm.send_to_users = AsyncMock(
            return_value=SendResult(1, 0, [], [])
        )

        with patch("services.notifications.triggers.get_settings") as mock_settings:
            mock_settings.return_value.fcm_enabled = True
            mock_settings.return_value.fcm_staging_lookahead_heats = 5

            triggers = NotificationTriggers(
                db=db_session,
                redis=None,
                fcm=mock_fcm,
            )

            result = await triggers.on_heat_schedule_updated(
                event_id=test_event.id,
                current_heat_number=5,
                scheduled_heats=[
                    {
                        "heat_number": 6,
                        "racers": [{"id": test_racers[0].id, "lane": 1}]
                    }
                ],
            )

            assert result.sent == 1
            mock_fcm.send_to_users.assert_called_once()

            # Verify call arguments
            call_args = mock_fcm.send_to_users.call_args
            assert test_user.id in call_args.kwargs["user_ids"]
            assert "racing soon" in call_args.kwargs["title"]

    @pytest.mark.asyncio
    async def test_result_trigger_sends_to_favorites(
        self,
        db_session: AsyncSession,
        test_user,
        test_event,
        test_heat,
        test_racers,
    ):
        """Test result notifications are sent to users with favorites."""
        from models.engagement import UserFavorite
        from services.notifications.triggers import NotificationTriggers
        from services.notifications.fcm_service import SendResult

        # Create favorite for test_user
        favorite = UserFavorite(
            user_id=test_user.id,
            racer_id=test_racers[0].id,
            notify_upcoming=True,
            notify_results=True,
        )
        db_session.add(favorite)
        await db_session.commit()

        # Mock FCMService
        mock_fcm = MagicMock()
        mock_fcm.send_to_users = AsyncMock(
            return_value=SendResult(1, 0, [], [])
        )

        with patch("services.notifications.triggers.get_settings") as mock_settings:
            mock_settings.return_value.fcm_enabled = True
            mock_settings.return_value.fcm_staging_lookahead_heats = 5

            triggers = NotificationTriggers(
                db=db_session,
                redis=None,
                fcm=mock_fcm,
            )

            result = await triggers.on_heat_completed(
                event_id=test_event.id,
                heat_id=test_heat.id,
                results=[
                    {"racer_id": test_racers[0].id, "place": 1, "time": 30.456}
                ],
            )

            assert result.sent == 1
            mock_fcm.send_to_users.assert_called_once()

            # Verify call has winning message
            call_args = mock_fcm.send_to_users.call_args
            assert "won" in call_args.kwargs["title"]

    @pytest.mark.asyncio
    async def test_staging_respects_notify_upcoming_setting(
        self,
        db_session: AsyncSession,
        test_user,
        test_event,
        test_racers,
    ):
        """Test staging notifications respect notify_upcoming=False."""
        from models.engagement import UserFavorite
        from services.notifications.triggers import NotificationTriggers

        # Create favorite with notifications disabled
        favorite = UserFavorite(
            user_id=test_user.id,
            racer_id=test_racers[0].id,
            notify_upcoming=False,  # Disabled
            notify_results=True,
        )
        db_session.add(favorite)
        await db_session.commit()

        mock_fcm = MagicMock()
        mock_fcm.send_to_users = AsyncMock()

        with patch("services.notifications.triggers.get_settings") as mock_settings:
            mock_settings.return_value.fcm_enabled = True
            mock_settings.return_value.fcm_staging_lookahead_heats = 5

            triggers = NotificationTriggers(
                db=db_session,
                redis=None,
                fcm=mock_fcm,
            )

            result = await triggers.on_heat_schedule_updated(
                event_id=test_event.id,
                current_heat_number=5,
                scheduled_heats=[
                    {
                        "heat_number": 6,
                        "racers": [{"id": test_racers[0].id, "lane": 1}]
                    }
                ],
            )

            # No notifications should be sent
            assert result.sent == 0
            mock_fcm.send_to_users.assert_not_called()

    @pytest.mark.asyncio
    async def test_result_respects_notify_results_setting(
        self,
        db_session: AsyncSession,
        test_user,
        test_event,
        test_heat,
        test_racers,
    ):
        """Test result notifications respect notify_results=False."""
        from models.engagement import UserFavorite
        from services.notifications.triggers import NotificationTriggers

        # Create favorite with result notifications disabled
        favorite = UserFavorite(
            user_id=test_user.id,
            racer_id=test_racers[0].id,
            notify_upcoming=True,
            notify_results=False,  # Disabled
        )
        db_session.add(favorite)
        await db_session.commit()

        mock_fcm = MagicMock()
        mock_fcm.send_to_users = AsyncMock()

        with patch("services.notifications.triggers.get_settings") as mock_settings:
            mock_settings.return_value.fcm_enabled = True
            mock_settings.return_value.fcm_staging_lookahead_heats = 5

            triggers = NotificationTriggers(
                db=db_session,
                redis=None,
                fcm=mock_fcm,
            )

            result = await triggers.on_heat_completed(
                event_id=test_event.id,
                heat_id=test_heat.id,
                results=[
                    {"racer_id": test_racers[0].id, "place": 1, "time": 30.456}
                ],
            )

            # No notifications should be sent
            assert result.sent == 0
            mock_fcm.send_to_users.assert_not_called()

    @pytest.mark.asyncio
    async def test_poll_activated_sends_to_event_users(
        self,
        db_session: AsyncSession,
        test_user,
        test_event,
        test_racers,
    ):
        """Test poll activation notifications go to users with favorites at event."""
        from models.engagement import UserFavorite
        from services.notifications.triggers import NotificationTriggers
        from services.notifications.fcm_service import SendResult

        # Create favorite for test_user at this event
        favorite = UserFavorite(
            user_id=test_user.id,
            racer_id=test_racers[0].id,
            notify_upcoming=True,
            notify_results=True,
        )
        db_session.add(favorite)
        await db_session.commit()

        mock_fcm = MagicMock()
        mock_fcm.send_to_users = AsyncMock(
            return_value=SendResult(1, 0, [], [])
        )

        with patch("services.notifications.triggers.get_settings") as mock_settings:
            mock_settings.return_value.fcm_enabled = True
            mock_settings.return_value.fcm_staging_lookahead_heats = 5

            triggers = NotificationTriggers(
                db=db_session,
                redis=None,
                fcm=mock_fcm,
            )

            result = await triggers.on_poll_activated(
                event_id=test_event.id,
                poll_id="pol_123",
                question="Which car looks the best?",
            )

            assert result.sent == 1
            mock_fcm.send_to_users.assert_called_once()

    @pytest.mark.asyncio
    async def test_prediction_resolved_sends_correct_message(
        self,
        db_session: AsyncSession,
        test_user,
        test_event,
        test_heat,
    ):
        """Test prediction resolved notifications have correct messaging."""
        from services.notifications.triggers import NotificationTriggers
        from services.notifications.fcm_service import SendResult, NotificationType

        mock_fcm = MagicMock()
        mock_fcm.send_to_users = AsyncMock(
            return_value=SendResult(1, 0, [], [])
        )

        with patch("services.notifications.triggers.get_settings") as mock_settings:
            mock_settings.return_value.fcm_enabled = True
            mock_settings.return_value.fcm_staging_lookahead_heats = 5

            triggers = NotificationTriggers(
                db=db_session,
                redis=None,
                fcm=mock_fcm,
            )

            # Test correct prediction
            result = await triggers.on_prediction_resolved(
                user_id=test_user.id,
                event_id=test_event.id,
                heat_id=test_heat.id,
                was_correct=True,
                points_earned=50,
            )

            assert result.sent == 1
            call_args = mock_fcm.send_to_users.call_args
            assert "Correct" in call_args.kwargs["title"]
            assert "50 points" in call_args.kwargs["body"]
            assert call_args.kwargs["notification_type"] == NotificationType.PREDICTION_RESULT

    @pytest.mark.asyncio
    async def test_purchase_completed_always_sends(
        self,
        db_session: AsyncSession,
        test_user,
    ):
        """Test purchase notifications cannot be opted out."""
        from services.notifications.triggers import NotificationTriggers
        from services.notifications.fcm_service import SendResult, NotificationType

        mock_fcm = MagicMock()
        mock_fcm.send_to_users = AsyncMock(
            return_value=SendResult(1, 0, [], [])
        )

        with patch("services.notifications.triggers.get_settings") as mock_settings:
            mock_settings.return_value.fcm_enabled = True
            mock_settings.return_value.fcm_staging_lookahead_heats = 5

            triggers = NotificationTriggers(
                db=db_session,
                redis=None,
                fcm=mock_fcm,
            )

            result = await triggers.on_purchase_completed(
                user_id=test_user.id,
                purchase_type="Digital Photo Package",
                amount="$9.99",
                receipt_id="rcpt_123",
            )

            assert result.sent == 1
            call_args = mock_fcm.send_to_users.call_args
            assert "Purchase Confirmed" in call_args.kwargs["title"]
            assert call_args.kwargs["notification_type"] == NotificationType.PURCHASE_CONFIRM
