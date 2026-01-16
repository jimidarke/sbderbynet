"""
Tests for favorites endpoints.

Tests the /v1/me/favorites routes for managing user favorite racers.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import UserFavoriteFactory, RacerFactory, RacerClassFactory
from tests.mocks import create_test_token


class TestListFavorites:
    """Tests for listing user favorites."""

    @pytest.mark.asyncio
    async def test_list_favorites_empty(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test listing favorites when user has none."""
        response = await authenticated_client.get("/v1/me/favorites")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data == []

    @pytest.mark.asyncio
    async def test_list_favorites_with_data(
        self,
        authenticated_client: AsyncClient,
        test_user,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test listing favorites returns racer details."""
        # Add some favorites
        favorite = UserFavoriteFactory.create(
            user_id=test_user.id,
            racer_id=test_racers[0].id,
        )
        db_session.add(favorite)
        await db_session.commit()

        response = await authenticated_client.get("/v1/me/favorites")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["racer_id"] == test_racers[0].id
        assert data[0]["racer"]["first_name"] == test_racers[0].first_name
        assert data[0]["notify_upcoming"] is True
        assert data[0]["notify_results"] is True

    @pytest.mark.asyncio
    async def test_list_favorites_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that listing favorites requires authentication."""
        response = await client.get("/v1/me/favorites")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_favorites_multiple(
        self,
        authenticated_client: AsyncClient,
        test_user,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test listing multiple favorites."""
        # Add favorites for multiple racers
        for racer in test_racers[:3]:
            favorite = UserFavoriteFactory.create(
                user_id=test_user.id,
                racer_id=racer.id,
            )
            db_session.add(favorite)
        await db_session.commit()

        response = await authenticated_client.get("/v1/me/favorites")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 3


class TestAddFavorite:
    """Tests for adding favorites."""

    @pytest.mark.asyncio
    async def test_add_favorite(
        self,
        authenticated_client: AsyncClient,
        test_racers,
    ):
        """Test adding a racer to favorites."""
        response = await authenticated_client.post(
            "/v1/me/favorites",
            json={"racer_id": test_racers[0].id},
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["racer_id"] == test_racers[0].id
        assert data["racer"]["first_name"] == test_racers[0].first_name
        assert data["notify_upcoming"] is True
        assert data["notify_results"] is True

    @pytest.mark.asyncio
    async def test_add_favorite_custom_notifications(
        self,
        authenticated_client: AsyncClient,
        test_racers,
    ):
        """Test adding favorite with custom notification settings."""
        response = await authenticated_client.post(
            "/v1/me/favorites",
            json={
                "racer_id": test_racers[0].id,
                "notify_upcoming": False,
                "notify_results": True,
            },
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["notify_upcoming"] is False
        assert data["notify_results"] is True

    @pytest.mark.asyncio
    async def test_add_favorite_duplicate(
        self,
        authenticated_client: AsyncClient,
        test_user,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test that adding duplicate favorite returns 409."""
        # Add initial favorite
        favorite = UserFavoriteFactory.create(
            user_id=test_user.id,
            racer_id=test_racers[0].id,
        )
        db_session.add(favorite)
        await db_session.commit()

        # Try to add again
        response = await authenticated_client.post(
            "/v1/me/favorites",
            json={"racer_id": test_racers[0].id},
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_add_favorite_nonexistent_racer(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test adding nonexistent racer returns 404."""
        response = await authenticated_client.post(
            "/v1/me/favorites",
            json={"racer_id": "rcr_nonexistent"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_favorite_requires_auth(
        self,
        client: AsyncClient,
        test_racers,
    ):
        """Test that adding favorites requires authentication."""
        response = await client.post(
            "/v1/me/favorites",
            json={"racer_id": test_racers[0].id},
        )

        assert response.status_code == 401


class TestUpdateFavorite:
    """Tests for updating favorite notification settings."""

    @pytest.mark.asyncio
    async def test_update_favorite(
        self,
        authenticated_client: AsyncClient,
        test_user,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test updating favorite notification settings."""
        favorite = UserFavoriteFactory.create(
            user_id=test_user.id,
            racer_id=test_racers[0].id,
            notify_upcoming=True,
            notify_results=True,
        )
        db_session.add(favorite)
        await db_session.commit()

        response = await authenticated_client.patch(
            f"/v1/me/favorites/{test_racers[0].id}",
            json={"notify_upcoming": False},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["notify_upcoming"] is False
        assert data["notify_results"] is True  # unchanged

    @pytest.mark.asyncio
    async def test_update_favorite_both_settings(
        self,
        authenticated_client: AsyncClient,
        test_user,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test updating both notification settings."""
        favorite = UserFavoriteFactory.create(
            user_id=test_user.id,
            racer_id=test_racers[0].id,
        )
        db_session.add(favorite)
        await db_session.commit()

        response = await authenticated_client.patch(
            f"/v1/me/favorites/{test_racers[0].id}",
            json={
                "notify_upcoming": False,
                "notify_results": False,
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["notify_upcoming"] is False
        assert data["notify_results"] is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_favorite(
        self,
        authenticated_client: AsyncClient,
        test_racers,
    ):
        """Test updating nonexistent favorite returns 404."""
        response = await authenticated_client.patch(
            f"/v1/me/favorites/{test_racers[0].id}",
            json={"notify_upcoming": False},
        )

        assert response.status_code == 404


class TestRemoveFavorite:
    """Tests for removing favorites."""

    @pytest.mark.asyncio
    async def test_remove_favorite(
        self,
        authenticated_client: AsyncClient,
        test_user,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test removing a favorite."""
        favorite = UserFavoriteFactory.create(
            user_id=test_user.id,
            racer_id=test_racers[0].id,
        )
        db_session.add(favorite)
        await db_session.commit()

        response = await authenticated_client.delete(
            f"/v1/me/favorites/{test_racers[0].id}",
        )

        assert response.status_code == 204

        # Verify it's gone
        list_response = await authenticated_client.get("/v1/me/favorites")
        assert list_response.status_code == 200
        assert list_response.json()["data"] == []

    @pytest.mark.asyncio
    async def test_remove_nonexistent_favorite(
        self,
        authenticated_client: AsyncClient,
        test_racers,
    ):
        """Test removing nonexistent favorite returns 404."""
        response = await authenticated_client.delete(
            f"/v1/me/favorites/{test_racers[0].id}",
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_favorite_requires_auth(
        self,
        client: AsyncClient,
        test_racers,
    ):
        """Test that removing favorites requires authentication."""
        response = await client.delete(
            f"/v1/me/favorites/{test_racers[0].id}",
        )

        assert response.status_code == 401


class TestFavoritesCount:
    """Tests for favorites count endpoint."""

    @pytest.mark.asyncio
    async def test_favorites_count_empty(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test count when user has no favorites."""
        response = await authenticated_client.get("/v1/me/favorites/count")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_favorites_count_with_data(
        self,
        authenticated_client: AsyncClient,
        test_user,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test count with favorites."""
        # Add 3 favorites
        for racer in test_racers[:3]:
            favorite = UserFavoriteFactory.create(
                user_id=test_user.id,
                racer_id=racer.id,
            )
            db_session.add(favorite)
        await db_session.commit()

        response = await authenticated_client.get("/v1/me/favorites/count")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["count"] == 3


class TestFavoriteResponseStructure:
    """Tests for favorite response structure."""

    @pytest.mark.asyncio
    async def test_favorite_includes_racer_details(
        self,
        authenticated_client: AsyncClient,
        test_user,
        test_racers,
        test_racer_class,
        test_event,
        db_session: AsyncSession,
    ):
        """Test that favorite includes full racer details."""
        racer = test_racers[0]
        favorite = UserFavoriteFactory.create(
            user_id=test_user.id,
            racer_id=racer.id,
        )
        db_session.add(favorite)
        await db_session.commit()

        response = await authenticated_client.get("/v1/me/favorites")

        assert response.status_code == 200
        data = response.json()["data"][0]

        # Check racer info structure
        racer_info = data["racer"]
        assert "id" in racer_info
        assert "first_name" in racer_info
        assert "last_name" in racer_info
        assert "car_number" in racer_info
        assert "car_name" in racer_info
        assert "class_name" in racer_info
        assert "event_id" in racer_info
        assert "event_name" in racer_info

        # Check values
        assert racer_info["id"] == racer.id
        assert racer_info["first_name"] == racer.first_name
        assert racer_info["event_id"] == test_event.id

    @pytest.mark.asyncio
    async def test_favorite_includes_timestamps(
        self,
        authenticated_client: AsyncClient,
        test_racers,
    ):
        """Test that favorite includes created_at timestamp."""
        # Add a favorite
        response = await authenticated_client.post(
            "/v1/me/favorites",
            json={"racer_id": test_racers[0].id},
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert "created_at" in data
        assert data["created_at"] is not None


class TestUserIsolation:
    """Tests for user data isolation."""

    @pytest.mark.asyncio
    async def test_users_see_only_own_favorites(
        self,
        client: AsyncClient,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test that users can only see their own favorites."""
        from tests.factories import UserFactory

        # Create two users
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        db_session.add(user1)
        db_session.add(user2)
        await db_session.flush()

        # Create favorite for user1
        favorite = UserFavoriteFactory.create(
            user_id=user1.id,
            racer_id=test_racers[0].id,
        )
        db_session.add(favorite)
        await db_session.commit()

        # User1 should see the favorite
        token1 = create_test_token(user_id=user1.id, email=user1.email)
        client.headers["Authorization"] = f"Bearer {token1}"
        response1 = await client.get("/v1/me/favorites")
        assert response1.status_code == 200
        assert len(response1.json()["data"]) == 1

        # User2 should see no favorites
        token2 = create_test_token(user_id=user2.id, email=user2.email)
        client.headers["Authorization"] = f"Bearer {token2}"
        response2 = await client.get("/v1/me/favorites")
        assert response2.status_code == 200
        assert len(response2.json()["data"]) == 0

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_favorite(
        self,
        client: AsyncClient,
        test_racers,
        db_session: AsyncSession,
    ):
        """Test that users cannot delete other users' favorites."""
        from tests.factories import UserFactory

        # Create two users
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        db_session.add(user1)
        db_session.add(user2)
        await db_session.flush()

        # Create favorite for user1
        favorite = UserFavoriteFactory.create(
            user_id=user1.id,
            racer_id=test_racers[0].id,
        )
        db_session.add(favorite)
        await db_session.commit()

        # User2 tries to delete user1's favorite - should return 404
        token2 = create_test_token(user_id=user2.id, email=user2.email)
        client.headers["Authorization"] = f"Bearer {token2}"
        response = await client.delete(f"/v1/me/favorites/{test_racers[0].id}")
        assert response.status_code == 404
