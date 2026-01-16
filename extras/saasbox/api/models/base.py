"""
Base model and mixins for SQLAlchemy models.
"""
import secrets
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def generate_prefixed_id(prefix: str, length: int = 12) -> str:
    """
    Generate a prefixed unique ID.

    Examples:
        generate_prefixed_id("usr") -> "usr_a1b2c3d4e5f6"
        generate_prefixed_id("org") -> "org_x7y8z9a0b1c2"
    """
    random_part = secrets.token_hex(length // 2)
    return f"{prefix}_{random_part}"


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )


class SoftDeleteMixin:
    """Mixin that adds soft delete support."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
