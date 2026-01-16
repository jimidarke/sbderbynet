"""
User and consent models.
"""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Enum, String, Text, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, generate_prefixed_id


class SystemRole(str, PyEnum):
    """System-wide user roles."""
    ADMIN = "admin"  # System administrator (3-4 people, invite only)
    USER = "user"    # Regular user (spectators, parents)


class User(Base, TimestampMixin):
    """
    User account linked to Firebase Authentication.
    Stores minimal PII per PIPEDA requirements.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: generate_prefixed_id("usr"),
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    display_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    system_role: Mapped[SystemRole] = mapped_column(
        Enum(SystemRole),
        default=SystemRole.USER,
        nullable=False,
    )

    # PIPEDA consent tracking
    consented_at: Mapped[datetime | None] = mapped_column(nullable=True)
    privacy_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Activity tracking
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    banned_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ban_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    consents: Mapped[list["UserConsent"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    organization_memberships: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    favorites: Mapped[list["UserFavorite"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    push_tokens: Mapped[list["PushToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notification_preferences: Mapped["NotificationPreference | None"] = relationship(
        back_populates="user",
        uselist=False,  # One-to-one relationship
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_users_email_lower", "email"),
        Index("ix_users_system_role", "system_role"),
    )

    @property
    def is_system_admin(self) -> bool:
        return self.system_role == SystemRole.ADMIN


class UserConsent(Base, TimestampMixin):
    """
    Tracks user consent for PIPEDA compliance.
    Records when users consented to privacy policy, terms, etc.
    """

    __tablename__ = "user_consents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consent_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # 'privacy_policy', 'terms_of_service', 'child_data'
    policy_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    consented_at: Mapped[datetime] = mapped_column(nullable=False)
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Relationship
    user: Mapped["User"] = relationship(back_populates="consents")

    __table_args__ = (
        Index("ix_user_consents_user_type", "user_id", "consent_type"),
    )


# Forward references for relationships
from models.organization import OrganizationMember
from models.engagement import UserFavorite, Prediction
from models.notification import PushToken, NotificationPreference
