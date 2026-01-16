"""
Tests for Pydantic schema validation.

Tests cover:
- Field validation and constraints
- Type coercion
- Default values
- Required vs optional fields
- Nested object validation
- Custom validators
"""
import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pydantic import ValidationError


class TestEventSchemas:
    """Tests for event-related schemas."""

    def test_event_create_valid_minimal(self):
        """Test creating event with minimal required fields."""
        from modules.events.schemas import EventCreate

        event = EventCreate(
            name="Summer Derby 2025",
            event_date=date.today() + timedelta(days=30),
        )

        assert event.name == "Summer Derby 2025"
        assert event.lanes == 3  # Default
        assert event.use_points is False  # Default
        assert event.description is None
        assert event.location is None
        assert event.settings is None

    def test_event_create_valid_full(self):
        """Test creating event with all fields."""
        from modules.events.schemas import EventCreate, EventLocation, EventSettings

        event = EventCreate(
            name="Summer Derby 2025",
            description="Annual summer derby race",
            event_date=date.today() + timedelta(days=30),
            location=EventLocation(
                venue_name="Derby Park",
                venue_address="123 Race St",
                city="Calgary",
                province="Alberta",
            ),
            lanes=4,
            use_points=True,
            settings=EventSettings(
                allow_predictions=True,
                allow_cheers=True,
                prediction_cutoff_minutes=10,
                max_cheers_per_racer=3,
            ),
        )

        assert event.name == "Summer Derby 2025"
        assert event.description == "Annual summer derby race"
        assert event.lanes == 4
        assert event.use_points is True
        assert event.location.city == "Calgary"
        assert event.settings.prediction_cutoff_minutes == 10

    def test_event_create_missing_name(self):
        """Test validation error when name is missing."""
        from modules.events.schemas import EventCreate

        with pytest.raises(ValidationError) as exc_info:
            EventCreate(
                event_date=date.today(),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_event_create_missing_event_date(self):
        """Test validation error when event_date is missing."""
        from modules.events.schemas import EventCreate

        with pytest.raises(ValidationError) as exc_info:
            EventCreate(
                name="Test Event",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("event_date",) for e in errors)

    def test_event_create_empty_name(self):
        """Test validation error for empty name."""
        from modules.events.schemas import EventCreate

        with pytest.raises(ValidationError) as exc_info:
            EventCreate(
                name="",
                event_date=date.today(),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_event_create_name_too_long(self):
        """Test validation error for name exceeding max length."""
        from modules.events.schemas import EventCreate

        with pytest.raises(ValidationError) as exc_info:
            EventCreate(
                name="A" * 201,  # Max is 200
                event_date=date.today(),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_event_create_lanes_constraints(self):
        """Test lanes field constraints (2-6)."""
        from modules.events.schemas import EventCreate

        # Valid: minimum
        event = EventCreate(
            name="Test",
            event_date=date.today(),
            lanes=2,
        )
        assert event.lanes == 2

        # Valid: maximum
        event = EventCreate(
            name="Test",
            event_date=date.today(),
            lanes=6,
        )
        assert event.lanes == 6

        # Invalid: below minimum
        with pytest.raises(ValidationError) as exc_info:
            EventCreate(
                name="Test",
                event_date=date.today(),
                lanes=1,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("lanes",) for e in errors)

        # Invalid: above maximum
        with pytest.raises(ValidationError) as exc_info:
            EventCreate(
                name="Test",
                event_date=date.today(),
                lanes=7,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("lanes",) for e in errors)

    def test_event_update_partial(self):
        """Test partial update schema with optional fields."""
        from modules.events.schemas import EventUpdate

        # All fields optional
        update = EventUpdate()
        assert update.name is None
        assert update.event_date is None
        assert update.lanes is None

        # Partial update
        update = EventUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.description is None

    def test_event_settings_defaults(self):
        """Test EventSettings default values."""
        from modules.events.schemas import EventSettings

        settings = EventSettings()
        assert settings.allow_predictions is True
        assert settings.allow_cheers is True
        assert settings.prediction_cutoff_minutes == 5
        assert settings.max_cheers_per_racer == 5

    def test_event_location_all_optional(self):
        """Test EventLocation with all optional fields."""
        from modules.events.schemas import EventLocation

        location = EventLocation()
        assert location.venue_name is None
        assert location.city is None


class TestSyncSchemas:
    """Tests for sync data schemas."""

    def test_class_sync_data(self):
        """Test class sync data validation."""
        from modules.events.schemas import ClassSyncData

        data = ClassSyncData(
            derbynet_class_id=1,
            name="Ages 6-8",
            sort_order=1,
        )

        assert data.derbynet_class_id == 1
        assert data.name == "Ages 6-8"
        assert data.sort_order == 1

    def test_racer_sync_data(self):
        """Test racer sync data validation."""
        from modules.events.schemas import RacerSyncData

        data = RacerSyncData(
            derbynet_racer_id=123,
            derbynet_class_id=1,
            first_name="John",
            last_name="Doe",
            car_number=42,
            car_name="Speed Racer",
        )

        assert data.first_name == "John"
        assert data.car_number == 42
        assert data.car_name == "Speed Racer"

    def test_result_sync_data(self):
        """Test result sync data validation."""
        from modules.events.schemas import ResultSyncData

        data = ResultSyncData(
            derbynet_round_id=1,
            heat_number=1,
            derbynet_racer_id=123,
            lane=2,
            finish_time=3.4567,
            finish_place=1,
        )

        assert data.finish_time == 3.4567
        assert data.finish_place == 1

    def test_result_sync_data_null_times(self):
        """Test result sync data with null times."""
        from modules.events.schemas import ResultSyncData

        data = ResultSyncData(
            derbynet_round_id=1,
            heat_number=1,
            derbynet_racer_id=123,
            lane=1,
        )

        assert data.finish_time is None
        assert data.finish_place is None


class TestRaceSchemas:
    """Tests for race-related schemas."""

    def test_racer_brief(self):
        """Test RacerBrief schema."""
        from modules.races.schemas import RacerBrief

        racer = RacerBrief(
            id="rcr_123",
            first_name="Jane",
            last_name="Doe",
            car_number=42,
            car_name="Lightning",
            class_name="Ages 6-8",
        )

        assert racer.display_name == "Jane Doe"
        assert racer.masked_name == "Jane D."

    def test_racer_brief_no_last_name(self):
        """Test RacerBrief masked name without last name."""
        from modules.races.schemas import RacerBrief

        racer = RacerBrief(
            id="rcr_123",
            first_name="Jane",
            last_name="",
            car_number=42,
            car_name=None,
        )

        assert racer.masked_name == "Jane"

    def test_racer_in_lane(self):
        """Test RacerInLane schema."""
        from modules.races.schemas import RacerInLane, RacerBrief

        racer_in_lane = RacerInLane(
            lane=1,
            racer=RacerBrief(
                id="rcr_123",
                first_name="Jane",
                last_name="Doe",
                car_number=42,
                car_name="Lightning",
            ),
            finish_time="3.4567",
            finish_place=1,
        )

        assert racer_in_lane.lane == 1
        assert racer_in_lane.racer.first_name == "Jane"
        assert racer_in_lane.finish_time == "3.4567"
        assert racer_in_lane.finish_place == 1

    def test_heat_response(self):
        """Test HeatResponse schema."""
        from modules.races.schemas import HeatResponse

        heat = HeatResponse(
            id="ht_123",
            round_id="rnd_456",
            round_name="Preliminary",
            heat_number=1,
            status="scheduled",
            is_current=False,
            started_at=None,
            finished_at=None,
            racers=[],
        )

        assert heat.id == "ht_123"
        assert heat.status == "scheduled"
        assert len(heat.racers) == 0

    def test_current_race_response(self):
        """Test CurrentRaceResponse schema."""
        from modules.races.schemas import CurrentRaceResponse

        response = CurrentRaceResponse(
            now_racing=True,
            race_status="racing",
            poll_interval=1000,
            updated_at=datetime.now(timezone.utc),
        )

        assert response.now_racing is True
        assert response.race_status == "racing"
        assert response.poll_interval == 1000

    def test_timer_info(self):
        """Test TimerInfo schema."""
        from modules.races.schemas import TimerInfo

        timer = TimerInfo(
            lanes=3,
            state="RACE",
            message="Race in progress",
            health_status="healthy",
            timers_online=3,
            timers_ready=3,
        )

        assert timer.lanes == 3
        assert timer.state == "RACE"
        assert timer.health_status == "healthy"

    def test_racer_standing(self):
        """Test RacerStanding schema."""
        from modules.races.schemas import RacerStanding, RacerBrief

        standing = RacerStanding(
            rank=1,
            racer=RacerBrief(
                id="rcr_123",
                first_name="Jane",
                last_name="Doe",
                car_number=42,
                car_name="Lightning",
            ),
            races_completed=3,
            total_time="10.1234",
            average_time="3.3745",
            best_time="3.1234",
            total_points=None,
            wins=2,
            podiums=3,
        )

        assert standing.rank == 1
        assert standing.wins == 2
        assert standing.podiums == 3

    def test_event_stats_response(self):
        """Test EventStatsResponse schema."""
        from modules.races.schemas import EventStatsResponse

        stats = EventStatsResponse(
            event_id="evt_123",
            event_name="Summer Derby",
            total_racers=50,
            total_classes=4,
            total_rounds=8,
            total_heats=32,
            heats_completed=20,
            fastest_time="3.1234",
            fastest_racer="Jane Doe",
            average_time="3.5000",
            event_status="published",
            is_racing=True,
        )

        assert stats.total_racers == 50
        assert stats.heats_completed == 20
        assert stats.is_racing is True


class TestCommonSchemas:
    """Tests for common schemas."""

    def test_api_response(self):
        """Test APIResponse wrapper."""
        from schemas.common import APIResponse

        response = APIResponse(data={"test": "value"})
        assert response.data == {"test": "value"}
        assert response.meta is None

        response = APIResponse(data="test", meta={"extra": "info"})
        assert response.data == "test"
        assert response.meta == {"extra": "info"}

    def test_paginated_response(self):
        """Test PaginatedResponse schema."""
        from schemas.common import PaginatedResponse, PaginationMeta

        response = PaginatedResponse(
            data=[{"id": 1}, {"id": 2}],
            meta=PaginationMeta(total=10, page=1, per_page=2, total_pages=5),
        )

        assert len(response.data) == 2
        assert response.meta.total == 10
        assert response.meta.page == 1

    def test_pagination_meta_from_query(self):
        """Test PaginationMeta.from_query calculation."""
        from schemas.common import PaginationMeta

        # Exact pages
        meta = PaginationMeta.from_query(total=100, page=1, per_page=10)
        assert meta.total_pages == 10

        # Partial last page
        meta = PaginationMeta.from_query(total=95, page=1, per_page=10)
        assert meta.total_pages == 10

        # Single page
        meta = PaginationMeta.from_query(total=5, page=1, per_page=10)
        assert meta.total_pages == 1

        # Empty result
        meta = PaginationMeta.from_query(total=0, page=1, per_page=10)
        assert meta.total_pages == 0

    def test_error_response(self):
        """Test ErrorResponse schema."""
        from schemas.common import ErrorResponse, ErrorBody

        response = ErrorResponse(
            error=ErrorBody(
                code="ERR-AUTH-001",
                message="Invalid token",
            ),
            request_id="req_123",
        )

        assert response.error.code == "ERR-AUTH-001"
        assert response.error.message == "Invalid token"
        assert response.request_id == "req_123"
        assert response.timestamp is not None

    def test_error_body_with_details(self):
        """Test ErrorBody with details."""
        from schemas.common import ErrorBody, ErrorDetail

        error = ErrorBody(
            code="ERR-VAL-001",
            message="Validation failed",
            details=ErrorDetail(
                field="name",
                reason="Field is required",
            ),
        )

        assert error.details.field == "name"
        assert error.details.reason == "Field is required"

    def test_health_response(self):
        """Test HealthResponse schema."""
        from schemas.common import HealthResponse

        health = HealthResponse(
            version="1.0.0",
            environment="development",
        )

        assert health.status == "ok"
        assert health.version == "1.0.0"
        assert health.database == "connected"
        assert health.redis == "connected"


class TestErrorCodes:
    """Tests for error code constants."""

    def test_auth_error_codes(self):
        """Test authentication error codes are properly formatted."""
        from schemas.common import ErrorCodes

        assert ErrorCodes.AUTH_INVALID_TOKEN == "ERR-AUTH-001"
        assert ErrorCodes.AUTH_EXPIRED_TOKEN == "ERR-AUTH-002"
        assert ErrorCodes.AUTH_INVALID_CREDENTIALS == "ERR-AUTH-003"

    def test_authz_error_codes(self):
        """Test authorization error codes."""
        from schemas.common import ErrorCodes

        assert ErrorCodes.AUTHZ_FORBIDDEN == "ERR-AUTHZ-001"
        assert ErrorCodes.AUTHZ_NOT_ORG_MEMBER == "ERR-AUTHZ-002"
        assert ErrorCodes.AUTHZ_NOT_ORG_ADMIN == "ERR-AUTHZ-003"

    def test_validation_error_codes(self):
        """Test validation error codes."""
        from schemas.common import ErrorCodes

        assert ErrorCodes.VAL_INVALID_INPUT == "ERR-VAL-001"
        assert ErrorCodes.VAL_MISSING_FIELD == "ERR-VAL-002"

    def test_not_found_error_codes(self):
        """Test not found error codes."""
        from schemas.common import ErrorCodes

        assert ErrorCodes.NOT_FOUND == "ERR-NOT-001"
        assert ErrorCodes.NOT_FOUND_EVENT == "ERR-NOT-004"

    def test_rate_limit_error_codes(self):
        """Test rate limit error codes."""
        from schemas.common import ErrorCodes

        assert ErrorCodes.RATE_LIMIT_EXCEEDED == "ERR-RATE-001"

    def test_system_error_codes(self):
        """Test system error codes."""
        from schemas.common import ErrorCodes

        assert ErrorCodes.SYS_INTERNAL_ERROR == "ERR-SYS-001"
        assert ErrorCodes.SYS_DATABASE_ERROR == "ERR-SYS-002"


class TestSchemaSerializaton:
    """Tests for schema serialization/deserialization."""

    def test_event_response_from_attributes(self):
        """Test EventResponse can be created from ORM model."""
        from modules.events.schemas import EventResponse
        from datetime import date, datetime

        # Simulate ORM-like object
        class MockEvent:
            id = "evt_123"
            org_id = "org_456"
            name = "Test Event"
            description = "A test event"
            event_date = date.today()
            venue_name = "Test Venue"
            venue_address = "123 Test St"
            city = "Calgary"
            province = "Alberta"
            status = "draft"
            is_public = False
            lanes = 3
            use_points = False
            settings = {"allow_predictions": True}
            last_sync_at = None
            synced_by_device = None
            created_at = datetime.utcnow()
            updated_at = None

        # model_validate with from_attributes=True should work
        response = EventResponse.model_validate(MockEvent())
        assert response.id == "evt_123"
        assert response.name == "Test Event"

    def test_json_serialization(self):
        """Test schemas serialize to JSON properly."""
        from modules.races.schemas import CurrentRaceResponse

        response = CurrentRaceResponse(
            now_racing=True,
            race_status="racing",
            poll_interval=1000,
            updated_at=datetime.now(timezone.utc),
        )

        # Should serialize without error
        json_data = response.model_dump(mode="json")
        assert isinstance(json_data, dict)
        assert json_data["now_racing"] is True
        assert isinstance(json_data["updated_at"], str)  # datetime becomes string

    def test_nested_serialization(self):
        """Test nested schemas serialize correctly."""
        from modules.races.schemas import RacerStanding, RacerBrief

        standing = RacerStanding(
            rank=1,
            racer=RacerBrief(
                id="rcr_123",
                first_name="Jane",
                last_name="Doe",
                car_number=42,
                car_name="Lightning",
            ),
            races_completed=3,
            total_time="10.1234",
            average_time="3.3745",
            best_time="3.1234",
            total_points=None,
        )

        json_data = standing.model_dump(mode="json")
        assert json_data["racer"]["first_name"] == "Jane"
        assert json_data["rank"] == 1
