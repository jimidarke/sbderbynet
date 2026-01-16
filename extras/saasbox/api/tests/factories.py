"""
Test data factories for generating realistic test data.

Uses the Factory pattern to create model instances with sensible defaults
that can be overridden as needed.
"""
import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from models.user import User, UserConsent, SystemRole
from models.organization import Organization, OrganizationMember, OrgRole, OrgStatus
from models.device import Device, DeviceStatus
from models.event import Event, EventStatus
from models.racer import Racer, RacerClass, RacerStatus
from models.race import Round, Heat, RaceResult, RoundStatus, HeatStatus
from models.engagement import UserFavorite, Prediction, Cheer, Poll, PollVote, PollStatus


def generate_id(prefix: str, length: int = 12) -> str:
    """Generate a prefixed ID."""
    return f"{prefix}_{secrets.token_hex(length // 2)}"


class BaseFactory:
    """Base factory with common methods."""

    model = None
    _counter = 0

    @classmethod
    def _get_counter(cls) -> int:
        cls._counter += 1
        return cls._counter

    @classmethod
    def create(cls, **kwargs) -> Any:
        """Create a model instance with given overrides."""
        raise NotImplementedError


class UserFactory(BaseFactory):
    """Factory for creating User instances."""

    model = User

    @classmethod
    def create(
        cls,
        id: str | None = None,
        firebase_uid: str | None = None,
        email: str | None = None,
        display_name: str | None = None,
        system_role: SystemRole = SystemRole.USER,
        is_active: bool = True,
        **kwargs,
    ) -> User:
        counter = cls._get_counter()
        return User(
            id=id or generate_id("usr"),
            firebase_uid=firebase_uid or f"firebase_uid_{counter}",
            email=email or f"testuser{counter}@example.com",
            display_name=display_name or f"Test User {counter}",
            system_role=system_role,
            is_active=is_active,
            consented_at=datetime.utcnow(),
            privacy_version="1.0",
            **kwargs,
        )


class OrganizationFactory(BaseFactory):
    """Factory for creating Organization instances."""

    model = Organization

    @classmethod
    def create(
        cls,
        id: str | None = None,
        name: str | None = None,
        slug: str | None = None,
        status: OrgStatus = OrgStatus.ACTIVE,
        city: str = "Calgary",
        province: str = "Alberta",
        **kwargs,
    ) -> Organization:
        counter = cls._get_counter()
        return Organization(
            id=id or generate_id("org"),
            name=name or f"Test Derby Club {counter}",
            slug=slug or f"test-derby-{counter}",
            status=status,
            city=city,
            province=province,
            country="Canada",
            settings={
                "timezone": "America/Edmonton",
                "public_profile": True,
                "allow_donations": True,
            },
            **kwargs,
        )


class OrganizationMemberFactory(BaseFactory):
    """Factory for creating OrganizationMember instances."""

    model = OrganizationMember

    @classmethod
    def create(
        cls,
        org_id: str,
        user_id: str,
        role: OrgRole = OrgRole.MEMBER,
        is_active: bool = True,
        **kwargs,
    ) -> OrganizationMember:
        return OrganizationMember(
            org_id=org_id,
            user_id=user_id,
            role=role,
            is_active=is_active,
            joined_at=datetime.utcnow(),
            **kwargs,
        )


class DeviceFactory(BaseFactory):
    """Factory for creating Device instances."""

    model = Device

    # Sample RSA public key for testing
    SAMPLE_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0Z3VS5JJcds3xfn/ygWyf8TFzUb0
T7QHZLMDB0OUGV8FG2FUhWN7Q5b0gXnJaVG3nJVBaA0BuL/lJKNGsMdwPgYQlNWk+jD8HY0H
QjjgMK0G8P5DQLG0Wv2rN7VbW2rKlS7C2OxYPVHT3V4QjPpG7L3V9X7Y8DxlAy4eZGXbJEt
a0BwJ5rBxLwL9VbMNVyJUf0xbWE/5L1wB7ZhE8dN6vCPFpRgWS8yZwC3BbcDx9K9WPJKnQ+5
LNGpOZsb4gXVbdLPZLEaXCNx/9X8Y3qH5fGLB4N3BhHfbADmPDQCP5V4XjfL4B6xZbCxYPCz
5WJQb7Z1MfXkE3DLhwIDAQAB
-----END PUBLIC KEY-----"""

    @classmethod
    def create(
        cls,
        id: str | None = None,
        org_id: str | None = None,
        name: str | None = None,
        public_key: str | None = None,
        status: DeviceStatus = DeviceStatus.ACTIVE,
        **kwargs,
    ) -> Device:
        counter = cls._get_counter()
        return Device(
            id=id or generate_id("dev"),
            org_id=org_id or generate_id("org"),
            name=name or f"DerbyPi-{counter:02d}",
            public_key=public_key or cls.SAMPLE_PUBLIC_KEY,
            status=status,
            last_seen_at=datetime.utcnow(),
            **kwargs,
        )


class EventFactory(BaseFactory):
    """Factory for creating Event instances."""

    model = Event

    DEFAULT_SETTINGS = {
        "allow_predictions": True,
        "allow_cheers": True,
        "prediction_cutoff_minutes": 5,
        "max_cheers_per_racer": 5,
    }

    @classmethod
    def create(
        cls,
        id: str | None = None,
        org_id: str | None = None,
        name: str | None = None,
        event_date: date | None = None,
        status: EventStatus = EventStatus.DRAFT,
        is_public: bool = False,
        lanes: int = 3,
        settings: dict | None = None,
        **kwargs,
    ) -> Event:
        counter = cls._get_counter()
        # Merge provided settings with defaults
        final_settings = {**cls.DEFAULT_SETTINGS, **(settings or {})}
        return Event(
            id=id or generate_id("evt"),
            org_id=org_id or generate_id("org"),
            name=name or f"Summer Derby {2024 + counter}",
            event_date=event_date or date.today() + timedelta(days=30),
            status=status,
            is_public=is_public,
            lanes=lanes,
            venue_name="Test Track",
            city="Calgary",
            province="Alberta",
            settings=final_settings,
            **kwargs,
        )


class RacerClassFactory(BaseFactory):
    """Factory for creating RacerClass instances."""

    model = RacerClass

    SAMPLE_CLASSES = [
        ("Ages 6-8", 6, 8),
        ("Ages 9-11", 9, 11),
        ("Ages 12-14", 12, 14),
        ("Stock Division", None, None),
        ("Super Stock", None, None),
    ]

    @classmethod
    def create(
        cls,
        id: str | None = None,
        event_id: str | None = None,
        name: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        **kwargs,
    ) -> RacerClass:
        counter = cls._get_counter()
        sample = cls.SAMPLE_CLASSES[counter % len(cls.SAMPLE_CLASSES)]

        return RacerClass(
            id=id or generate_id("cls"),
            event_id=event_id or generate_id("evt"),
            name=name or sample[0],
            min_age=min_age if min_age is not None else sample[1],
            max_age=max_age if max_age is not None else sample[2],
            sort_order=counter,
            **kwargs,
        )


class RacerFactory(BaseFactory):
    """Factory for creating Racer instances."""

    model = Racer

    FIRST_NAMES = [
        "Emma", "Liam", "Olivia", "Noah", "Ava", "Oliver",
        "Sophia", "Elijah", "Isabella", "Lucas", "Mia", "Mason",
    ]
    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
        "Miller", "Davis", "Rodriguez", "Martinez", "Wilson", "Anderson",
    ]

    @classmethod
    def create(
        cls,
        id: str | None = None,
        event_id: str | None = None,
        class_id: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        car_number: int | None = None,
        car_name: str | None = None,
        status: RacerStatus = RacerStatus.PASSED,
        **kwargs,
    ) -> Racer:
        counter = cls._get_counter()
        return Racer(
            id=id or generate_id("rcr"),
            event_id=event_id or generate_id("evt"),
            class_id=class_id,
            first_name=first_name or cls.FIRST_NAMES[counter % len(cls.FIRST_NAMES)],
            last_name=last_name or cls.LAST_NAMES[counter % len(cls.LAST_NAMES)],
            car_number=car_number or counter,
            car_name=car_name or f"Speed Demon {counter}",
            status=status,
            date_of_birth=date.today() - timedelta(days=365 * 10),  # 10 years old
            **kwargs,
        )


class RoundFactory(BaseFactory):
    """Factory for creating Round instances."""

    model = Round

    ROUND_NAMES = [
        "1 Preliminary",
        "2 Semi-Final",
        "3 Final",
        "4 Championship",
    ]

    @classmethod
    def create(
        cls,
        id: str | None = None,
        event_id: str | None = None,
        class_id: str | None = None,
        name: str | None = None,
        round_number: int | None = None,
        status: RoundStatus = RoundStatus.PENDING,
        **kwargs,
    ) -> Round:
        counter = cls._get_counter()
        return Round(
            id=id or generate_id("rnd"),
            event_id=event_id or generate_id("evt"),
            class_id=class_id,
            name=name or cls.ROUND_NAMES[counter % len(cls.ROUND_NAMES)],
            round_number=round_number or (counter % 4) + 1,
            status=status,
            heats_scheduled=0,
            heats_completed=0,
            **kwargs,
        )


class HeatFactory(BaseFactory):
    """Factory for creating Heat instances."""

    model = Heat

    @classmethod
    def create(
        cls,
        id: str | None = None,
        round_id: str | None = None,
        heat_number: int | None = None,
        status: HeatStatus = HeatStatus.SCHEDULED,
        is_current: bool = False,
        **kwargs,
    ) -> Heat:
        counter = cls._get_counter()
        return Heat(
            id=id or generate_id("ht"),
            round_id=round_id or generate_id("rnd"),
            heat_number=heat_number or counter,
            status=status,
            is_current=is_current,
            **kwargs,
        )


class RaceResultFactory(BaseFactory):
    """Factory for creating RaceResult instances."""

    model = RaceResult

    @classmethod
    def create(
        cls,
        id: str | None = None,
        heat_id: str | None = None,
        racer_id: str | None = None,
        lane: int = 1,
        finish_time: Decimal | None = None,
        finish_place: int | None = None,
        **kwargs,
    ) -> RaceResult:
        counter = cls._get_counter()
        return RaceResult(
            id=id or generate_id("res"),
            heat_id=heat_id or generate_id("ht"),
            racer_id=racer_id or generate_id("rcr"),
            lane=lane,
            finish_time=finish_time,
            finish_place=finish_place,
            recorded_at=datetime.utcnow() if finish_time else None,
            **kwargs,
        )


# =============================================================================
# Bulk Data Generation
# =============================================================================

def create_full_event_data(
    org_id: str,
    num_classes: int = 3,
    racers_per_class: int = 12,
    heats_per_round: int = 4,
) -> dict[str, Any]:
    """
    Create a complete event with all related data.

    Returns a dictionary with all created instances.
    """
    event = EventFactory.create(org_id=org_id)

    classes = []
    racers = []
    rounds = []
    heats = []
    results = []

    for c in range(num_classes):
        racer_class = RacerClassFactory.create(event_id=event.id)
        classes.append(racer_class)

        # Create racers for this class
        class_racers = [
            RacerFactory.create(
                event_id=event.id,
                class_id=racer_class.id,
                car_number=(c * racers_per_class) + r + 1,
            )
            for r in range(racers_per_class)
        ]
        racers.extend(class_racers)

        # Create round for this class
        round_obj = RoundFactory.create(
            event_id=event.id,
            class_id=racer_class.id,
            round_number=1,
        )
        rounds.append(round_obj)

        # Create heats for this round
        for h in range(heats_per_round):
            heat = HeatFactory.create(
                round_id=round_obj.id,
                heat_number=h + 1,
            )
            heats.append(heat)

            # Create results for racers in this heat (3 per heat)
            heat_racers = class_racers[h * 3:(h + 1) * 3]
            for lane, racer in enumerate(heat_racers, 1):
                result = RaceResultFactory.create(
                    heat_id=heat.id,
                    racer_id=racer.id,
                    lane=lane,
                    finish_time=Decimal(f"3.{100 + lane * 50:03d}"),
                    finish_place=lane,
                )
                results.append(result)

    return {
        "event": event,
        "classes": classes,
        "racers": racers,
        "rounds": rounds,
        "heats": heats,
        "results": results,
    }


class UserFavoriteFactory(BaseFactory):
    """Factory for creating UserFavorite instances."""

    model = UserFavorite

    @classmethod
    def create(
        cls,
        user_id: str,
        racer_id: str,
        notify_upcoming: bool = True,
        notify_results: bool = True,
        **kwargs,
    ) -> UserFavorite:
        return UserFavorite(
            user_id=user_id,
            racer_id=racer_id,
            notify_upcoming=notify_upcoming,
            notify_results=notify_results,
            **kwargs,
        )


class PredictionFactory(BaseFactory):
    """Factory for creating Prediction instances."""

    model = Prediction

    @classmethod
    def create(
        cls,
        id: str | None = None,
        user_id: str | None = None,
        heat_id: str | None = None,
        predicted_racer_id: str | None = None,
        is_correct: bool | None = None,
        points_earned: int = 0,
        **kwargs,
    ) -> Prediction:
        return Prediction(
            id=id or generate_id("prd"),
            user_id=user_id or generate_id("usr"),
            heat_id=heat_id or generate_id("ht"),
            predicted_racer_id=predicted_racer_id or generate_id("rcr"),
            is_correct=is_correct,
            points_earned=points_earned,
            **kwargs,
        )


class CheerFactory(BaseFactory):
    """Factory for creating Cheer instances."""

    model = Cheer

    @classmethod
    def create(
        cls,
        user_id: str | None = None,
        racer_id: str | None = None,
        **kwargs,
    ) -> Cheer:
        return Cheer(
            user_id=user_id or generate_id("usr"),
            racer_id=racer_id or generate_id("rcr"),
            **kwargs,
        )


class PollFactory(BaseFactory):
    """Factory for creating Poll instances."""

    model = Poll

    SAMPLE_QUESTIONS = [
        "Who has the Best Looking Car?",
        "Fan Favorite Racer?",
        "Most Creative Design?",
        "Best Team Spirit?",
    ]

    @classmethod
    def create(
        cls,
        id: str | None = None,
        event_id: str | None = None,
        question: str | None = None,
        description: str | None = None,
        options: list | None = None,
        status: "PollStatus" = None,
        opens_at: datetime | None = None,
        closes_at: datetime | None = None,
        created_by: str | None = None,
        **kwargs,
    ) -> "Poll":
        from models.engagement import PollStatus as PS
        counter = cls._get_counter()

        # Default options if not provided
        if options is None:
            options = [
                {"id": "opt_1", "label": "Option A"},
                {"id": "opt_2", "label": "Option B"},
                {"id": "opt_3", "label": "Option C"},
            ]

        return Poll(
            id=id or generate_id("pol"),
            event_id=event_id or generate_id("evt"),
            question=question or cls.SAMPLE_QUESTIONS[counter % len(cls.SAMPLE_QUESTIONS)],
            description=description,
            options=options,
            status=status or PS.ACTIVE,
            opens_at=opens_at,
            closes_at=closes_at,
            created_by=created_by,
            **kwargs,
        )


class PollVoteFactory(BaseFactory):
    """Factory for creating PollVote instances."""

    model = PollVote

    @classmethod
    def create(
        cls,
        poll_id: str | None = None,
        user_id: str | None = None,
        option_id: str | None = None,
        **kwargs,
    ) -> "PollVote":
        return PollVote(
            poll_id=poll_id or generate_id("pol"),
            user_id=user_id or generate_id("usr"),
            option_id=option_id or "opt_1",
            **kwargs,
        )
