"""
Tests for the polls system.

Tests cover:
- Listing polls
- Getting poll details
- Voting in polls
- Viewing poll results
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.event import EventStatus
from models.engagement import PollStatus
from tests.factories import (
    UserFactory,
    OrganizationFactory,
    EventFactory,
    PollFactory,
    PollVoteFactory,
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
    """Create a public test event."""
    event = EventFactory.create(
        org_id=test_organization.id,
        is_public=True,
        status=EventStatus.PUBLISHED,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest.fixture
async def test_poll(db_session: AsyncSession, test_public_event):
    """Create an active test poll."""
    poll = PollFactory.create(
        event_id=test_public_event.id,
        question="Who has the Best Looking Car?",
        options=[
            {"id": "opt_1", "label": "Car #1 - Lightning"},
            {"id": "opt_2", "label": "Car #2 - Thunder"},
            {"id": "opt_3", "label": "Car #3 - Storm"},
        ],
        status=PollStatus.ACTIVE,
    )
    db_session.add(poll)
    await db_session.commit()
    await db_session.refresh(poll)
    return poll


@pytest.fixture
async def test_closed_poll(db_session: AsyncSession, test_public_event):
    """Create a closed test poll."""
    poll = PollFactory.create(
        event_id=test_public_event.id,
        question="Fan Favorite from last year?",
        options=[
            {"id": "opt_a", "label": "Racer A"},
            {"id": "opt_b", "label": "Racer B"},
        ],
        status=PollStatus.CLOSED,
    )
    db_session.add(poll)
    await db_session.commit()
    await db_session.refresh(poll)
    return poll


@pytest.fixture
async def test_draft_poll(db_session: AsyncSession, test_public_event):
    """Create a draft test poll (not visible)."""
    poll = PollFactory.create(
        event_id=test_public_event.id,
        question="Draft poll question?",
        status=PollStatus.DRAFT,
    )
    db_session.add(poll)
    await db_session.commit()
    await db_session.refresh(poll)
    return poll


@pytest.fixture
async def test_future_poll(db_session: AsyncSession, test_public_event):
    """Create a poll that opens in the future."""
    poll = PollFactory.create(
        event_id=test_public_event.id,
        question="Future poll?",
        status=PollStatus.ACTIVE,
        opens_at=datetime.utcnow() + timedelta(hours=1),
    )
    db_session.add(poll)
    await db_session.commit()
    await db_session.refresh(poll)
    return poll


@pytest.fixture
async def test_expired_poll(db_session: AsyncSession, test_public_event):
    """Create a poll that has expired."""
    poll = PollFactory.create(
        event_id=test_public_event.id,
        question="Expired poll?",
        status=PollStatus.ACTIVE,
        closes_at=datetime.utcnow() - timedelta(hours=1),
    )
    db_session.add(poll)
    await db_session.commit()
    await db_session.refresh(poll)
    return poll


# =============================================================================
# List Polls Tests
# =============================================================================


class TestListPolls:
    """Tests for listing polls."""

    async def test_list_active_polls(
        self,
        client: AsyncClient,
        event_url: str,
        test_poll,
    ):
        """Should list active polls by default."""
        response = await client.get(f"{event_url}/polls")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["id"] == test_poll.id
        assert data[0]["question"] == test_poll.question
        assert data[0]["status"] == "active"

    async def test_list_closed_polls(
        self,
        client: AsyncClient,
        event_url: str,
        test_poll,
        test_closed_poll,
    ):
        """Should list closed polls when filtered."""
        response = await client.get(f"{event_url}/polls?status=closed")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["id"] == test_closed_poll.id
        assert data[0]["status"] == "closed"

    async def test_list_all_polls(
        self,
        client: AsyncClient,
        event_url: str,
        test_poll,
        test_closed_poll,
        test_draft_poll,
    ):
        """Should list all non-draft polls when filtered."""
        response = await client.get(f"{event_url}/polls?status=all")

        assert response.status_code == 200
        data = response.json()["data"]
        # Should not include draft poll
        assert len(data) == 2
        poll_ids = [p["id"] for p in data]
        assert test_poll.id in poll_ids
        assert test_closed_poll.id in poll_ids
        assert test_draft_poll.id not in poll_ids

    async def test_list_polls_with_vote_counts(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        event_url: str,
        test_poll,
        test_user,
        second_user,
    ):
        """Should include vote counts in poll list."""
        # Add some votes
        from models.engagement import PollVote

        vote1 = PollVote(poll_id=test_poll.id, user_id=test_user.id, option_id="opt_1")
        vote2 = PollVote(poll_id=test_poll.id, user_id=second_user.id, option_id="opt_2")
        db_session.add(vote1)
        db_session.add(vote2)
        await db_session.commit()

        response = await client.get(f"{event_url}/polls")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data[0]["total_votes"] == 2

    async def test_list_polls_shows_user_voted_status(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        event_url: str,
        test_poll,
        test_user,
        auth_headers,
    ):
        """Should show if user has voted when authenticated."""
        # User votes
        from models.engagement import PollVote

        vote = PollVote(poll_id=test_poll.id, user_id=test_user.id, option_id="opt_1")
        db_session.add(vote)
        await db_session.commit()

        response = await client.get(f"{event_url}/polls", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data[0]["user_has_voted"] is True

    async def test_list_polls_is_public(
        self,
        client: AsyncClient,
        event_url: str,
        test_poll,
    ):
        """Poll list should be accessible without auth."""
        response = await client.get(f"{event_url}/polls")
        assert response.status_code == 200


# =============================================================================
# Get Poll Tests
# =============================================================================


class TestGetPoll:
    """Tests for getting poll details."""

    async def test_get_poll_success(
        self,
        client: AsyncClient,
        event_url: str,
        test_poll,
    ):
        """Should return poll details with options."""
        response = await client.get(f"{event_url}/polls/{test_poll.id}")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == test_poll.id
        assert data["question"] == test_poll.question
        assert len(data["options"]) == 3
        assert data["options"][0]["id"] == "opt_1"
        assert data["options"][0]["label"] == "Car #1 - Lightning"

    async def test_get_poll_shows_user_vote(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        event_url: str,
        test_poll,
        test_user,
        auth_headers,
    ):
        """Should show user's vote when authenticated."""
        from models.engagement import PollVote

        vote = PollVote(poll_id=test_poll.id, user_id=test_user.id, option_id="opt_2")
        db_session.add(vote)
        await db_session.commit()

        response = await client.get(
            f"{event_url}/polls/{test_poll.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["user_has_voted"] is True
        assert data["user_vote_option_id"] == "opt_2"

    async def test_get_poll_not_found(
        self,
        client: AsyncClient,
        event_url: str,
    ):
        """Should return 404 for non-existent poll."""
        response = await client.get(f"{event_url}/polls/pol_nonexistent")
        assert response.status_code == 404

    async def test_get_draft_poll_not_found(
        self,
        client: AsyncClient,
        event_url: str,
        test_draft_poll,
    ):
        """Should not return draft polls."""
        response = await client.get(f"{event_url}/polls/{test_draft_poll.id}")
        assert response.status_code == 404


# =============================================================================
# Vote Tests
# =============================================================================


class TestVoteInPoll:
    """Tests for voting in polls."""

    async def test_vote_success(
        self,
        client: AsyncClient,
        event_url: str,
        test_poll,
        auth_headers,
    ):
        """Should successfully vote in a poll."""
        response = await client.post(
            f"{event_url}/polls/{test_poll.id}/vote",
            json={"option_id": "opt_1"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["poll_id"] == test_poll.id
        assert data["option_id"] == "opt_1"

    async def test_vote_requires_auth(
        self,
        client: AsyncClient,
        event_url: str,
        test_poll,
    ):
        """Should require authentication to vote."""
        response = await client.post(
            f"{event_url}/polls/{test_poll.id}/vote",
            json={"option_id": "opt_1"},
        )
        assert response.status_code == 401

    async def test_vote_duplicate_rejected(
        self,
        client: AsyncClient,
        event_url: str,
        test_poll,
        auth_headers,
    ):
        """Should reject duplicate votes."""
        # First vote
        await client.post(
            f"{event_url}/polls/{test_poll.id}/vote",
            json={"option_id": "opt_1"},
            headers=auth_headers,
        )

        # Second vote attempt
        response = await client.post(
            f"{event_url}/polls/{test_poll.id}/vote",
            json={"option_id": "opt_2"},
            headers=auth_headers,
        )

        assert response.status_code == 409
        assert "already voted" in response.json()["detail"]["message"]

    async def test_vote_invalid_option(
        self,
        client: AsyncClient,
        event_url: str,
        test_poll,
        auth_headers,
    ):
        """Should reject invalid option ID."""
        response = await client.post(
            f"{event_url}/polls/{test_poll.id}/vote",
            json={"option_id": "invalid_option"},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Invalid option" in response.json()["detail"]["message"]

    async def test_vote_closed_poll_rejected(
        self,
        client: AsyncClient,
        event_url: str,
        test_closed_poll,
        auth_headers,
    ):
        """Should reject votes on closed polls."""
        response = await client.post(
            f"{event_url}/polls/{test_closed_poll.id}/vote",
            json={"option_id": "opt_a"},
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not accepting votes" in response.json()["detail"]["message"]

    async def test_vote_future_poll_rejected(
        self,
        client: AsyncClient,
        event_url: str,
        test_future_poll,
        auth_headers,
    ):
        """Should reject votes on polls that haven't opened yet."""
        response = await client.post(
            f"{event_url}/polls/{test_future_poll.id}/vote",
            json={"option_id": "opt_1"},
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not open yet" in response.json()["detail"]["message"]

    async def test_vote_expired_poll_rejected(
        self,
        client: AsyncClient,
        event_url: str,
        test_expired_poll,
        auth_headers,
    ):
        """Should reject votes on expired polls."""
        response = await client.post(
            f"{event_url}/polls/{test_expired_poll.id}/vote",
            json={"option_id": "opt_1"},
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "closed" in response.json()["detail"]["message"]

    async def test_vote_poll_not_found(
        self,
        client: AsyncClient,
        event_url: str,
        auth_headers,
    ):
        """Should return 404 for non-existent poll."""
        response = await client.post(
            f"{event_url}/polls/pol_nonexistent/vote",
            json={"option_id": "opt_1"},
            headers=auth_headers,
        )
        assert response.status_code == 404


# =============================================================================
# Poll Results Tests
# =============================================================================


class TestPollResults:
    """Tests for viewing poll results."""

    async def test_results_visible_after_voting(
        self,
        client: AsyncClient,
        event_url: str,
        test_poll,
        auth_headers,
    ):
        """Should show results after user votes."""
        # Vote first
        await client.post(
            f"{event_url}/polls/{test_poll.id}/vote",
            json={"option_id": "opt_1"},
            headers=auth_headers,
        )

        # Get results
        response = await client.get(
            f"{event_url}/polls/{test_poll.id}/results",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == test_poll.id
        assert data["total_votes"] == 1
        assert len(data["options"]) == 3

        # Find the voted option
        voted_opt = next(o for o in data["options"] if o["id"] == "opt_1")
        assert voted_opt["vote_count"] == 1
        assert voted_opt["vote_percent"] == 100.0

    async def test_results_visible_when_closed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        event_url: str,
        test_closed_poll,
        test_user,
        second_user,
    ):
        """Should show results for closed polls without auth."""
        # Add some votes
        from models.engagement import PollVote

        vote1 = PollVote(poll_id=test_closed_poll.id, user_id=test_user.id, option_id="opt_a")
        vote2 = PollVote(poll_id=test_closed_poll.id, user_id=second_user.id, option_id="opt_b")
        db_session.add(vote1)
        db_session.add(vote2)
        await db_session.commit()

        # Get results without auth
        response = await client.get(f"{event_url}/polls/{test_closed_poll.id}/results")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_votes"] == 2

    async def test_results_hidden_before_voting(
        self,
        client: AsyncClient,
        event_url: str,
        test_poll,
        auth_headers,
    ):
        """Should hide results if user hasn't voted and poll is open."""
        response = await client.get(
            f"{event_url}/polls/{test_poll.id}/results",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "after voting" in response.json()["detail"]["message"]

    async def test_results_hidden_without_auth_for_open_poll(
        self,
        client: AsyncClient,
        event_url: str,
        test_poll,
    ):
        """Should hide results for open polls without auth."""
        response = await client.get(f"{event_url}/polls/{test_poll.id}/results")

        assert response.status_code == 403

    async def test_results_show_vote_percentages(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        event_url: str,
        test_closed_poll,
        test_user,
        second_user,
    ):
        """Should calculate correct vote percentages."""
        from models.engagement import PollVote

        # 3 votes: 2 for opt_a, 1 for opt_b
        vote1 = PollVote(poll_id=test_closed_poll.id, user_id=test_user.id, option_id="opt_a")
        vote2 = PollVote(poll_id=test_closed_poll.id, user_id=second_user.id, option_id="opt_a")
        db_session.add(vote1)
        db_session.add(vote2)
        await db_session.commit()

        # Create third user and vote
        third_user = UserFactory.create()
        db_session.add(third_user)
        await db_session.commit()

        vote3 = PollVote(poll_id=test_closed_poll.id, user_id=third_user.id, option_id="opt_b")
        db_session.add(vote3)
        await db_session.commit()

        response = await client.get(f"{event_url}/polls/{test_closed_poll.id}/results")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_votes"] == 3

        opt_a = next(o for o in data["options"] if o["id"] == "opt_a")
        opt_b = next(o for o in data["options"] if o["id"] == "opt_b")

        assert opt_a["vote_count"] == 2
        assert opt_a["vote_percent"] == 66.7  # 2/3 = 66.7%
        assert opt_b["vote_count"] == 1
        assert opt_b["vote_percent"] == 33.3  # 1/3 = 33.3%

    async def test_results_show_user_vote(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        event_url: str,
        test_closed_poll,
        test_user,
        auth_headers,
    ):
        """Should show which option user voted for."""
        from models.engagement import PollVote

        vote = PollVote(poll_id=test_closed_poll.id, user_id=test_user.id, option_id="opt_b")
        db_session.add(vote)
        await db_session.commit()

        response = await client.get(
            f"{event_url}/polls/{test_closed_poll.id}/results",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["user_vote_option_id"] == "opt_b"

    async def test_results_poll_not_found(
        self,
        client: AsyncClient,
        event_url: str,
    ):
        """Should return 404 for non-existent poll."""
        response = await client.get(f"{event_url}/polls/pol_nonexistent/results")
        assert response.status_code == 404
