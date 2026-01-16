"""
Common Pydantic schemas used across the API.
"""
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


DataT = TypeVar("DataT")


class APIResponse(BaseModel, Generic[DataT]):
    """Standard API response wrapper."""

    data: DataT
    meta: dict[str, Any] | None = None


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Paginated API response."""

    data: list[DataT]
    meta: "PaginationMeta"


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    total: int
    page: int
    per_page: int
    total_pages: int

    @classmethod
    def from_query(cls, total: int, page: int, per_page: int) -> "PaginationMeta":
        return cls(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
        )


class ErrorDetail(BaseModel):
    """Error detail for specific field."""

    field: str | None = None
    reason: str


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: "ErrorBody"
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorBody(BaseModel):
    """Error body with code and message."""

    code: str
    message: str
    details: ErrorDetail | None = None


# Error code constants
class ErrorCodes:
    """Standardized error codes."""

    # Authentication errors (ERR-AUTH-*)
    AUTH_INVALID_TOKEN = "ERR-AUTH-001"
    AUTH_EXPIRED_TOKEN = "ERR-AUTH-002"
    AUTH_INVALID_CREDENTIALS = "ERR-AUTH-003"
    AUTH_DEVICE_NOT_REGISTERED = "ERR-AUTH-004"
    AUTH_INVALID_SIGNATURE = "ERR-AUTH-005"
    AUTH_NONCE_REUSED = "ERR-AUTH-006"
    AUTH_TIMESTAMP_EXPIRED = "ERR-AUTH-007"
    AUTH_MISSING_TOKEN = "ERR-AUTH-008"

    # Authorization errors (ERR-AUTHZ-*)
    AUTHZ_FORBIDDEN = "ERR-AUTHZ-001"
    AUTHZ_NOT_ORG_MEMBER = "ERR-AUTHZ-002"
    AUTHZ_NOT_ORG_ADMIN = "ERR-AUTHZ-003"
    AUTHZ_NOT_SYSTEM_ADMIN = "ERR-AUTHZ-004"

    # Validation errors (ERR-VAL-*)
    VAL_INVALID_INPUT = "ERR-VAL-001"
    VAL_MISSING_FIELD = "ERR-VAL-002"
    VAL_INVALID_FORMAT = "ERR-VAL-003"
    VAL_DUPLICATE_ENTRY = "ERR-VAL-004"

    # Not found errors (ERR-NOT-*)
    NOT_FOUND = "ERR-NOT-001"
    NOT_FOUND_USER = "ERR-NOT-002"
    NOT_FOUND_ORG = "ERR-NOT-003"
    NOT_FOUND_EVENT = "ERR-NOT-004"
    NOT_FOUND_RACER = "ERR-NOT-005"
    NOT_FOUND_DEVICE = "ERR-NOT-006"

    # Rate limiting (ERR-RATE-*)
    RATE_LIMIT_EXCEEDED = "ERR-RATE-001"

    # System errors (ERR-SYS-*)
    SYS_INTERNAL_ERROR = "ERR-SYS-001"
    SYS_DATABASE_ERROR = "ERR-SYS-002"
    SYS_EXTERNAL_SERVICE = "ERR-SYS-003"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str
    environment: str
    database: str = "connected"
    redis: str = "connected"


class TimestampMixin(BaseModel):
    """Mixin for created/updated timestamps."""

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    updated_at: datetime | None = None
