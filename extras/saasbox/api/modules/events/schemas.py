"""
Pydantic schemas for events module.
"""
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class EventLocation(BaseModel):
    """Event location details."""
    venue_name: str | None = None
    venue_address: str | None = None
    city: str | None = None
    province: str | None = None


class EventSettings(BaseModel):
    """Event configuration settings."""
    allow_predictions: bool = True
    allow_cheers: bool = True
    prediction_cutoff_minutes: int = 5
    max_cheers_per_racer: int = 5


class EventCreate(BaseModel):
    """Request schema for creating an event."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    event_date: date
    location: EventLocation | None = None
    lanes: int = Field(default=3, ge=2, le=6)
    use_points: bool = False
    settings: EventSettings | None = None


class EventUpdate(BaseModel):
    """Request schema for updating an event."""
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    event_date: date | None = None
    location: EventLocation | None = None
    lanes: int | None = Field(None, ge=2, le=6)
    use_points: bool | None = None
    settings: EventSettings | None = None


class EventResponse(BaseModel):
    """Response schema for an event."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    name: str
    description: str | None
    event_date: date
    venue_name: str | None
    venue_address: str | None
    city: str | None
    province: str | None
    status: str
    is_public: bool
    lanes: int
    use_points: bool
    settings: dict[str, Any]
    last_sync_at: datetime | None
    synced_by_device: str | None
    created_at: datetime
    updated_at: datetime | None


class EventListResponse(BaseModel):
    """Response schema for event list."""
    id: str
    name: str
    event_date: date
    city: str | None
    status: str
    is_public: bool
    racer_count: int = 0
    class_count: int = 0


class EventPublishRequest(BaseModel):
    """Request to publish an event."""
    is_public: bool = True


class EventSyncData(BaseModel):
    """Data structure for syncing from DerbyPi."""
    db_hash: str = Field(..., description="SHA-256 hash of DerbyNet database")
    classes: list["ClassSyncData"]
    racers: list["RacerSyncData"]
    rounds: list["RoundSyncData"]
    heats: list["HeatSyncData"]
    results: list["ResultSyncData"]


class ClassSyncData(BaseModel):
    """Class data from DerbyNet sync."""
    derbynet_class_id: int
    name: str
    sort_order: int = 0


class RacerSyncData(BaseModel):
    """Racer data from DerbyNet sync."""
    derbynet_racer_id: int
    derbynet_class_id: int | None
    first_name: str
    last_name: str
    car_number: int
    car_name: str | None = None


class RoundSyncData(BaseModel):
    """Round data from DerbyNet sync."""
    derbynet_round_id: int
    derbynet_class_id: int | None
    name: str
    round_number: int


class HeatSyncData(BaseModel):
    """Heat data from DerbyNet sync."""
    derbynet_round_id: int
    heat_number: int
    is_current: bool = False


class ResultSyncData(BaseModel):
    """Race result data from DerbyNet sync."""
    derbynet_round_id: int
    heat_number: int
    derbynet_racer_id: int
    lane: int
    finish_time: float | None = None
    finish_place: int | None = None


class SyncStatusResponse(BaseModel):
    """Response for sync status."""
    event_id: str
    last_sync_at: datetime | None
    synced_by_device: str | None
    db_hash: str | None
    racer_count: int
    class_count: int
    round_count: int
    heat_count: int
    result_count: int


# Forward references for nested models
EventSyncData.model_rebuild()
