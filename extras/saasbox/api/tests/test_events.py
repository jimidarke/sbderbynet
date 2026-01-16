"""
Tests for events module.

Tests cover:
- Event CRUD operations
- Event publishing
- Device sync
- Access control
- Payload validation
"""
import pytest
from datetime import date, timedelta
from httpx import AsyncClient

from tests.mocks import create_test_token


class TestEventCreate:
    """Tests for event creation."""

    @pytest.mark.asyncio
    async def test_create_event_as_org_admin(
        self,
        org_admin_client: AsyncClient,
        test_organization,
    ):
        """Test creating an event as organization admin."""
        payload = {
            "name": "Summer Derby 2025",
            "description": "Annual summer derby race",
            "event_date": str(date.today() + timedelta(days=60)),
            "location": {
                "venue_name": "Derby Park",
                "venue_address": "123 Race St",
                "city": "Calgary",
                "province": "Alberta",
            },
            "lanes": 3,
            "use_points": False,
            "settings": {
                "allow_predictions": True,
                "allow_cheers": True,
                "prediction_cutoff_minutes": 5,
                "max_cheers_per_racer": 5,
            },
        }

        response = await org_admin_client.post(
            f"/v1/orgs/{test_organization.id}/events",
            json=payload,
        )

        assert response.status_code == 201
        data = response.json()

        assert "data" in data
        event = data["data"]
        assert event["name"] == "Summer Derby 2025"
        assert event["description"] == "Annual summer derby race"
        assert event["lanes"] == 3
        assert event["status"] == "draft"
        assert event["is_public"] is False
        assert event["venue_name"] == "Derby Park"
        assert event["city"] == "Calgary"

    @pytest.mark.asyncio
    async def test_create_event_minimal_payload(
        self,
        org_admin_client: AsyncClient,
        test_organization,
    ):
        """Test creating event with minimal required fields."""
        payload = {
            "name": "Quick Event",
            "event_date": str(date.today() + timedelta(days=30)),
        }

        response = await org_admin_client.post(
            f"/v1/orgs/{test_organization.id}/events",
            json=payload,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == "Quick Event"
        assert data["lanes"] == 3  # Default value

    @pytest.mark.asyncio
    async def test_create_event_as_member_forbidden(
        self,
        org_member_client: AsyncClient,
        test_organization,
    ):
        """Test that regular members cannot create events."""
        payload = {
            "name": "Unauthorized Event",
            "event_date": str(date.today() + timedelta(days=30)),
        }

        response = await org_member_client.post(
            f"/v1/orgs/{test_organization.id}/events",
            json=payload,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_event_unauthenticated(
        self,
        client: AsyncClient,
        test_organization,
    ):
        """Test that unauthenticated requests are rejected."""
        payload = {
            "name": "No Auth Event",
            "event_date": str(date.today() + timedelta(days=30)),
        }

        response = await client.post(
            f"/v1/orgs/{test_organization.id}/events",
            json=payload,
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_event_invalid_payload(
        self,
        org_admin_client: AsyncClient,
        test_organization,
    ):
        """Test validation of invalid payloads."""
        # Missing required field
        response = await org_admin_client.post(
            f"/v1/orgs/{test_organization.id}/events",
            json={"name": "No Date Event"},
        )
        assert response.status_code == 422

        # Invalid lanes value
        response = await org_admin_client.post(
            f"/v1/orgs/{test_organization.id}/events",
            json={
                "name": "Bad Lanes",
                "event_date": str(date.today()),
                "lanes": 10,  # Max is 6
            },
        )
        assert response.status_code == 422

        # Empty name
        response = await org_admin_client.post(
            f"/v1/orgs/{test_organization.id}/events",
            json={
                "name": "",
                "event_date": str(date.today()),
            },
        )
        assert response.status_code == 422


class TestEventList:
    """Tests for event listing."""

    @pytest.mark.asyncio
    async def test_list_events_as_member(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test listing events as organization member."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events",
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)
        assert data["meta"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_events_pagination(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        db_session,
    ):
        """Test event list pagination."""
        from tests.factories import EventFactory

        # Create multiple events
        for i in range(5):
            event = EventFactory.create(org_id=test_organization.id)
            db_session.add(event)
        await db_session.commit()

        # First page
        response = await org_admin_client.get(
            f"/v1/orgs/{test_organization.id}/events",
            params={"page": 1, "per_page": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 2

        # Second page
        response = await org_admin_client.get(
            f"/v1/orgs/{test_organization.id}/events",
            params={"page": 2, "per_page": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

    @pytest.mark.asyncio
    async def test_list_events_status_filter(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test filtering events by status."""
        response = await org_admin_client.get(
            f"/v1/orgs/{test_organization.id}/events",
            params={"status": "draft"},
        )

        assert response.status_code == 200
        data = response.json()
        for event in data["data"]:
            assert event["status"] == "draft"


class TestEventGet:
    """Tests for getting individual events."""

    @pytest.mark.asyncio
    async def test_get_event_as_member(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test getting event details as member."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}",
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["id"] == test_event.id
        assert data["name"] == test_event.name
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_public_event_without_auth(
        self,
        client: AsyncClient,
        test_organization,
        test_public_event,
    ):
        """Test getting public event without authentication."""
        response = await client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_public_event.id}",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["is_public"] is True

    @pytest.mark.asyncio
    async def test_get_private_event_without_auth(
        self,
        client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test that private events require authentication."""
        response = await client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}",
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_event(
        self,
        org_member_client: AsyncClient,
        test_organization,
    ):
        """Test getting non-existent event."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/evt_nonexistent",
        )

        assert response.status_code == 404


class TestEventUpdate:
    """Tests for event updates."""

    @pytest.mark.asyncio
    async def test_update_event_as_admin(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test updating event as admin."""
        response = await org_admin_client.patch(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}",
            json={
                "name": "Updated Event Name",
                "description": "New description",
                "lanes": 4,
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["name"] == "Updated Event Name"
        assert data["description"] == "New description"
        assert data["lanes"] == 4

    @pytest.mark.asyncio
    async def test_update_event_partial(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test partial update (only some fields)."""
        original_name = test_event.name

        response = await org_admin_client.patch(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}",
            json={"description": "Only description changed"},
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # Name should be unchanged
        assert data["name"] == original_name
        assert data["description"] == "Only description changed"

    @pytest.mark.asyncio
    async def test_update_event_as_member_forbidden(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test that members cannot update events."""
        response = await org_member_client.patch(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}",
            json={"name": "Unauthorized Update"},
        )

        assert response.status_code == 403


class TestEventDelete:
    """Tests for event deletion."""

    @pytest.mark.asyncio
    async def test_delete_event_as_admin(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test soft-deleting event as admin."""
        response = await org_admin_client.delete(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}",
        )

        assert response.status_code == 204

        # Verify event is no longer accessible
        response = await org_admin_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}",
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_event_as_member_forbidden(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test that members cannot delete events."""
        response = await org_member_client.delete(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}",
        )

        assert response.status_code == 403


class TestEventPublish:
    """Tests for event publishing."""

    @pytest.mark.asyncio
    async def test_publish_event(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test publishing an event."""
        response = await org_admin_client.post(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/publish",
            json={"is_public": True},
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["is_public"] is True
        assert data["status"] == "published"

    @pytest.mark.asyncio
    async def test_unpublish_event(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_public_event,
    ):
        """Test unpublishing an event."""
        response = await org_admin_client.post(
            f"/v1/orgs/{test_organization.id}/events/{test_public_event.id}/publish",
            json={"is_public": False},
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["is_public"] is False


class TestEventSync:
    """Tests for device sync endpoint."""

    @pytest.mark.asyncio
    async def test_sync_status(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test getting sync status."""
        response = await org_admin_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/sync-status",
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["event_id"] == test_event.id
        assert "last_sync_at" in data
        assert "racer_count" in data
        assert "class_count" in data


class TestEventPayloadValidation:
    """Tests for payload structure validation."""

    @pytest.mark.asyncio
    async def test_event_response_structure(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Verify event response has all expected fields."""
        response = await org_admin_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}",
        )

        assert response.status_code == 200
        event = response.json()["data"]

        # Required fields
        required_fields = [
            "id",
            "org_id",
            "name",
            "event_date",
            "status",
            "is_public",
            "lanes",
            "use_points",
            "settings",
            "created_at",
        ]

        for field in required_fields:
            assert field in event, f"Missing field: {field}"

        # Type validation
        assert isinstance(event["id"], str)
        assert event["id"].startswith("evt_")
        assert isinstance(event["lanes"], int)
        assert isinstance(event["is_public"], bool)
        assert isinstance(event["settings"], dict)

    @pytest.mark.asyncio
    async def test_event_list_response_structure(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Verify event list response structure."""
        response = await org_admin_client.get(
            f"/v1/orgs/{test_organization.id}/events",
        )

        assert response.status_code == 200
        data = response.json()

        # Pagination meta
        assert "meta" in data
        meta = data["meta"]
        assert "total" in meta
        assert "page" in meta
        assert "per_page" in meta
        assert "total_pages" in meta

        # List items
        assert "data" in data
        assert isinstance(data["data"], list)

        if len(data["data"]) > 0:
            item = data["data"][0]
            assert "id" in item
            assert "name" in item
            assert "event_date" in item
            assert "status" in item
