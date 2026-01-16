"""
Tests for races module.

Tests cover:
- Current race polling endpoint
- Heat listing and filtering
- Race results
- Round listings
- Standings calculations
- Event statistics
- Access control for public/private events
"""
import pytest
from datetime import datetime
from decimal import Decimal
from httpx import AsyncClient

from tests.mocks import create_test_token


class TestCurrentRace:
    """Tests for current race polling endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_race_public_event(
        self,
        client: AsyncClient,
        test_organization,
        test_public_event,
        test_round,
        test_heat,
        db_session,
    ):
        """Test getting current race for public event without auth."""
        from models.race import HeatStatus

        # Mark heat as current and racing
        test_heat.is_current = True
        test_heat.status = HeatStatus.RACING
        await db_session.commit()

        response = await client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_public_event.id}/races/current",
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "now_racing" in data
        assert "race_status" in data
        assert "poll_interval" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_get_current_race_private_event_authenticated(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test getting current race for private event as member."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/current",
        )

        assert response.status_code == 200
        data = response.json()
        assert "race_status" in data

    @pytest.mark.asyncio
    async def test_get_current_race_private_event_unauthenticated(
        self,
        client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test that private events return 404 without auth."""
        response = await client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/current",
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_current_race_poll_intervals(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_round,
        test_heat,
        db_session,
    ):
        """Test that poll intervals vary by race status."""
        from models.race import HeatStatus

        # Test racing status - should have 1000ms interval
        test_heat.is_current = True
        test_heat.status = HeatStatus.RACING
        await db_session.commit()

        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/current",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["poll_interval"] == 1000
        assert data["race_status"] == "racing"

        # Test staging status - should have 2000ms interval
        test_heat.status = HeatStatus.STAGING
        await db_session.commit()

        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/current",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["poll_interval"] == 2000
        assert data["race_status"] == "staging"

    @pytest.mark.asyncio
    async def test_current_race_with_racers(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_heat_with_results,
        db_session,
    ):
        """Test current race includes racer information."""
        heat, results = test_heat_with_results

        # Mark as current
        heat.is_current = True
        await db_session.commit()

        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/current",
        )

        assert response.status_code == 200
        data = response.json()

        assert "racers" in data
        assert len(data["racers"]) > 0

        # Verify racer structure
        racer = data["racers"][0]
        assert "lane" in racer
        assert "racer" in racer
        assert "first_name" in racer["racer"]
        assert "last_name" in racer["racer"]
        assert "car_number" in racer["racer"]


class TestListRaces:
    """Tests for heat/race listing."""

    @pytest.mark.asyncio
    async def test_list_races_as_member(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_heat,
    ):
        """Test listing races as organization member."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races",
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio
    async def test_list_races_pagination(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
        test_round,
        db_session,
    ):
        """Test race list pagination."""
        from tests.factories import HeatFactory

        # Create multiple heats
        for i in range(5):
            heat = HeatFactory.create(
                round_id=test_round.id,
                heat_number=i + 1,
            )
            db_session.add(heat)
        await db_session.commit()

        # First page
        response = await org_admin_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races",
            params={"page": 1, "per_page": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 2

    @pytest.mark.asyncio
    async def test_list_races_filter_by_round(
        self,
        org_admin_client: AsyncClient,
        test_organization,
        test_event,
        test_round,
        test_heat,
    ):
        """Test filtering races by round."""
        response = await org_admin_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races",
            params={"round_id": test_round.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1

    @pytest.mark.asyncio
    async def test_list_races_public_event_no_auth(
        self,
        client: AsyncClient,
        test_organization,
        test_public_event,
        db_session,
    ):
        """Test listing races for public event without auth."""
        from tests.factories import RoundFactory, HeatFactory

        round_obj = RoundFactory.create(event_id=test_public_event.id)
        db_session.add(round_obj)
        await db_session.commit()

        heat = HeatFactory.create(round_id=round_obj.id)
        db_session.add(heat)
        await db_session.commit()

        response = await client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_public_event.id}/races",
        )

        assert response.status_code == 200


class TestGetRace:
    """Tests for getting individual heat/race."""

    @pytest.mark.asyncio
    async def test_get_race_as_member(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_heat,
    ):
        """Test getting heat details as member."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/{test_heat.id}",
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["id"] == test_heat.id
        assert "round_id" in data
        assert "heat_number" in data
        assert "status" in data
        assert "racers" in data

    @pytest.mark.asyncio
    async def test_get_race_with_results(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_heat_with_results,
    ):
        """Test getting heat includes race results."""
        heat, results = test_heat_with_results

        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/{heat.id}",
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert len(data["racers"]) == len(results)

        # Verify result data included
        for racer_in_lane in data["racers"]:
            assert "finish_time" in racer_in_lane
            assert "finish_place" in racer_in_lane

    @pytest.mark.asyncio
    async def test_get_nonexistent_race(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test getting non-existent race returns 404."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/ht_nonexistent",
        )

        assert response.status_code == 404


class TestRaceResults:
    """Tests for race results endpoint."""

    @pytest.mark.asyncio
    async def test_get_race_results(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_heat_with_results,
    ):
        """Test getting race results."""
        heat, results = test_heat_with_results

        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/{heat.id}/results",
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["heat_id"] == heat.id
        assert "results" in data
        assert len(data["results"]) == len(results)

        # Verify result structure
        result = data["results"][0]
        assert "id" in result
        assert "racer_id" in result
        assert "racer_name" in result
        assert "lane" in result
        assert "finish_time" in result
        assert "finish_place" in result

    @pytest.mark.asyncio
    async def test_results_sorted_by_place(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_heat_with_results,
    ):
        """Test results are sorted by finish place."""
        heat, _ = test_heat_with_results

        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/{heat.id}/results",
        )

        assert response.status_code == 200
        data = response.json()["data"]

        places = [r["finish_place"] for r in data["results"]]
        assert places == sorted(places)


class TestListRounds:
    """Tests for round listing."""

    @pytest.mark.asyncio
    async def test_list_rounds(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_round,
    ):
        """Test listing rounds for an event."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/rounds",
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert isinstance(data, list)
        assert len(data) >= 1

        # Verify round structure
        round_obj = data[0]
        assert "id" in round_obj
        assert "name" in round_obj
        assert "round_number" in round_obj
        assert "status" in round_obj
        assert "heats_scheduled" in round_obj
        assert "heats_completed" in round_obj
        assert "is_current" in round_obj

    @pytest.mark.asyncio
    async def test_list_rounds_public_event(
        self,
        client: AsyncClient,
        test_organization,
        test_public_event,
        db_session,
    ):
        """Test listing rounds for public event without auth."""
        from tests.factories import RoundFactory

        round_obj = RoundFactory.create(event_id=test_public_event.id)
        db_session.add(round_obj)
        await db_session.commit()

        response = await client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_public_event.id}/races/rounds",
        )

        assert response.status_code == 200


class TestRoundStandings:
    """Tests for round standings."""

    @pytest.mark.asyncio
    async def test_get_round_standings(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_round,
        test_heat_with_results,
    ):
        """Test getting standings for a round."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/rounds/{test_round.id}/standings",
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["round_id"] == test_round.id
        assert "round_name" in data
        assert "standings" in data
        assert "heats_completed" in data
        assert "heats_total" in data

    @pytest.mark.asyncio
    async def test_standings_includes_racer_stats(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_round,
        test_heat_with_results,
    ):
        """Test standings include calculated stats."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/rounds/{test_round.id}/standings",
        )

        assert response.status_code == 200
        standings = response.json()["data"]["standings"]

        if len(standings) > 0:
            standing = standings[0]
            assert "rank" in standing
            assert "racer" in standing
            assert "races_completed" in standing
            assert "best_time" in standing
            assert "wins" in standing
            assert "podiums" in standing

    @pytest.mark.asyncio
    async def test_standings_sorted_by_best_time(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_round,
        test_heat_with_results,
    ):
        """Test standings are sorted correctly."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/rounds/{test_round.id}/standings",
        )

        assert response.status_code == 200
        standings = response.json()["data"]["standings"]

        # Ranks should be sequential
        ranks = [s["rank"] for s in standings]
        assert ranks == list(range(1, len(ranks) + 1))

    @pytest.mark.asyncio
    async def test_get_nonexistent_round_standings(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test getting standings for non-existent round."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/rounds/rnd_nonexistent/standings",
        )

        assert response.status_code == 404


class TestEventStats:
    """Tests for event statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_event_stats(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_racers,
        test_heat_with_results,
    ):
        """Test getting event statistics."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/stats",
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["event_id"] == test_event.id
        assert data["event_name"] == test_event.name
        assert "total_racers" in data
        assert "total_classes" in data
        assert "total_rounds" in data
        assert "total_heats" in data
        assert "heats_completed" in data
        assert "event_status" in data
        assert "is_racing" in data

    @pytest.mark.asyncio
    async def test_stats_includes_timing_info(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_heat_with_results,
    ):
        """Test stats include timing information when available."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/stats",
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # Timing info present when results exist
        assert "fastest_time" in data
        assert "fastest_racer" in data
        assert "average_time" in data

    @pytest.mark.asyncio
    async def test_stats_public_event_no_auth(
        self,
        client: AsyncClient,
        test_organization,
        test_public_event,
    ):
        """Test getting stats for public event without auth."""
        response = await client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_public_event.id}/races/stats",
        )

        assert response.status_code == 200


class TestRacePayloadValidation:
    """Tests for race response payload validation."""

    @pytest.mark.asyncio
    async def test_current_race_response_structure(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_heat_with_results,
        db_session,
    ):
        """Verify current race response has all expected fields."""
        heat, _ = test_heat_with_results
        heat.is_current = True
        await db_session.commit()

        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/current",
        )

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "now_racing",
            "race_status",
            "poll_interval",
            "updated_at",
            "racers",
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Type validation
        assert isinstance(data["now_racing"], bool)
        assert data["race_status"] in ["idle", "staging", "racing", "finished"]
        assert isinstance(data["poll_interval"], int)
        assert data["poll_interval"] > 0
        assert isinstance(data["racers"], list)

    @pytest.mark.asyncio
    async def test_heat_response_structure(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_heat,
    ):
        """Verify heat response has all expected fields."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/{test_heat.id}",
        )

        assert response.status_code == 200
        heat = response.json()["data"]

        required_fields = [
            "id",
            "round_id",
            "heat_number",
            "status",
            "is_current",
            "racers",
        ]

        for field in required_fields:
            assert field in heat, f"Missing field: {field}"

        # Type validation
        assert isinstance(heat["id"], str)
        assert heat["id"].startswith("ht_")
        assert isinstance(heat["heat_number"], int)
        assert isinstance(heat["is_current"], bool)
        assert isinstance(heat["racers"], list)

    @pytest.mark.asyncio
    async def test_race_result_time_format(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_heat_with_results,
    ):
        """Verify finish times are formatted correctly."""
        heat, _ = test_heat_with_results

        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/{heat.id}/results",
        )

        assert response.status_code == 200
        results = response.json()["data"]["results"]

        for result in results:
            if result["finish_time"] is not None:
                # Should be string format like "3.1234"
                assert isinstance(result["finish_time"], str)
                # Should be parseable as float
                float(result["finish_time"])

    @pytest.mark.asyncio
    async def test_standings_response_structure(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
        test_round,
        test_heat_with_results,
    ):
        """Verify standings response structure."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/rounds/{test_round.id}/standings",
        )

        assert response.status_code == 200
        data = response.json()["data"]

        required_fields = [
            "round_id",
            "round_name",
            "heats_completed",
            "heats_total",
            "standings",
            "use_points",
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        assert isinstance(data["standings"], list)
        assert isinstance(data["use_points"], bool)

    @pytest.mark.asyncio
    async def test_event_stats_response_structure(
        self,
        org_member_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Verify event stats response structure."""
        response = await org_member_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/races/stats",
        )

        assert response.status_code == 200
        data = response.json()["data"]

        required_fields = [
            "event_id",
            "event_name",
            "total_racers",
            "total_classes",
            "total_rounds",
            "total_heats",
            "heats_completed",
            "event_status",
            "is_racing",
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Type validation
        assert isinstance(data["total_racers"], int)
        assert isinstance(data["total_classes"], int)
        assert isinstance(data["total_rounds"], int)
        assert isinstance(data["total_heats"], int)
        assert isinstance(data["heats_completed"], int)
        assert isinstance(data["is_racing"], bool)
