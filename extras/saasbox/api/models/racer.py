"""
Racer and class models.
"""
from datetime import date
from enum import Enum as PyEnum

from sqlalchemy import Enum, String, Date, Integer, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, generate_prefixed_id


class RacerStatus(str, PyEnum):
    """Racer registration status."""
    REGISTERED = "registered"    # Registered but not checked in
    CHECKED_IN = "checked_in"    # Checked in at event
    PASSED = "passed"            # Passed inspection
    RACING = "racing"            # Currently racing
    FINISHED = "finished"        # Done racing
    DISQUALIFIED = "disqualified"


class RacerClass(Base, TimestampMixin):
    """
    Racing class (age group/division).
    Examples: "Ages 6-8", "Stock Division", "Super Stock"
    """

    __tablename__ = "racer_classes"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: generate_prefixed_id("cls"),
    )
    event_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Age range (optional)
    min_age: Mapped[int | None] = mapped_column(nullable=True)
    max_age: Mapped[int | None] = mapped_column(nullable=True)

    # Display order
    sort_order: Mapped[int] = mapped_column(default=0)

    # Synced from DerbyNet
    derbynet_class_id: Mapped[int | None] = mapped_column(nullable=True)

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="racer_classes")
    racers: Mapped[list["Racer"]] = relationship(
        back_populates="racer_class",
        cascade="all, delete-orphan",
    )
    rounds: Mapped[list["Round"]] = relationship(
        back_populates="racer_class",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_racer_classes_event", "event_id"),
    )


class Racer(Base, TimestampMixin):
    """
    A racer participant.
    PIPEDA compliant - only stores first name, last name, DOB.
    """

    __tablename__ = "racers"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: generate_prefixed_id("rcr"),
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

    # PIPEDA minimal data
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Car info
    car_number: Mapped[int] = mapped_column(Integer, nullable=False)
    car_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status
    status: Mapped[RacerStatus] = mapped_column(
        Enum(RacerStatus),
        default=RacerStatus.REGISTERED,
        nullable=False,
    )

    # Synced from DerbyNet
    derbynet_racer_id: Mapped[int | None] = mapped_column(nullable=True)

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="racers")
    racer_class: Mapped["RacerClass | None"] = relationship(back_populates="racers")
    race_results: Mapped[list["RaceResult"]] = relationship(
        back_populates="racer",
        cascade="all, delete-orphan",
    )
    favorites: Mapped[list["UserFavorite"]] = relationship(
        back_populates="racer",
        cascade="all, delete-orphan",
    )
    cheers: Mapped[list["Cheer"]] = relationship(
        back_populates="racer",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_racers_event_car", "event_id", "car_number"),
        Index("ix_racers_class", "class_id"),
    )

    @property
    def display_name(self) -> str:
        """Full name for display."""
        return f"{self.first_name} {self.last_name}"

    @property
    def masked_name(self) -> str:
        """Masked name for public display (privacy)."""
        if self.last_name:
            return f"{self.first_name} {self.last_name[0]}."
        return self.first_name

    @property
    def age(self) -> int | None:
        """Calculate age from date of birth."""
        if not self.date_of_birth:
            return None
        from datetime import date as date_type
        today = date_type.today()
        age = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return age


# Forward references
from models.event import Event
from models.race import Round, RaceResult
from models.engagement import UserFavorite, Cheer
