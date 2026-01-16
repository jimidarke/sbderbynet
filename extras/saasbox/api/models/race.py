"""
Race models - Rounds, Heats, and Results.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Enum, String, Integer, Numeric, Index, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, generate_prefixed_id


class RoundStatus(str, PyEnum):
    """Round progress status."""
    PENDING = "pending"      # Not yet started
    ACTIVE = "active"        # Currently racing
    COMPLETED = "completed"  # All heats finished


class HeatStatus(str, PyEnum):
    """Heat progress status."""
    SCHEDULED = "scheduled"  # Waiting to race
    STAGING = "staging"      # Cars being staged
    RACING = "racing"        # Race in progress
    FINISHED = "finished"    # Results recorded


class Round(Base, TimestampMixin):
    """
    A racing round within an event (e.g., "Preliminary", "Semi-Final", "Final").
    """

    __tablename__ = "rounds"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: generate_prefixed_id("rnd"),
    )
    event_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_id: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("racer_classes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Round info
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )  # e.g., "1 Preliminary", "2 Semi-Final", "3 Final"
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    status: Mapped[RoundStatus] = mapped_column(
        Enum(RoundStatus),
        default=RoundStatus.PENDING,
        nullable=False,
    )

    # Heat counts
    heats_scheduled: Mapped[int] = mapped_column(default=0)
    heats_completed: Mapped[int] = mapped_column(default=0)

    # Roster
    roster_size: Mapped[int] = mapped_column(default=0)

    # Synced from DerbyNet
    derbynet_round_id: Mapped[int | None] = mapped_column(nullable=True)

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="rounds")
    racer_class: Mapped["RacerClass | None"] = relationship(back_populates="rounds")
    heats: Mapped[list["Heat"]] = relationship(
        back_populates="round",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_rounds_event_number", "event_id", "round_number"),
        Index("ix_rounds_class", "class_id"),
    )

    @property
    def is_complete(self) -> bool:
        return self.status == RoundStatus.COMPLETED


class Heat(Base, TimestampMixin):
    """
    A single race heat within a round.
    """

    __tablename__ = "heats"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: generate_prefixed_id("ht"),
    )
    round_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    heat_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    status: Mapped[HeatStatus] = mapped_column(
        Enum(HeatStatus),
        default=HeatStatus.SCHEDULED,
        nullable=False,
    )

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Is this the current heat being raced?
    is_current: Mapped[bool] = mapped_column(default=False)

    # Synced from DerbyNet
    derbynet_heat_number: Mapped[int | None] = mapped_column(nullable=True)

    # Relationships
    round: Mapped["Round"] = relationship(back_populates="heats")
    results: Mapped[list["RaceResult"]] = relationship(
        back_populates="heat",
        cascade="all, delete-orphan",
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="heat",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_heats_round_number", "round_id", "heat_number"),
        Index("ix_heats_current", "is_current", postgresql_where="is_current = true"),
    )

    @property
    def is_finished(self) -> bool:
        return self.status == HeatStatus.FINISHED


class RaceResult(Base, TimestampMixin):
    """
    Result for a single racer in a heat.
    """

    __tablename__ = "race_results"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: generate_prefixed_id("res"),
    )
    heat_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("heats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    racer_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("racers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Lane assignment
    lane: Mapped[int] = mapped_column(Integer, nullable=False)

    # Results
    finish_time: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=4),
        nullable=True,
    )  # e.g., 3.4567 seconds
    finish_place: Mapped[int | None] = mapped_column(nullable=True)  # 1, 2, 3...
    points: Mapped[int | None] = mapped_column(nullable=True)  # For points-based scoring

    # Result recorded timestamp
    recorded_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Synced from DerbyNet
    derbynet_result_id: Mapped[int | None] = mapped_column(nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    heat: Mapped["Heat"] = relationship(back_populates="results")
    racer: Mapped["Racer"] = relationship(back_populates="race_results")

    __table_args__ = (
        Index("ix_results_heat_lane", "heat_id", "lane"),
        Index("ix_results_racer", "racer_id"),
    )

    @property
    def has_time(self) -> bool:
        return self.finish_time is not None

    @property
    def time_display(self) -> str:
        """Format finish time for display."""
        if self.finish_time is None:
            return "-"
        return f"{self.finish_time:.4f}"


# Forward references
from models.event import Event
from models.racer import RacerClass, Racer
from models.engagement import Prediction
