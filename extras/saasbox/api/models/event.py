"""
Event model - represents a derby race day.
"""
from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import Enum, String, Text, Date, Index, ForeignKey, Boolean
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, SoftDeleteMixin, generate_prefixed_id


class EventStatus(str, PyEnum):
    """Event lifecycle status."""
    DRAFT = "draft"          # Not yet published
    PUBLISHED = "published"  # Visible to public
    ACTIVE = "active"        # Race day in progress
    COMPLETED = "completed"  # Race finished
    CANCELLED = "cancelled"  # Event cancelled


class Event(Base, TimestampMixin, SoftDeleteMixin):
    """
    A derby racing event (race day).
    Contains racers, classes, rounds, heats, and results.
    """

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: generate_prefixed_id("evt"),
    )
    org_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Event details
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    event_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    # Location
    venue_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    venue_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    province: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Status
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus),
        default=EventStatus.DRAFT,
        nullable=False,
    )
    is_public: Mapped[bool] = mapped_column(default=False)

    # Sync tracking
    derbynet_db_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )  # SHA-256 hash of synced DerbyNet database
    last_sync_at: Mapped[datetime | None] = mapped_column(nullable=True)
    synced_by_device: Mapped[str | None] = mapped_column(
        String(25),
        nullable=True,
    )

    # Race configuration
    lanes: Mapped[int] = mapped_column(default=3)
    use_points: Mapped[bool] = mapped_column(default=False)

    # Settings
    settings: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    # Example settings:
    # {
    #     "allow_predictions": true,
    #     "allow_cheers": true,
    #     "prediction_cutoff_minutes": 5,
    #     "max_cheers_per_racer": 5
    # }

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="events")
    racer_classes: Mapped[list["RacerClass"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    racers: Mapped[list["Racer"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    rounds: Mapped[list["Round"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    polls: Mapped[list["Poll"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_events_org_date", "org_id", "event_date"),
        Index("ix_events_status", "status"),
        # RLS policy will be created via migration
    )

    @property
    def is_active(self) -> bool:
        return self.status == EventStatus.ACTIVE

    @property
    def is_viewable(self) -> bool:
        """Event can be viewed by the public."""
        return self.is_public and self.status in (
            EventStatus.PUBLISHED,
            EventStatus.ACTIVE,
            EventStatus.COMPLETED,
        )


# Forward references
from models.organization import Organization
from models.racer import RacerClass, Racer
from models.race import Round
from models.engagement import Poll
