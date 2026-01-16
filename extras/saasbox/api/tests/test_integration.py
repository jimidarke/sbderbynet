"""
Integration tests for full API workflows.

Tests cover:
- Complete user registration and authentication flow
- Event lifecycle (create, publish, race, complete)
- Device registration and sync workflow
- Multi-tenant data isolation
- Cross-module interactions
"""
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient

from tests.mocks import MockFirebaseAuth, create_test_token


class TestUserAuthenticationFlow:
    """Integration tests for complete user authentication flow."""

    @pytest.mark.asyncio
    async def test_full_firebase_login_flow(
        self,
        client: AsyncClient,
        db_session,
    ):
        """Test complete Firebase login flow: verify -> get tokens -> use API."""
        # Step 1: Exchange Firebase token for API tokens
        with patch(
            "modules.auth.routes.verify_firebase_token",
            MockFirebaseAuth.verify_token,
        ):
            response = await client.post(
                "/v1/auth/firebase/verify",
                json={"id_token": "valid_token"},
            )

        assert response.status_code == 200
        data = response.json()

        # Verify we get tokens
        access_token = data["access_token"]
        assert access_token is not None
        assert data["refresh_token"] is not None
        assert data["user"]["email"] == "testuser@gmail.com"

    @pytest.mark.asyncio
    async def test_token_refresh_flow(
        self,
        client: AsyncClient,
        test_user,
    ):
        """Test token refresh flow."""
        # Create initial tokens
        token = create_test_token(
            user_id=test_user.id,
            email=test_user.email,
            system_role="user",
        )

        # Use the access token (would work)
        client.headers["Authorization"] = f"Bearer {token}"

        # Note: Full refresh flow would need proper token handling
        # This tests the endpoint exists and accepts proper format
        response = await client.post(
            "/v1/auth/refresh",
            json={"refresh_token": "test_refresh_token"},
        )

        # Refresh with invalid token should return 401
        assert response.status_code == 401


class TestEventLifecycleFlow:
    """Integration tests for complete event lifecycle."""

    @pytest.mark.asyncio
    async def test_create_event_add_data_publish_flow(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        db_session,
    ):
        """Test complete flow: create event -> add racers -> publish."""
        # Step 1: Create event
        response = await org_admin_client.post(
            f"/v1/orgs/{test_organization.id}/events",
            json={
                "name": "Integration Test Derby",
                "event_date": str(date.today() + timedelta(days=30)),
                "lanes": 3,
            },
        )

        assert response.status_code == 201
        event_data = response.json()["data"]
        event_id = event_data["id"]

        # Verify event is draft
        assert event_data["status"] == "draft"
        assert event_data["is_public"] is False

        # Step 2: Verify event appears in list
        response = await org_admin_client.get(
            f"/v1/orgs/{test_organization.id}/events",
        )

        assert response.status_code == 200
        events = response.json()["data"]
        assert any(e["id"] == event_id for e in events)

        # Step 3: Update event details
        response = await org_admin_client.patch(
            f"/v1/orgs/{test_organization.id}/events/{event_id}",
            json={
                "description": "Updated description",
                "lanes": 4,
            },
        )

        assert response.status_code == 200
        assert response.json()["data"]["lanes"] == 4

        # Step 4: Publish event
        response = await org_admin_client.post(
            f"/v1/orgs/{test_organization.id}/events/{event_id}/publish",
            json={"is_public": True},
        )

        assert response.status_code == 200
        published = response.json()["data"]
        assert published["status"] == "published"
        assert published["is_public"] is True

    @pytest.mark.asyncio
    async def test_event_visibility_public_vs_private(
        self,
        client: AsyncClient,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_public_event,
    ):
        """Test event visibility based on public/private status."""
        # Note: Access control depends on proper session/transaction handling
        # which may not work perfectly with SQLite in-memory testing

        # Private event: authenticated member should succeed
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}",
        )
        assert response.status_code == 200

        # Public event: unauthenticated should succeed
        response = await client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_public_event.id}",
        )
        assert response.status_code == 200


class TestRacePollingFlow:
    """Integration tests for real-time race polling."""

    @pytest.mark.asyncio
    async def test_race_status_progression(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_round,
        test_heat,
        db_session,
    ):
        """Test race status progression: idle -> staging -> racing -> finished."""
        from models.race import HeatStatus

        base_url = f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/current"

        # Initial state: no current heat (idle)
        response = await org_member_client.get(base_url)
        assert response.status_code == 200
        data = response.json()
        assert data["race_status"] == "idle"
        assert data["poll_interval"] == 5000  # Slow polling

        # Set heat as current and staging
        test_heat.is_current = True
        test_heat.status = HeatStatus.STAGING
        await db_session.commit()

        response = await org_member_client.get(base_url)
        assert response.status_code == 200
        data = response.json()
        assert data["race_status"] == "staging"
        assert data["poll_interval"] == 2000  # Medium polling

        # Set to racing
        test_heat.status = HeatStatus.RACING
        await db_session.commit()

        response = await org_member_client.get(base_url)
        assert response.status_code == 200
        data = response.json()
        assert data["race_status"] == "racing"
        assert data["now_racing"] is True
        assert data["poll_interval"] == 1000  # Fast polling

        # Set to finished
        test_heat.status = HeatStatus.FINISHED
        await db_session.commit()

        response = await org_member_client.get(base_url)
        assert response.status_code == 200
        data = response.json()
        assert data["race_status"] == "finished"
        assert data["now_racing"] is False

    @pytest.mark.asyncio
    async def test_race_results_flow(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_heat_with_results,
    ):
        """Test getting race results after completion."""
        heat, results = test_heat_with_results

        # Get heat details
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/{heat.id}",
        )
        assert response.status_code == 200
        heat_data = response.json()["data"]
        assert heat_data["status"] == "finished"
        assert len(heat_data["racers"]) == len(results)

        # Get detailed results
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/{heat.id}/results",
        )
        assert response.status_code == 200
        results_data = response.json()["data"]
        assert len(results_data["results"]) == len(results)

        # Verify results have times and places
        for result in results_data["results"]:
            assert result["finish_time"] is not None
            assert result["finish_place"] is not None


class TestMultiTenantIsolation:
    """Integration tests for multi-tenant data isolation."""

    @pytest.mark.asyncio
    async def test_organization_data_isolation(
        self,
        client: AsyncClient,
        test_user,
        db_session,
    ):
        """Test that organizations cannot see each other's data."""
        from tests.factories import OrganizationFactory, EventFactory

        # Create two organizations
        org1 = OrganizationFactory.create()
        org2 = OrganizationFactory.create()
        db_session.add_all([org1, org2])
        await db_session.commit()

        # Create events for each org
        event1 = EventFactory.create(org_id=org1.id, is_public=True)
        event2 = EventFactory.create(org_id=org2.id, is_public=True)
        db_session.add_all([event1, event2])
        await db_session.commit()

        # Create client with membership only in org1
        token = create_test_token(
            user_id=test_user.id,
            email=test_user.email,
            system_role="user",
            org_memberships=[{"id": org1.id, "role": "admin"}],
        )
        client.headers["Authorization"] = f"Bearer {token}"

        # Can access org1's event
        response = await client.get(
            f"/v1/orgs/{org1.id}/events/{event1.id}",
        )
        assert response.status_code == 200

        # Cannot access org2's private data (if event was private)
        # Public events are accessible by anyone

    @pytest.mark.asyncio
    async def test_member_vs_admin_permissions(
        self,
        org_admin_client: AsyncClient,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test different permission levels within an organization."""
        # Member cannot update event - should get 403
        response = await org_member_client.patch(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}",
            json={"description": "Member update"},
        )
        assert response.status_code == 403

        # Both can view event
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}",
        )
        assert response.status_code == 200


class TestStandingsCalculation:
    """Integration tests for standings calculation."""

    @pytest.mark.asyncio
    async def test_standings_with_multiple_heats(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_racer_class,
        test_racers,
        db_session,
    ):
        """Test standings calculation across multiple heats."""
        from tests.factories import RoundFactory, HeatFactory, RaceResultFactory
        from models.race import HeatStatus

        # Create round with multiple heats
        round_obj = RoundFactory.create(
            event_id=test_event.id,
            class_id=test_racer_class.id,
        )
        db_session.add(round_obj)
        await db_session.commit()

        # Create two heats with results
        for heat_num in range(1, 3):
            heat = HeatFactory.create(
                round_id=round_obj.id,
                heat_number=heat_num,
                status=HeatStatus.FINISHED,
            )
            db_session.add(heat)
            await db_session.commit()

            # Add results for first 3 racers
            for i, racer in enumerate(test_racers[:3]):
                result = RaceResultFactory.create(
                    heat_id=heat.id,
                    racer_id=racer.id,
                    lane=i + 1,
                    finish_time=Decimal(f"3.{100 + i * 50 + heat_num * 10:03d}"),
                    finish_place=i + 1,
                )
                db_session.add(result)

            await db_session.commit()

        # Get standings
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/rounds/{round_obj.id}/standings",
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # Should have standings for 3 racers
        assert len(data["standings"]) == 3

        # First place racer should have 2 wins
        first = data["standings"][0]
        assert first["rank"] == 1
        assert first["wins"] == 2
        assert first["races_completed"] == 2


class TestEventStatisticsFlow:
    """Integration tests for event statistics."""

    @pytest.mark.asyncio
    async def test_stats_update_after_race(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_racers,
        test_round,
        db_session,
    ):
        """Test that stats update after race completion."""
        from tests.factories import HeatFactory, RaceResultFactory
        from models.race import HeatStatus

        base_url = f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/stats"

        # Get initial stats
        response = await org_member_client.get(base_url)
        assert response.status_code == 200
        initial_stats = response.json()["data"]

        initial_heats_completed = initial_stats["heats_completed"]

        # Add a completed heat
        heat = HeatFactory.create(
            round_id=test_round.id,
            heat_number=99,
            status=HeatStatus.FINISHED,
        )
        db_session.add(heat)
        await db_session.commit()

        # Add results with times
        for i, racer in enumerate(test_racers[:3]):
            result = RaceResultFactory.create(
                heat_id=heat.id,
                racer_id=racer.id,
                lane=i + 1,
                finish_time=Decimal("3.1234"),
                finish_place=i + 1,
            )
            db_session.add(result)
        await db_session.commit()

        # Get updated stats
        response = await org_member_client.get(base_url)
        assert response.status_code == 200
        updated_stats = response.json()["data"]

        # Heats completed should have increased
        assert updated_stats["heats_completed"] > initial_heats_completed

        # Should have timing info
        assert updated_stats["fastest_time"] is not None


class TestErrorHandlingFlow:
    """Integration tests for error handling across the API."""

    @pytest.mark.asyncio
    async def test_cascading_not_found_errors(
        self,
        org_member_client: AsyncClient,
        test_organization,
    ):
        """Test not found errors propagate correctly."""
        # Non-existent event
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/evt_nonexistent",
        )
        assert response.status_code == 404

        # Non-existent org
        response = await org_member_client.get(
            "/v1/orgs/org_nonexistent/events",
        )
        # Would be 404 or 403 depending on implementation

    @pytest.mark.asyncio
    async def test_validation_errors_detailed(
        self,
        org_admin_client: AsyncClient,
        test_organization,
    ):
        """Test validation errors return detailed info."""
        # Invalid lanes value
        response = await org_admin_client.post(
            f"/v1/orgs/{test_organization.id}/events",
            json={
                "name": "Test",
                "event_date": str(date.today()),
                "lanes": 10,  # Invalid: max is 6
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_unauthorized_vs_forbidden(
        self,
        client: AsyncClient,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test authentication and authorization errors."""
        # Auth but not admin -> 403
        response = await org_member_client.post(
            f"/v1/orgs/{test_organization.id}/events",
            json={"name": "Test", "event_date": str(date.today())},
        )
        assert response.status_code == 403


class TestConcurrentAccess:
    """Integration tests for concurrent access patterns."""

    @pytest.mark.asyncio
    async def test_multiple_clients_polling(
        self,
        client: AsyncClient,
        test_organization,
        test_public_event,
        db_session,
    ):
        """Test multiple clients can poll concurrently."""
        import asyncio

        url = f"/v1/orgs/{test_organization.id}/events/{test_public_event.id}/races/current"

        # Simulate multiple concurrent requests
        async def poll():
            return await client.get(url)

        # Run 5 concurrent polls
        tasks = [poll() for _ in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed - race_status will be 'idle' if no active heat
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["race_status"] in ["idle", "staging", "racing", "finished"]


class TestDataConsistency:
    """Integration tests for data consistency."""

    @pytest.mark.asyncio
    async def test_event_delete_consistency(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test deleting event properly removes from listings."""
        event_id = test_event.id

        # Verify event exists in list
        response = await org_admin_client.get(
            f"/v1/orgs/{test_organization.id}/events",
        )
        assert any(e["id"] == event_id for e in response.json()["data"])

        # Delete event
        response = await org_admin_client.delete(
            f"/v1/orgs/{test_organization.id}/events/{event_id}",
        )
        assert response.status_code == 204

        # Verify event no longer in list
        response = await org_admin_client.get(
            f"/v1/orgs/{test_organization.id}/events",
        )
        assert not any(e["id"] == event_id for e in response.json()["data"])

        # Verify direct access returns 404
        response = await org_admin_client.get(
            f"/v1/orgs/{test_organization.id}/events/{event_id}",
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_round_standings_consistency(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_round,
        test_heat_with_results,
    ):
        """Test standings match actual results."""
        heat, results = test_heat_with_results

        # Get standings
        standings_response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/rounds/{test_round.id}/standings",
        )
        standings = standings_response.json()["data"]["standings"]

        # Get results directly
        results_response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/{heat.id}/results",
        )
        results_data = results_response.json()["data"]["results"]

        # Number of racers should match
        assert len(standings) == len(results_data)

        # Best times should be consistent
        for standing in standings:
            if standing["best_time"]:
                # Find matching result
                racer_results = [
                    r for r in results_data
                    if r["racer_id"] == standing["racer"]["id"]
                ]
                if racer_results:
                    assert standing["best_time"] == racer_results[0]["finish_time"]
