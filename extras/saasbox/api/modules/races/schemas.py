"""
Pydantic schemas for races module.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


# Racer schemas (included here to avoid circular imports)
class RacerBrief(BaseModel):
    """Brief racer info for race lineups."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    first_name: str
    last_name: str
    car_number: int
    car_name: str | None
    class_name: str | None = None

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def masked_name(self) -> str:
        """Privacy-safe name for public display."""
        if self.last_name:
            return f"{self.first_name} {self.last_name[0]}."
        return self.first_name


class RacerInLane(BaseModel):
    """Racer with lane assignment and result."""
    lane: int
    racer: RacerBrief
    finish_time: str | None = None  # Formatted as string "3.4567"
    finish_place: int | None = None


# Round schemas
class RoundResponse(BaseModel):
    """Response schema for a round."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    class_id: str | None
    class_name: str | None = None
    name: str
    round_number: int
    status: str
    heats_scheduled: int
    heats_completed: int
    roster_size: int


class RoundListResponse(BaseModel):
    """Response for round list with standings option."""
    id: str
    name: str
    class_name: str | None
    round_number: int
    status: str
    heats_scheduled: int
    heats_completed: int
    is_current: bool = False


# Heat schemas
class HeatResponse(BaseModel):
    """Response schema for a heat."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    round_id: str
    round_name: str | None = None
    heat_number: int
    status: str
    is_current: bool
    started_at: datetime | None
    finished_at: datetime | None
    racers: list[RacerInLane] = []


class HeatListResponse(BaseModel):
    """Brief heat info for lists."""
    id: str
    round_name: str
    heat_number: int
    status: str
    is_current: bool


# Race result schemas
class RaceResultResponse(BaseModel):
    """Race result for a single racer."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    heat_id: str
    racer_id: str
    racer_name: str
    car_number: int
    lane: int
    finish_time: str | None
    finish_place: int | None
    points: int | None


class HeatResultsResponse(BaseModel):
    """Complete results for a heat."""
    heat_id: str
    round_name: str
    heat_number: int
    status: str
    results: list[RaceResultResponse]


# Current race (polling endpoint)
class TimerInfo(BaseModel):
    """Timer hardware status."""
    lanes: int
    state: str  # CONNECTED, STAGING, RACE, UNCONFIGURED, UNCONFIRMED
    message: str
    health_status: str  # healthy, degraded, warning, critical
    timers_online: int
    timers_ready: int
    last_contact: datetime | None = None


class CurrentRaceResponse(BaseModel):
    """
    Response for the polling endpoint.
    Contains all information needed to display current race status.
    """
    # Race status
    now_racing: bool
    race_status: str  # idle, staging, racing, finished

    # Current heat info
    current_heat: HeatResponse | None = None
    round_name: str | None = None
    class_name: str | None = None
    heat_number: int | None = None
    total_heats: int | None = None

    # Racers in current heat
    racers: list[RacerInLane] = []

    # Timer status (if available)
    timer: TimerInfo | None = None

    # Server-recommended poll interval (ms)
    poll_interval: int = 1000

    # Last update timestamp
    updated_at: datetime


# Standings schemas
class RacerStanding(BaseModel):
    """Racer standings within a round."""
    rank: int
    racer: RacerBrief
    races_completed: int
    total_time: str | None  # Sum of finish times
    average_time: str | None
    best_time: str | None
    total_points: int | None
    wins: int = 0
    podiums: int = 0  # Top 3 finishes


class RoundStandingsResponse(BaseModel):
    """Standings for a round."""
    round_id: str
    round_name: str
    class_name: str | None
    heats_completed: int
    heats_total: int
    standings: list[RacerStanding]
    use_points: bool = False


# Statistics schemas
class RacerStats(BaseModel):
    """Statistics for a racer across an event."""
    racer_id: str
    racer_name: str
    car_number: int
    class_name: str | None

    # Race counts
    total_races: int
    wins: int
    podiums: int

    # Time stats
    best_time: str | None
    average_time: str | None
    worst_time: str | None

    # Points (if using points system)
    total_points: int | None

    # Placement distribution
    first_places: int = 0
    second_places: int = 0
    third_places: int = 0


class EventStatsResponse(BaseModel):
    """Overall event statistics."""
    event_id: str
    event_name: str

    # Counts
    total_racers: int
    total_classes: int
    total_rounds: int
    total_heats: int
    heats_completed: int

    # Timing
    fastest_time: str | None
    fastest_racer: str | None
    average_time: str | None

    # Status
    event_status: str
    is_racing: bool


class UpcomingHeat(BaseModel):
    """Information about an upcoming heat."""
    heat_id: str
    round_name: str
    heat_number: int
    estimated_time: datetime | None = None
    racers: list[RacerBrief]
