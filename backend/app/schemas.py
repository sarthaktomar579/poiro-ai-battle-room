"""Pydantic request/response schemas (the public API contract)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import JobStatus, ParticipantRole, RoomStatus, RoundStatus


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: "UserOut"


class UserOut(ORMBase):
    id: str
    email: EmailStr
    display_name: str
    created_at: datetime


# ---------- Rooms ----------


class CreateRoomRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=2000)


class JoinRoomRequest(BaseModel):
    code: str = Field(min_length=4, max_length=8)


class RoomSummary(ORMBase):
    id: str
    code: str
    name: str
    prompt: str
    status: RoomStatus
    host_id: str
    current_round_id: Optional[str] = None
    created_at: datetime


class ParticipantOut(ORMBase):
    id: str
    user_id: str
    role: ParticipantRole
    is_active: bool
    joined_at: datetime
    display_name: str = ""
    email: str = ""


# ---------- Rounds / Submissions / Jobs ----------


class StartRoundRequest(BaseModel):
    prompt: Optional[str] = Field(default=None, max_length=2000)


class SubmitRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)


class ScoreRequest(BaseModel):
    submission_id: str
    value: float = Field(ge=0, le=10)
    note: Optional[str] = Field(default=None, max_length=500)


class PickWinnerRequest(BaseModel):
    submission_id: str


class JobOut(ORMBase):
    id: str
    status: JobStatus
    attempt: int
    provider: str
    output: Optional[str]
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class ScoreOut(ORMBase):
    id: str
    value: float
    note: Optional[str]
    scored_by_user_id: str
    created_at: datetime


class SubmissionOut(ORMBase):
    id: str
    round_id: str
    user_id: str
    display_name: str = ""
    prompt: str
    created_at: datetime
    latest_job: Optional[JobOut] = None
    score: Optional[ScoreOut] = None


class RoundOut(ORMBase):
    id: str
    room_id: str
    round_number: int
    prompt: str
    status: RoundStatus
    winner_submission_id: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    submissions: List[SubmissionOut] = []


class RoomState(BaseModel):
    """Everything the frontend needs to fully render a room.

    Returned by the snapshot endpoint and re-used as the "hello" payload
    when a websocket client connects.
    """

    room: RoomSummary
    role: ParticipantRole
    participants: List[ParticipantOut]
    current_round: Optional[RoundOut] = None
    past_rounds: List[RoundOut] = []
    leaderboard: List["LeaderboardEntry"] = []


class LeaderboardEntry(BaseModel):
    user_id: str
    display_name: str
    total_score: float
    wins: int


class RoomActivityEvent(ORMBase):
    id: str
    room_id: str
    type: str
    payload: dict
    created_at: datetime


# Resolve forward references
TokenResponse.model_rebuild()
RoomState.model_rebuild()
