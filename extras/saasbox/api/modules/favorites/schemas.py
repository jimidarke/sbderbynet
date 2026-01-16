"""
Pydantic schemas for favorites module.
"""
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class RacerInfo(BaseModel):
    """Racer information included with favorites."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    first_name: str
    last_name: str
    car_number: int
    car_name: str | None = None
    class_name: str | None = None
    event_id: str
    event_name: str | None = None

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def masked_name(self) -> str:
        """Privacy-safe name for public display."""
        if self.last_name:
            return f"{self.first_name} {self.last_name[0]}."
        return self.first_name


class FavoriteCreate(BaseModel):
    """Request schema for adding a favorite racer."""
    racer_id: str = Field(..., description="ID of the racer to favorite")
    notify_upcoming: bool = Field(
        default=True,
        description="Notify when racer is about to race",
    )
    notify_results: bool = Field(
        default=True,
        description="Notify when racer finishes a race",
    )


class FavoriteUpdate(BaseModel):
    """Request schema for updating favorite notification settings."""
    notify_upcoming: bool | None = None
    notify_results: bool | None = None


class FavoriteResponse(BaseModel):
    """Response schema for a favorite."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    racer_id: str
    racer: RacerInfo
    notify_upcoming: bool
    notify_results: bool
    created_at: datetime


class FavoriteListResponse(BaseModel):
    """Response schema for favorite list item."""
    id: int
    racer_id: str
    racer: RacerInfo
    notify_upcoming: bool
    notify_results: bool
    created_at: datetime


class NotificationSettings(BaseModel):
    """User notification settings."""
    push_enabled: bool = True
    favorite_upcoming_enabled: bool = True
    favorite_results_enabled: bool = True
    event_announcements_enabled: bool = True


class NotificationSettingsUpdate(BaseModel):
    """Request schema for updating notification settings."""
    push_enabled: bool | None = None
    favorite_upcoming_enabled: bool | None = None
    favorite_results_enabled: bool | None = None
    event_announcements_enabled: bool | None = None


class PushTokenRegister(BaseModel):
    """Request schema for registering a push token."""
    token: str = Field(..., description="FCM push notification token")
    device_type: str = Field(
        default="unknown",
        description="Device type: ios, android, web",
    )
