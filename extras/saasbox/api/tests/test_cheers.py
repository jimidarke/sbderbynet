"""
Tests for the cheers system.

Tests cover:
- Sending cheers (with rate limiting)
- Getting cheer status
- Getting cheer counts
- Cheer leaderboard
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.event import EventStatus
from tests.factories import (
    UserFactory,
    OrganizationFactory,
    EventFactory,
    RacerFactory,
    RacerClassFactory,
    CheerFactory,
)
from tests.mocks import create_test_token


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def event_url(test_organization, test_public_event):
    """Build the base URL for audience endpoints."""
    return f"/v1/orgs/{test_organization.id}/events/{test_public_event.id}/audience"


@pytest.fixture
def auth_headers(test_user):
    """Create auth headers for test user."""
    token = create_test_token(
        user_id=test_user.id,
        email=test_user.email,
        system_role=test_user.system_role.value,
        org_memberships=[],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def second_user(db_session: AsyncSession):
    """Create a second test user."""
    user = UserFactory.create()
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def second_auth_headers(second_user):
    """Create auth headers for second user."""
    token = create_test_token(
        user_id=second_user.id,
        email=second_user.email,
        system_role=second_user.system_role.value,
        org_memberships=[],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_public_event(db_session: AsyncSession, test_organization):
    """Create a public test event with cheers enabled."""
    event = EventFactory.create(
        org_id=test_organization.id,
        is_public=True,
        status=EventStatus.PUBLISHED,
        settings={
            "allow_predictions": True,
            "allow_cheers": True,
            "max_cheers_per_racer": 5,
        },
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest.fixture
async def test_racer(db_session: AsyncSession, test_public_event):
    """Create a test racer for the public event."""
    racer_class = RacerClassFactory.create(event_id=test_public_event.id)
    db_session.add(racer_class)
    await db_session.commit()

    racer = RacerFactory.create(
        event_id=test_public_event.id,
        class_id=racer_class.id,
    )
    db_session.add(racer)
    await db_session.commit()
    await db_session.refresh(racer)
    return racer


@pytest.fixture
async def test_racers(db_session: AsyncSession, test_public_event):
    """Create multiple test racers for the public event."""
    racer_class = RacerClassFactory.create(event_id=test_public_event.id)
    db_session.add(racer_class)
    await db_session.commit()

    racers = [
        RacerFactory.create(
            event_id=test_public_event.id,
            class_id=racer_class.id,
            car_number=i + 1,
        )
        for i in range(5)
    ]
    for racer in racers:
        db_session.add(racer)
    await db_session.commit()
    for racer in racers:
        await db_session.refresh(racer)
    return racers


# =============================================================================
# Send Cheer Tests
# =============================================================================


class TestSendCheer:
    """Tests for sending cheers."""

    async def test_send_cheer_success(
        self,
        client: AsyncClient,
        event_url: str,
        test_racer,
        auth_headers,
    ):
        """Should successfully send a cheer."""
        response = await client.post(
            f"{event_url}/cheers/{test_racer.id}",
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["racer_id"] == test_racer.id
        assert data["racer"]["id"] == test_racer.id
        assert data["racer"]["first_name"] == test_racer.first_name
        assert "created_at" in data

    async def test_send_multiple_cheers(
        self,
        client: AsyncClient,
        event_url: str,
        test_racer,
        auth_headers,
    ):
        """Should be able to send multiple cheers up to the limit."""
        for i in range(3):
            response = await client.post(
                f"{event_url}/cheers/{test_racer.id}",
                headers=auth_headers,
            )
            assert response.status_code == 201

    async def test_rate_limit_exceeded(
        self,
        client: AsyncClient,
        event_url: str,
        test_racer,
        auth_headers,
    ):
        """Should reject cheers after rate limit exceeded."""
        # Send max cheers (5)
        for i in range(5):
            response = await client.post(
                f"{event_url}/cheers/{test_racer.id}",
                headers=auth_headers,
            )
            assert response.status_code == 201

        # 6th cheer should fail
        response = await client.post(
            f"{event_url}/cheers/{test_racer.id}",
            headers=auth_headers,
        )
        assert response.status_code == 429
        assert "Maximum cheers" in response.json()["detail"]["message"]

    async def test_cheers_disabled(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_organization,
        test_racer,
        auth_headers,
    ):
        """Should reject cheers when disabled for event."""
        # Create event with cheers disabled
        event = EventFactory.create(
            org_id=test_organization.id,
            is_public=True,
            status=EventStatus.PUBLISHED,
            settings={"allow_cheers": False},
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        # Create racer in this event
        racer_class = RacerClassFactory.create(event_id=event.id)
        db_session.add(racer_class)
        await db_session.commit()

        racer = RacerFactory.create(event_id=event.id, class_id=racer_class.id)
        db_session.add(racer)
        await db_session.commit()
        await db_session.refresh(racer)

        url = f"/v1/orgs/{test_organization.id}/events/{event.id}/audience/cheers/{racer.id}"
        response = await client.post(url, headers=auth_headers)

        assert response.status_code == 403
        assert "not allowed" in response.json()["detail"]["message"]

    async def test_cheer_racer_not_found(
        self,
        client: AsyncClient,
        event_url: str,
        auth_headers,
    ):
        """Should return 404 for non-existent racer."""
        response = await client.post(
            f"{event_url}/cheers/rcr_nonexistent",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_cheer_requires_auth(
        self,
        client: AsyncClient,
        event_url: str,
        test_racer,
    ):
        """Should require authentication to send cheers."""
        response = await client.post(f"{event_url}/cheers/{test_racer.id}")
        assert response.status_code == 401


# =============================================================================
# Cheer Status Tests
# =============================================================================


class TestCheerStatus:
    """Tests for getting user's cheer status."""

    async def test_get_status_no_cheers(
        self,
        client: AsyncClient,
        event_url: str,
        test_racer,
        auth_headers,
    ):
        """Should return status with zero cheers."""
        response = await client.get(
            f"{event_url}/cheers/{test_racer.id}/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["racer_id"] == test_racer.id
        assert data["cheers_sent"] == 0
        assert data["max_cheers"] == 5
        assert data["can_cheer"] is True

    async def test_get_status_with_cheers(
        self,
        client: AsyncClient,
        event_url: str,
        test_racer,
        auth_headers,
    ):
        """Should return correct count after sending cheers."""
        # Send 3 cheers
        for _ in range(3):
            await client.post(
                f"{event_url}/cheers/{test_racer.id}",
                headers=auth_headers,
            )

        response = await client.get(
            f"{event_url}/cheers/{test_racer.id}/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["cheers_sent"] == 3
        assert data["can_cheer"] is True

    async def test_get_status_at_limit(
        self,
        client: AsyncClient,
        event_url: str,
        test_racer,
        auth_headers,
    ):
        """Should show can_cheer=False when at limit."""
        # Send max cheers
        for _ in range(5):
            await client.post(
                f"{event_url}/cheers/{test_racer.id}",
                headers=auth_headers,
            )

        response = await client.get(
            f"{event_url}/cheers/{test_racer.id}/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["cheers_sent"] == 5
        assert data["can_cheer"] is False


# =============================================================================
# Cheer Count Tests
# =============================================================================


class TestCheerCount:
    """Tests for getting cheer counts."""

    async def test_get_count_no_cheers(
        self,
        client: AsyncClient,
        event_url: str,
        test_racer,
    ):
        """Should return zero count with no cheers."""
        response = await client.get(f"{event_url}/cheers/{test_racer.id}/count")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["racer_id"] == test_racer.id
        assert data["cheer_count"] == 0

    async def test_get_count_with_cheers(
        self,
        client: AsyncClient,
        event_url: str,
        test_racer,
        auth_headers,
    ):
        """Should return correct total cheer count."""
        # Send some cheers
        for _ in range(3):
            await client.post(
                f"{event_url}/cheers/{test_racer.id}",
                headers=auth_headers,
            )

        response = await client.get(f"{event_url}/cheers/{test_racer.id}/count")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["cheer_count"] == 3

    async def test_count_aggregates_all_users(
        self,
        client: AsyncClient,
        event_url: str,
        test_racer,
        auth_headers,
        second_auth_headers,
    ):
        """Should aggregate cheers from multiple users."""
        # First user sends 3 cheers
        for _ in range(3):
            await client.post(
                f"{event_url}/cheers/{test_racer.id}",
                headers=auth_headers,
            )

        # Second user sends 2 cheers
        for _ in range(2):
            await client.post(
                f"{event_url}/cheers/{test_racer.id}",
                headers=second_auth_headers,
            )

        response = await client.get(f"{event_url}/cheers/{test_racer.id}/count")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["cheer_count"] == 5

    async def test_count_is_public(
        self,
        client: AsyncClient,
        event_url: str,
        test_racer,
    ):
        """Cheer count should be accessible without auth."""
        response = await client.get(f"{event_url}/cheers/{test_racer.id}/count")
        assert response.status_code == 200


# =============================================================================
# Cheer Leaderboard Tests
# =============================================================================


class TestCheerLeaderboard:
    """Tests for the cheer leaderboard."""

    async def test_leaderboard_empty(
        self,
        client: AsyncClient,
        event_url: str,
        test_racers,
    ):
        """Should return empty leaderboard with no cheers."""
        response = await client.get(f"{event_url}/cheers/leaderboard")

        assert response.status_code == 200
        data = response.json()["data"]
        # All racers appear with 0 cheers
        assert len(data["entries"]) == len(test_racers)
        for entry in data["entries"]:
            assert entry["total_cheers"] == 0
            assert entry["unique_supporters"] == 0

    async def test_leaderboard_ordered_by_cheers(
        self,
        client: AsyncClient,
        event_url: str,
        test_racers,
        auth_headers,
        second_auth_headers,
    ):
        """Should order racers by total cheers descending."""
        # Give racers different cheer counts
        # Racer 0: 5 cheers (3 from user1, 2 from user2)
        # Racer 1: 2 cheers (2 from user1)
        # Racer 2: 1 cheer (1 from user2)

        for _ in range(3):
            await client.post(
                f"{event_url}/cheers/{test_racers[0].id}",
                headers=auth_headers,
            )

        for _ in range(2):
            await client.post(
                f"{event_url}/cheers/{test_racers[0].id}",
                headers=second_auth_headers,
            )

        for _ in range(2):
            await client.post(
                f"{event_url}/cheers/{test_racers[1].id}",
                headers=auth_headers,
            )

        await client.post(
            f"{event_url}/cheers/{test_racers[2].id}",
            headers=second_auth_headers,
        )

        response = await client.get(f"{event_url}/cheers/leaderboard")

        assert response.status_code == 200
        data = response.json()["data"]
        entries = data["entries"]

        # First racer should have the most cheers
        assert entries[0]["racer_id"] == test_racers[0].id
        assert entries[0]["total_cheers"] == 5
        assert entries[0]["unique_supporters"] == 2

    async def test_leaderboard_limit(
        self,
        client: AsyncClient,
        event_url: str,
        test_racers,
    ):
        """Should respect limit parameter."""
        response = await client.get(f"{event_url}/cheers/leaderboard?limit=2")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["entries"]) == 2

    async def test_leaderboard_is_public(
        self,
        client: AsyncClient,
        event_url: str,
        test_racers,
    ):
        """Leaderboard should be accessible without auth."""
        response = await client.get(f"{event_url}/cheers/leaderboard")
        assert response.status_code == 200
