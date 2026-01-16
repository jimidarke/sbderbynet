"""
Tests for prediction game endpoints.

Tests the /v1/orgs/{org_id}/events/{event_id}/audience/predictions routes.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    UserFactory,
    PredictionFactory,
    RacerFactory,
    HeatFactory,
    RaceResultFactory,
    RoundFactory,
)
from tests.mocks import create_test_token


class TestCreatePrediction:
    """Tests for creating predictions."""

    @pytest.mark.asyncio
    async def test_create_prediction(
        self,
        authenticated_client: AsyncClient,
        test_organization,
        test_event,
        test_racers,
        test_round,
        db_session: AsyncSession,
    ):
        """Test creating a prediction for a heat."""
        # Create a heat with racer entries
        heat = HeatFactory.create(round_id=test_round.id)
        db_session.add(heat)
        await db_session.flush()

        # Add racer to heat
        result = RaceResultFactory.create(
            heat_id=heat.id,
            racer_id=test_racers[0].id,
            lane=1,
        )
        db_session.add(result)
        await db_session.commit()

        response = await authenticated_client.post(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions",
            json={
                "heat_id": heat.id,
                "predicted_racer_id": test_racers[0].id,
            },
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["heat_id"] == heat.id
        assert data["predicted_racer_id"] == test_racers[0].id
        assert data["is_correct"] is None  # Not yet resolved
        assert data["points_earned"] == 0

    @pytest.mark.asyncio
    async def test_create_prediction_requires_auth(
        self,
        client: AsyncClient,
        test_organization,
        test_event,
        test_heat,
        test_racers,
    ):
        """Test that creating predictions requires authentication."""
        response = await client.post(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions",
            json={
                "heat_id": test_heat.id,
                "predicted_racer_id": test_racers[0].id,
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_prediction_duplicate(
        self,
        authenticated_client: AsyncClient,
        test_user,
        test_organization,
        test_event,
        test_racers,
        test_round,
        db_session: AsyncSession,
    ):
        """Test that duplicate predictions return 409."""
        # Create heat with racer
        heat = HeatFactory.create(round_id=test_round.id)
        db_session.add(heat)
        await db_session.flush()

        result = RaceResultFactory.create(
            heat_id=heat.id,
            racer_id=test_racers[0].id,
            lane=1,
        )
        db_session.add(result)

        # Create existing prediction
        prediction = PredictionFactory.create(
            user_id=test_user.id,
            heat_id=heat.id,
            predicted_racer_id=test_racers[0].id,
        )
        db_session.add(prediction)
        await db_session.commit()

        # Try to create another
        response = await authenticated_client.post(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions",
            json={
                "heat_id": heat.id,
                "predicted_racer_id": test_racers[0].id,
            },
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_prediction_racer_not_in_heat(
        self,
        authenticated_client: AsyncClient,
        test_organization,
        test_event,
        test_racers,
        test_round,
        db_session: AsyncSession,
    ):
        """Test prediction fails if racer not in heat."""
        # Create heat without the racer
        heat = HeatFactory.create(round_id=test_round.id)
        db_session.add(heat)
        await db_session.commit()

        response = await authenticated_client.post(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions",
            json={
                "heat_id": heat.id,
                "predicted_racer_id": test_racers[0].id,
            },
        )

        assert response.status_code == 400
        assert "not participating" in response.json()["detail"]["message"]

    @pytest.mark.asyncio
    async def test_create_prediction_heat_already_started(
        self,
        authenticated_client: AsyncClient,
        test_organization,
        test_event,
        test_racers,
        test_round,
        db_session: AsyncSession,
    ):
        """Test prediction fails if heat already started."""
        from models.race import HeatStatus

        # Create finished heat
        heat = HeatFactory.create(
            round_id=test_round.id,
            status=HeatStatus.FINISHED,
        )
        db_session.add(heat)
        await db_session.flush()

        result = RaceResultFactory.create(
            heat_id=heat.id,
            racer_id=test_racers[0].id,
            lane=1,
        )
        db_session.add(result)
        await db_session.commit()

        response = await authenticated_client.post(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions",
            json={
                "heat_id": heat.id,
                "predicted_racer_id": test_racers[0].id,
            },
        )

        assert response.status_code == 400
        assert "already started" in response.json()["detail"]["message"]

    @pytest.mark.asyncio
    async def test_create_prediction_nonexistent_heat(
        self,
        authenticated_client: AsyncClient,
        test_organization,
        test_event,
        test_racers,
    ):
        """Test prediction fails for nonexistent heat."""
        response = await authenticated_client.post(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions",
            json={
                "heat_id": "ht_nonexistent",
                "predicted_racer_id": test_racers[0].id,
            },
        )

        assert response.status_code == 404


class TestListPredictions:
    """Tests for listing user predictions."""

    @pytest.mark.asyncio
    async def test_list_predictions_empty(
        self,
        authenticated_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test listing predictions when user has none."""
        response = await authenticated_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions",
        )

        assert response.status_code == 200
        assert response.json()["data"] == []

    @pytest.mark.asyncio
    async def test_list_predictions_with_data(
        self,
        authenticated_client: AsyncClient,
        test_user,
        test_organization,
        test_event,
        test_racers,
        test_round,
        test_heat,
        db_session: AsyncSession,
    ):
        """Test listing predictions returns correct data."""
        # Add racer to heat
        result = RaceResultFactory.create(
            heat_id=test_heat.id,
            racer_id=test_racers[0].id,
            lane=1,
        )
        db_session.add(result)

        # Create prediction
        prediction = PredictionFactory.create(
            user_id=test_user.id,
            heat_id=test_heat.id,
            predicted_racer_id=test_racers[0].id,
        )
        db_session.add(prediction)
        await db_session.commit()

        response = await authenticated_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["heat_id"] == test_heat.id
        assert data[0]["predicted_racer"]["id"] == test_racers[0].id


class TestLeaderboard:
    """Tests for prediction leaderboard."""

    @pytest.mark.asyncio
    async def test_leaderboard_empty(
        self,
        client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test leaderboard with no predictions."""
        response = await client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions/leaderboard",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_participants"] == 0
        assert data["entries"] == []

    @pytest.mark.asyncio
    async def test_leaderboard_with_predictions(
        self,
        client: AsyncClient,
        test_organization,
        test_event,
        test_round,
        test_heat,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test leaderboard shows correct rankings."""
        # Create users
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        db_session.add(user1)
        db_session.add(user2)
        await db_session.flush()

        # User1: 2 correct predictions (20 points)
        pred1 = PredictionFactory.create(
            user_id=user1.id,
            heat_id=test_heat.id,
            predicted_racer_id=test_racers[0].id,
            is_correct=True,
            points_earned=10,
        )
        db_session.add(pred1)

        # User2: 1 correct prediction (10 points)
        pred2 = PredictionFactory.create(
            user_id=user2.id,
            heat_id=test_heat.id,
            predicted_racer_id=test_racers[1].id,
            is_correct=True,
            points_earned=10,
        )
        db_session.add(pred2)
        await db_session.commit()

        response = await client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions/leaderboard",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_participants"] == 2
        assert len(data["entries"]) == 2
        # Both have same points, order may vary
        assert all(e["total_points"] == 10 for e in data["entries"])

    @pytest.mark.asyncio
    async def test_leaderboard_no_auth_required(
        self,
        client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test leaderboard is public - no auth required."""
        response = await client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions/leaderboard",
        )

        # Should succeed without auth
        assert response.status_code == 200


class TestPredictionStats:
    """Tests for user prediction stats."""

    @pytest.mark.asyncio
    async def test_stats_no_predictions(
        self,
        authenticated_client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test stats with no predictions."""
        response = await authenticated_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions/stats",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_predictions"] == 0
        assert data["correct_predictions"] == 0
        assert data["total_points"] == 0

    @pytest.mark.asyncio
    async def test_stats_with_predictions(
        self,
        authenticated_client: AsyncClient,
        test_user,
        test_organization,
        test_event,
        test_round,
        test_heat,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test stats with predictions."""
        # Create predictions
        pred1 = PredictionFactory.create(
            user_id=test_user.id,
            heat_id=test_heat.id,
            predicted_racer_id=test_racers[0].id,
            is_correct=True,
            points_earned=10,
        )
        db_session.add(pred1)
        await db_session.commit()

        response = await authenticated_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions/stats",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_predictions"] == 1
        assert data["correct_predictions"] == 1
        assert data["total_points"] == 10
        assert data["accuracy_percent"] == 100.0


class TestUpcomingHeats:
    """Tests for upcoming heats endpoint."""

    @pytest.mark.asyncio
    async def test_upcoming_heats_empty(
        self,
        client: AsyncClient,
        test_organization,
        test_event,
    ):
        """Test upcoming heats when none scheduled."""
        response = await client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions/upcoming",
        )

        assert response.status_code == 200
        assert response.json()["data"] == []

    @pytest.mark.asyncio
    async def test_upcoming_heats_with_data(
        self,
        client: AsyncClient,
        test_organization,
        test_event,
        test_round,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test upcoming heats returns scheduled heats."""
        from models.race import HeatStatus

        # Create scheduled heat
        heat = HeatFactory.create(
            round_id=test_round.id,
            status=HeatStatus.SCHEDULED,
        )
        db_session.add(heat)
        await db_session.flush()

        # Add racers
        for i, racer in enumerate(test_racers[:3]):
            result = RaceResultFactory.create(
                heat_id=heat.id,
                racer_id=racer.id,
                lane=i + 1,
            )
            db_session.add(result)
        await db_session.commit()

        response = await client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions/upcoming",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["heat_id"] == heat.id
        assert len(data[0]["racers"]) == 3

    @pytest.mark.asyncio
    async def test_upcoming_heats_shows_user_prediction_status(
        self,
        authenticated_client: AsyncClient,
        test_user,
        test_organization,
        test_event,
        test_round,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test upcoming heats shows if user has predicted."""
        from models.race import HeatStatus

        # Create two scheduled heats
        heat1 = HeatFactory.create(round_id=test_round.id, status=HeatStatus.SCHEDULED, heat_number=1)
        heat2 = HeatFactory.create(round_id=test_round.id, status=HeatStatus.SCHEDULED, heat_number=2)
        db_session.add(heat1)
        db_session.add(heat2)
        await db_session.flush()

        # Add racers to both heats
        for heat in [heat1, heat2]:
            result = RaceResultFactory.create(
                heat_id=heat.id,
                racer_id=test_racers[0].id,
                lane=1,
            )
            db_session.add(result)

        # User has predicted for heat1 only
        prediction = PredictionFactory.create(
            user_id=test_user.id,
            heat_id=heat1.id,
            predicted_racer_id=test_racers[0].id,
        )
        db_session.add(prediction)
        await db_session.commit()

        response = await authenticated_client.get(
            f"/v1/orgs/{test_organization.id}/events/{test_event.id}/audience/predictions/upcoming",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 2

        # Find heats by ID
        heat1_data = next(h for h in data if h["heat_id"] == heat1.id)
        heat2_data = next(h for h in data if h["heat_id"] == heat2.id)

        assert heat1_data["user_has_predicted"] is True
        assert heat2_data["user_has_predicted"] is False


class TestPredictionResolution:
    """Tests for prediction resolution."""

    @pytest.mark.asyncio
    async def test_resolve_predictions(
        self,
        test_user,
        test_round,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test resolving predictions when heat finishes."""
        from modules.audience.routes import resolve_heat_predictions
        from decimal import Decimal

        # Create heat
        heat = HeatFactory.create(round_id=test_round.id)
        db_session.add(heat)
        await db_session.flush()

        # Add race results - racer 0 wins
        for i, racer in enumerate(test_racers[:3]):
            result = RaceResultFactory.create(
                heat_id=heat.id,
                racer_id=racer.id,
                lane=i + 1,
                finish_time=Decimal(f"3.{100 + i * 50:03d}"),
                finish_place=i + 1,
            )
            db_session.add(result)

        # Create predictions - user predicted racer 0 (correct)
        prediction = PredictionFactory.create(
            user_id=test_user.id,
            heat_id=heat.id,
            predicted_racer_id=test_racers[0].id,
        )
        db_session.add(prediction)
        await db_session.commit()

        # Resolve
        resolved = await resolve_heat_predictions(heat.id, db_session)
        assert resolved == 1

        # Check prediction was updated
        await db_session.refresh(prediction)
        assert prediction.is_correct is True
        assert prediction.points_earned == 10

    @pytest.mark.asyncio
    async def test_resolve_predictions_incorrect(
        self,
        test_user,
        test_round,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test resolving incorrect prediction."""
        from modules.audience.routes import resolve_heat_predictions
        from decimal import Decimal

        # Create heat
        heat = HeatFactory.create(round_id=test_round.id)
        db_session.add(heat)
        await db_session.flush()

        # Add race results - racer 0 wins
        for i, racer in enumerate(test_racers[:3]):
            result = RaceResultFactory.create(
                heat_id=heat.id,
                racer_id=racer.id,
                lane=i + 1,
                finish_time=Decimal(f"3.{100 + i * 50:03d}"),
                finish_place=i + 1,
            )
            db_session.add(result)

        # Create prediction - user predicted racer 1 (incorrect)
        prediction = PredictionFactory.create(
            user_id=test_user.id,
            heat_id=heat.id,
            predicted_racer_id=test_racers[1].id,
        )
        db_session.add(prediction)
        await db_session.commit()

        # Resolve
        await resolve_heat_predictions(heat.id, db_session)

        # Check prediction was updated
        await db_session.refresh(prediction)
        assert prediction.is_correct is False
        assert prediction.points_earned == 0
