"""ORM models for the Poiro AI Battle Room.

The data model intentionally mirrors the assignment's required entities so
the README ER diagram and the code stay 1:1:

  User  -< Room (host)
  User  -< Participant >- Room
  Room  -< Round
  Round -< Submission >- User
  Submission -< Job (1:N for retries; latest is the canonical state)
  Submission -< Score
  Room  -< Event   (event-sourced room activity log)
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ---------- Enums ----------


class RoomStatus(str, enum.Enum):
    lobby = "lobby"
    in_round = "in_round"
    scoring = "scoring"
    ended = "ended"


class RoundStatus(str, enum.Enum):
    open = "open"           # accepting submissions
    generating = "generating"  # all submissions in, jobs running
    scoring = "scoring"     # host can score
    completed = "completed"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    timed_out = "timed_out"


class ParticipantRole(str, enum.Enum):
    host = "host"
    participant = "participant"


# ---------- Models ----------


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    hosted_rooms: Mapped[List["Room"]] = relationship(back_populates="host")
    participations: Mapped[List["Participant"]] = relationship(back_populates="user")
    submissions: Mapped[List["Submission"]] = relationship(back_populates="user")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RoomStatus] = mapped_column(
        Enum(RoomStatus, native_enum=False), default=RoomStatus.lobby, nullable=False
    )
    host_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    current_round_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    host: Mapped[User] = relationship(back_populates="hosted_rooms")
    participants: Mapped[List["Participant"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    rounds: Mapped[List["Round"]] = relationship(
        back_populates="room", cascade="all, delete-orphan", order_by="Round.round_number"
    )
    events: Mapped[List["Event"]] = relationship(
        back_populates="room", cascade="all, delete-orphan", order_by="Event.created_at"
    )


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("room_id", "user_id", name="uq_room_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    room_id: Mapped[str] = mapped_column(String(36), ForeignKey("rooms.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    role: Mapped[ParticipantRole] = mapped_column(
        Enum(ParticipantRole, native_enum=False),
        default=ParticipantRole.participant,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    room: Mapped[Room] = relationship(back_populates="participants")
    user: Mapped[User] = relationship(back_populates="participations")


class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    room_id: Mapped[str] = mapped_column(String(36), ForeignKey("rooms.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RoundStatus] = mapped_column(
        Enum(RoundStatus, native_enum=False), default=RoundStatus.open, nullable=False
    )
    winner_submission_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    room: Mapped[Room] = relationship(back_populates="rounds")
    submissions: Mapped[List["Submission"]] = relationship(
        back_populates="round", cascade="all, delete-orphan"
    )


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("round_id", "user_id", name="uq_round_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    round_id: Mapped[str] = mapped_column(String(36), ForeignKey("rounds.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    round: Mapped[Round] = relationship(back_populates="submissions")
    user: Mapped[User] = relationship(back_populates="submissions")
    jobs: Mapped[List["Job"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan", order_by="Job.created_at"
    )
    score: Mapped[Optional["Score"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan", uselist=False
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    submission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("submissions.id"), nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False), default=JobStatus.queued, nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="mock", nullable=False)
    output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    submission: Mapped[Submission] = relationship(back_populates="jobs")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    submission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("submissions.id"), unique=True, nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scored_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    submission: Mapped[Submission] = relationship(back_populates="score")


class Event(Base):
    """Append-only log of every meaningful room state transition.

    This doubles as our realtime audit log: the WebSocket layer reads the
    same record it just inserted and broadcasts it to the room.
    """

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    room_id: Mapped[str] = mapped_column(String(36), ForeignKey("rooms.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    room: Mapped[Room] = relationship(back_populates="events")
