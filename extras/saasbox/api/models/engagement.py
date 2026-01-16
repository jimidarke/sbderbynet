"""
Engagement models - Favorites, Predictions, Cheers, Polls.
"""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Enum, String, Text, Integer, Index, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any

from models.base import Base, TimestampMixin, generate_prefixed_id


class UserFavorite(Base, TimestampMixin):
    """
    User's favorite racers for push notifications.
    """

    __tablename__ = "user_favorites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    racer_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("racers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Notification preferences for this favorite
    notify_upcoming: Mapped[bool] = mapped_column(default=True)
    notify_results: Mapped[bool] = mapped_column(default=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="favorites")
    racer: Mapped["Racer"] = relationship(back_populates="favorites")

    __table_args__ = (
        Index("ix_favorites_user_racer", "user_id", "racer_id", unique=True),
    )


class Prediction(Base, TimestampMixin):
    """
    User prediction for heat winner.
    """

    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: generate_prefixed_id("prd"),
    )
    user_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    heat_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("heats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    predicted_racer_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("racers.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Was the prediction correct?
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)  # null = not yet resolved
    points_earned: Mapped[int] = mapped_column(default=0)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="predictions")
    heat: Mapped["Heat"] = relationship(back_populates="predictions")
    predicted_racer: Mapped["Racer"] = relationship()

    __table_args__ = (
        Index("ix_predictions_user_heat", "user_id", "heat_id", unique=True),
        Index("ix_predictions_heat", "heat_id"),
    )


class Cheer(Base, TimestampMixin):
    """
    User cheer/reaction for a racer.
    Rate-limited: 5 cheers per racer per user per event.
    """

    __tablename__ = "cheers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    racer_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("racers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship()
    racer: Mapped["Racer"] = relationship(back_populates="cheers")

    __table_args__ = (
        Index("ix_cheers_racer", "racer_id"),
        Index("ix_cheers_user_racer", "user_id", "racer_id"),
    )


class PollStatus(str, PyEnum):
    """Poll lifecycle status."""
    DRAFT = "draft"      # Not yet open
    ACTIVE = "active"    # Accepting votes
    CLOSED = "closed"    # Voting ended


class Poll(Base, TimestampMixin):
    """
    Audience poll for events.
    Examples: "Best Looking Car", "Fan Favorite"
    """

    __tablename__ = "polls"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: generate_prefixed_id("pol"),
    )
    event_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Poll content
    question: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Options (stored as JSON for flexibility)
    # Format: [{"id": "opt_1", "label": "Car #5", "racer_id": "rcr_xxx"}, ...]
    options: Mapped[list[Any]] = mapped_column(JSON, default=list)

    # Status
    status: Mapped[PollStatus] = mapped_column(
        Enum(PollStatus),
        default=PollStatus.DRAFT,
        nullable=False,
    )
    opens_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closes_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Created by
    created_by: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="polls")
    votes: Mapped[list["PollVote"]] = relationship(
        back_populates="poll",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_polls_event_status", "event_id", "status"),
    )

    @property
    def is_active(self) -> bool:
        if self.status != PollStatus.ACTIVE:
            return False
        now = datetime.utcnow()
        if self.opens_at and now < self.opens_at:
            return False
        if self.closes_at and now > self.closes_at:
            return False
        return True


class PollVote(Base, TimestampMixin):
    """
    User vote in a poll.
    One vote per user per poll.
    """

    __tablename__ = "poll_votes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    poll_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("polls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Selected option ID (matches options[].id in Poll)
    option_id: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationships
    poll: Mapped["Poll"] = relationship(back_populates="votes")
    user: Mapped["User"] = relationship()

    __table_args__ = (
        Index("ix_poll_votes_poll_user", "poll_id", "user_id", unique=True),
    )


# Forward references
from models.user import User
from models.racer import Racer
from models.race import Heat
from models.event import Event
