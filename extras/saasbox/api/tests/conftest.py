"""
Pytest configuration and fixtures for the test suite.

This module provides:
- Async test configuration
- Database fixtures with test isolation
- Mock authentication
- HTTP client fixtures
- Factory fixtures for test data
"""
import asyncio
from datetime import datetime, date
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.database import get_db
from app.main import app
# Import Base from models and ensure all models are loaded for table creation
from models.base import Base
import models  # This imports all models via models/__init__.py
from tests.factories import (
    UserFactory,
    OrganizationFactory,
    EventFactory,
    RacerFactory,
    RacerClassFactory,
    RoundFactory,
    HeatFactory,
    RaceResultFactory,
    DeviceFactory,
    UserFavoriteFactory,
    PredictionFactory,
    CheerFactory,
    PollFactory,
    PollVoteFactory,
)
from tests.mocks import MockFirebaseAuth, create_test_token


# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Cached test settings instance
_test_settings: Settings | None = None


def get_test_settings() -> Settings:
    """Override settings for testing."""
    global _test_settings
    if _test_settings is None:
        _test_settings = Settings(
            environment="development",
            debug=True,
            database_url=TEST_DATABASE_URL,
            redis_url="redis://localhost:6379/15",  # Use separate DB for tests
            jwt_secret_key="test-secret-key-for-testing-only",
            jwt_algorithm="HS256",
            jwt_issuer="soapboxderbynet.com",
            firebase_project_id="test-project",
            alert_manager_enabled=False,  # Disable external logging in tests
        )
    return _test_settings


# Clear the lru_cache on get_settings and replace with test settings
# This must happen before any other imports that might call get_settings()
get_settings.cache_clear()

# Also override the lru_cache with our test settings function
# This patches get_settings in app.config so any module importing from there gets test settings
import app.config as app_config_module
app_config_module.get_settings = get_test_settings


@pytest.fixture(scope="session", autouse=True)
def ensure_test_settings():
    """Ensure test settings are used throughout the test session."""
    # Clear any cached settings
    if hasattr(get_settings, 'cache_clear'):
        get_settings.cache_clear()

    # Re-patch in case of reimports
    import app.config as config_mod
    config_mod.get_settings = get_test_settings

    # Also patch in jwt_handler module if already imported
    import sys
    if "modules.auth.jwt_handler" in sys.modules:
        sys.modules["modules.auth.jwt_handler"].get_settings = get_test_settings

    yield


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create async engine for each test function."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for each test."""
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database override."""

    # Create proper async generator that yields the test session
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    # Override dependencies
    app.dependency_overrides[get_settings] = get_test_settings
    app.dependency_overrides[get_db] = override_get_db

    # Mock Redis
    with patch("app.redis_client.get_redis") as mock_redis:
        mock_redis_client = AsyncMock()
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True
        mock_redis_client.setex.return_value = True
        mock_redis_client.ping.return_value = True
        mock_redis_client.incr.return_value = 1  # For rate limiting
        mock_redis_client.expire.return_value = True  # For rate limiting
        mock_redis_client.delete.return_value = 1
        mock_redis.return_value = mock_redis_client

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as ac:
            yield ac

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authenticated_client(
    client: AsyncClient,
    test_user,
) -> AsyncClient:
    """Client with authentication headers."""
    token = create_test_token(
        user_id=test_user.id,
        email=test_user.email,
        system_role=test_user.system_role.value,
        org_memberships=[],
    )
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def admin_client(
    client: AsyncClient,
    test_admin,
) -> AsyncClient:
    """Client with system admin authentication."""
    token = create_test_token(
        user_id=test_admin.id,
        email=test_admin.email,
        system_role="admin",
        org_memberships=[],
    )
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def org_admin_client(
    client: AsyncClient,
    test_user,
    test_organization,
) -> AsyncClient:
    """Client with organization admin authentication."""
    token = create_test_token(
        user_id=test_user.id,
        email=test_user.email,
        system_role="user",
        org_memberships=[{"id": test_organization.id, "role": "admin"}],
    )
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def org_member_client(
    client: AsyncClient,
    test_user,
    test_organization,
) -> AsyncClient:
    """Client with organization member authentication."""
    token = create_test_token(
        user_id=test_user.id,
        email=test_user.email,
        system_role="user",
        org_memberships=[{"id": test_organization.id, "role": "member"}],
    )
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# =============================================================================
# Data Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    user = UserFactory.create()
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession):
    """Create a test system admin."""
    from models.user import SystemRole
    admin = UserFactory.create(system_role=SystemRole.ADMIN)
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def test_organization(db_session: AsyncSession):
    """Create a test organization."""
    org = OrganizationFactory.create()
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_org_with_member(db_session: AsyncSession, test_user, test_organization):
    """Create organization with a member."""
    from models.organization import OrganizationMember, OrgRole

    membership = OrganizationMember(
        org_id=test_organization.id,
        user_id=test_user.id,
        role=OrgRole.MEMBER,
        joined_at=datetime.utcnow(),
        is_active=True,
    )
    db_session.add(membership)
    await db_session.commit()
    return test_organization


@pytest_asyncio.fixture
async def test_event(db_session: AsyncSession, test_organization):
    """Create a test event."""
    event_obj = EventFactory.create(org_id=test_organization.id)
    db_session.add(event_obj)
    await db_session.commit()
    await db_session.refresh(event_obj)
    return event_obj


@pytest_asyncio.fixture
async def test_public_event(db_session: AsyncSession, test_organization):
    """Create a public test event."""
    from models.event import EventStatus
    event_obj = EventFactory.create(
        org_id=test_organization.id,
        is_public=True,
        status=EventStatus.PUBLISHED,
    )
    db_session.add(event_obj)
    await db_session.commit()
    await db_session.refresh(event_obj)
    return event_obj


@pytest_asyncio.fixture
async def test_racer_class(db_session: AsyncSession, test_event):
    """Create a test racer class."""
    racer_class = RacerClassFactory.create(event_id=test_event.id)
    db_session.add(racer_class)
    await db_session.commit()
    await db_session.refresh(racer_class)
    return racer_class


@pytest_asyncio.fixture
async def test_racers(db_session: AsyncSession, test_event, test_racer_class):
    """Create multiple test racers."""
    racers = [
        RacerFactory.create(
            event_id=test_event.id,
            class_id=test_racer_class.id,
            car_number=i + 1,
        )
        for i in range(6)
    ]
    for racer in racers:
        db_session.add(racer)
    await db_session.commit()
    for racer in racers:
        await db_session.refresh(racer)
    return racers


@pytest_asyncio.fixture
async def test_round(db_session: AsyncSession, test_event, test_racer_class):
    """Create a test round."""
    round_obj = RoundFactory.create(
        event_id=test_event.id,
        class_id=test_racer_class.id,
    )
    db_session.add(round_obj)
    await db_session.commit()
    await db_session.refresh(round_obj)
    return round_obj


@pytest_asyncio.fixture
async def test_heat(db_session: AsyncSession, test_round):
    """Create a test heat."""
    heat = HeatFactory.create(round_id=test_round.id)
    db_session.add(heat)
    await db_session.commit()
    await db_session.refresh(heat)
    return heat


@pytest_asyncio.fixture
async def test_heat_with_results(db_session: AsyncSession, test_heat, test_racers):
    """Create a heat with race results."""
    from models.race import HeatStatus
    from decimal import Decimal

    results = []
    for i, racer in enumerate(test_racers[:3]):  # 3 lanes
        result = RaceResultFactory.create(
            heat_id=test_heat.id,
            racer_id=racer.id,
            lane=i + 1,
            finish_time=Decimal(f"3.{100 + i * 50:03d}"),
            finish_place=i + 1,
        )
        db_session.add(result)
        results.append(result)

    test_heat.status = HeatStatus.FINISHED
    await db_session.commit()

    for result in results:
        await db_session.refresh(result)

    return test_heat, results


@pytest_asyncio.fixture
async def test_device(db_session: AsyncSession, test_organization):
    """Create a test device."""
    device = DeviceFactory.create(org_id=test_organization.id)
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


@pytest_asyncio.fixture
async def full_event_setup(
    db_session: AsyncSession,
    test_organization,
    test_event,
    test_racer_class,
    test_racers,
    test_round,
    test_heat_with_results,
):
    """Complete event setup with all related data."""
    heat, results = test_heat_with_results
    return {
        "organization": test_organization,
        "event": test_event,
        "racer_class": test_racer_class,
        "racers": test_racers,
        "round": test_round,
        "heat": heat,
        "results": results,
    }
