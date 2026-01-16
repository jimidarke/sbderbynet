"""
Device model for DerbyPi authentication and management.
"""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Enum, String, Text, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, generate_prefixed_id


class DeviceStatus(str, PyEnum):
    """Device registration status."""
    PENDING = "pending"      # Registered but not yet verified
    ACTIVE = "active"        # Verified and operational
    INACTIVE = "inactive"    # Temporarily disabled
    REVOKED = "revoked"      # Permanently disabled


class Device(Base, TimestampMixin):
    """
    DerbyPi device registered for syncing race data.
    Uses RSA-2048 key-pair authentication.
    """

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(
        String(25),
        primary_key=True,
        default=lambda: generate_prefixed_id("dev"),
    )
    org_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Device identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )  # Human-readable name like "DerbyPi-01"
    hardware_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
    )  # Optional hardware serial number

    # RSA-2048 public key for authentication
    public_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )  # PEM-encoded RSA public key

    # Status
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus),
        default=DeviceStatus.PENDING,
        nullable=False,
    )

    # Activity tracking
    last_seen_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Registration metadata
    registered_by: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )  # User ID who registered this device
    activated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Firmware info
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationship
    organization: Mapped["Organization"] = relationship(back_populates="devices")

    __table_args__ = (
        Index("ix_devices_org_status", "org_id", "status"),
        Index("ix_devices_status", "status"),
    )

    @property
    def is_active(self) -> bool:
        return self.status == DeviceStatus.ACTIVE

    @property
    def is_operational(self) -> bool:
        """Device can sync data."""
        return self.status in (DeviceStatus.ACTIVE, DeviceStatus.PENDING)


# Forward reference
from models.organization import Organization
