"""
Pydantic schemas for audience participation module.
"""
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class RacerBrief(BaseModel):
    """Brief racer info for predictions."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    first_name: str
    last_name: str
    car_number: int
    car_name: str | None = None


class HeatBrief(BaseModel):
    """Brief heat info for predictions."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    heat_number: int
    round_name: str | None = None
    status: str


class PredictionCreate(BaseModel):
    """Request schema for creating a prediction."""
    heat_id: str = Field(..., description="ID of the heat to predict")
    predicted_racer_id: str = Field(..., description="ID of the racer predicted to win")


class PredictionResponse(BaseModel):
    """Response schema for a prediction."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    heat_id: str
    heat: HeatBrief | None = None
    predicted_racer_id: str
    predicted_racer: RacerBrief | None = None
    is_correct: bool | None
    points_earned: int
    created_at: datetime


class PredictionListResponse(BaseModel):
    """Response schema for prediction list."""
    id: str
    heat_id: str
    heat_number: int
    round_name: str | None = None
    predicted_racer: RacerBrief
    is_correct: bool | None
    points_earned: int
    created_at: datetime


class LeaderboardEntry(BaseModel):
    """Entry in the prediction leaderboard."""
    rank: int
    user_id: str
    display_name: str | None
    total_predictions: int
    correct_predictions: int
    total_points: int
    accuracy_percent: float


class LeaderboardResponse(BaseModel):
    """Response for prediction leaderboard."""
    event_id: str
    event_name: str
    total_participants: int
    entries: list[LeaderboardEntry]


class PredictionStats(BaseModel):
    """User's prediction statistics for an event."""
    event_id: str
    total_predictions: int
    correct_predictions: int
    pending_predictions: int
    total_points: int
    accuracy_percent: float
    rank: int | None = None


class UpcomingHeatForPrediction(BaseModel):
    """Heat available for prediction."""
    heat_id: str
    heat_number: int
    round_name: str
    class_name: str | None = None
    racers: list[RacerBrief]
    prediction_cutoff_at: datetime | None = None
    user_has_predicted: bool = False


# =============================================================================
# Cheer Schemas
# =============================================================================

class CheerResponse(BaseModel):
    """Response schema for a cheer."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    racer_id: str
    racer: RacerBrief | None = None
    created_at: datetime


class CheerCountResponse(BaseModel):
    """Response for cheer count."""
    racer_id: str
    racer: RacerBrief | None = None
    cheer_count: int


class RacerCheerStats(BaseModel):
    """Cheer statistics for a racer."""
    racer_id: str
    racer: RacerBrief
    total_cheers: int
    unique_supporters: int


class EventCheerLeaderboard(BaseModel):
    """Leaderboard of most-cheered racers in an event."""
    event_id: str
    event_name: str
    entries: list[RacerCheerStats]


class UserCheerStatus(BaseModel):
    """User's cheer status for a racer."""
    racer_id: str
    cheers_sent: int
    max_cheers: int
    can_cheer: bool


# =============================================================================
# Poll Schemas
# =============================================================================

class PollOptionSchema(BaseModel):
    """A poll option."""
    id: str
    label: str
    racer_id: str | None = None


class PollOptionWithVotes(PollOptionSchema):
    """Poll option with vote count (for results)."""
    vote_count: int
    vote_percent: float


class PollResponse(BaseModel):
    """Response schema for a poll."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    question: str
    description: str | None = None
    options: list[PollOptionSchema]
    status: str
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    created_at: datetime
    user_has_voted: bool = False
    user_vote_option_id: str | None = None


class PollListResponse(BaseModel):
    """Response for poll list."""
    id: str
    question: str
    status: str
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    total_votes: int
    user_has_voted: bool = False


class PollVoteCreate(BaseModel):
    """Request schema for voting in a poll."""
    option_id: str = Field(..., description="ID of the option to vote for")


class PollVoteResponse(BaseModel):
    """Response after voting in a poll."""
    poll_id: str
    option_id: str
    message: str = "Vote recorded successfully"


class PollResultsResponse(BaseModel):
    """Poll results with vote counts."""
    id: str
    question: str
    description: str | None = None
    status: str
    total_votes: int
    options: list[PollOptionWithVotes]
    closes_at: datetime | None = None
    user_vote_option_id: str | None = None
