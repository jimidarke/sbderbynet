"""
Organization (tenant) models for multi-tenancy.
"""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Enum, String, Text, Boolean, Index, ForeignKey
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, SoftDeleteMixin, generate_prefixed_id


class OrgStatus(str, PyEnum):
    """Organization status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class OrgRole(str, PyEnum):
    """Roles within an organization."""
    OWNER = "owner"    # Can delete org, manage billing
    ADMIN = "admin"    # Can manage events, devices, members
    MEMBER = "member"  # Can view events, interact with features


class Organization(Base, TimestampMixin, SoftDeleteMixin):
    """
    Organization (tenant) - represents a derby club or event organizer.
    All tenant-scoped data is isolated via PostgreSQL RLS.
    """

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        default=lambda: generate_prefixed_id("org"),
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )  # URL-safe identifier (e.g., "calgary-derby")
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    logo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    website_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Location
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    province: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str] = mapped_column(String(50), default="Canada")

    # Status
    status: Mapped[OrgStatus] = mapped_column(
        Enum(OrgStatus),
        default=OrgStatus.ACTIVE,
        nullable=False,
    )
    suspended_at: Mapped[datetime | None] = mapped_column(nullable=True)
    suspension_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Settings (JSON for flexibility)
    settings: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    # Example settings:
    # {
    #     "timezone": "America/Edmonton",
    #     "public_profile": true,
    #     "allow_donations": true,
    #     "default_poll_duration": 3600
    # }

    # Relationships
    members: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    devices: Mapped[list["Device"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_organizations_status", "status"),
    )

    @property
    def is_active(self) -> bool:
        return self.status == OrgStatus.ACTIVE and not self.is_deleted


class OrganizationMember(Base, TimestampMixin):
    """
    Membership linking users to organizations with roles.
    """

    __tablename__ = "organization_members"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    org_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[OrgRole] = mapped_column(
        Enum(OrgRole),
        default=OrgRole.MEMBER,
        nullable=False,
    )

    # Invitation tracking
    invited_by: Mapped[str | None] = mapped_column(String(20), nullable=True)
    invited_at: Mapped[datetime | None] = mapped_column(nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="organization_memberships")

    __table_args__ = (
        Index("ix_org_members_org_user", "org_id", "user_id", unique=True),
        Index("ix_org_members_user", "user_id"),
    )

    @property
    def is_admin(self) -> bool:
        return self.role in (OrgRole.OWNER, OrgRole.ADMIN)

    @property
    def is_owner(self) -> bool:
        return self.role == OrgRole.OWNER


# Forward references
from models.user import User
from models.event import Event
from models.device import Device
