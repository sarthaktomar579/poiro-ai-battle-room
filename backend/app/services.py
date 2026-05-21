"""Pure-ish helpers that assemble high-level views from the ORM.

Routers stay thin; this module hosts the only place where we know how a
room snapshot is shaped (so WS handshake and HTTP snapshot can't drift).
"""
from __future__ import annotations

import random
import string
from typing import List, Optional

from sqlalchemy.orm import Session

from . import models, schemas


# ---------- Room code ----------


def generate_room_code(db: Session, *, length: int = 6, max_attempts: int = 25) -> str:
    """Short, easy-to-share, collision-free code."""
    alphabet = string.ascii_uppercase + string.digits
    # Drop visually ambiguous characters to keep codes phone-friendly.
    alphabet = alphabet.translate(str.maketrans("", "", "O0I1"))
    for _ in range(max_attempts):
        code = "".join(random.choices(alphabet, k=length))
        if not db.query(models.Room).filter(models.Room.code == code).first():
            return code
    # Extremely unlikely; widen the space.
    return "".join(random.choices(alphabet, k=length + 2))


# ---------- Submission shaping ----------


def submission_to_out(db: Session, submission: models.Submission) -> schemas.SubmissionOut:
    latest_job = (
        db.query(models.Job)
        .filter(models.Job.submission_id == submission.id)
        .order_by(models.Job.created_at.desc())
        .first()
    )
    score = (
        db.query(models.Score)
        .filter(models.Score.submission_id == submission.id)
        .first()
    )
    return schemas.SubmissionOut(
        id=submission.id,
        round_id=submission.round_id,
        user_id=submission.user_id,
        display_name=submission.user.display_name if submission.user else "",
        prompt=submission.prompt,
        created_at=submission.created_at,
        latest_job=schemas.JobOut.model_validate(latest_job) if latest_job else None,
        score=schemas.ScoreOut.model_validate(score) if score else None,
    )


def round_to_out(db: Session, rnd: models.Round) -> schemas.RoundOut:
    subs = (
        db.query(models.Submission)
        .filter(models.Submission.round_id == rnd.id)
        .order_by(models.Submission.created_at.asc())
        .all()
    )
    return schemas.RoundOut(
        id=rnd.id,
        room_id=rnd.room_id,
        round_number=rnd.round_number,
        prompt=rnd.prompt,
        status=rnd.status,
        winner_submission_id=rnd.winner_submission_id,
        started_at=rnd.started_at,
        ended_at=rnd.ended_at,
        submissions=[submission_to_out(db, s) for s in subs],
    )


def participants_for_room(db: Session, room_id: str) -> List[schemas.ParticipantOut]:
    rows = (
        db.query(models.Participant, models.User)
        .join(models.User, models.User.id == models.Participant.user_id)
        .filter(models.Participant.room_id == room_id)
        .order_by(models.Participant.joined_at.asc())
        .all()
    )
    out: List[schemas.ParticipantOut] = []
    for p, u in rows:
        out.append(
            schemas.ParticipantOut(
                id=p.id,
                user_id=u.id,
                role=p.role,
                is_active=p.is_active,
                joined_at=p.joined_at,
                display_name=u.display_name,
                email=u.email,
            )
        )
    return out


def leaderboard_for_room(db: Session, room_id: str) -> List[schemas.LeaderboardEntry]:
    rounds = db.query(models.Round).filter(models.Round.room_id == room_id).all()
    if not rounds:
        return []
    round_ids = [r.id for r in rounds]

    totals: dict[str, float] = {}
    wins: dict[str, int] = {}
    names: dict[str, str] = {}

    subs = (
        db.query(models.Submission, models.User)
        .join(models.User, models.User.id == models.Submission.user_id)
        .filter(models.Submission.round_id.in_(round_ids))
        .all()
    )
    sub_by_id: dict[str, models.Submission] = {s.id: s for s, _ in subs}
    for s, u in subs:
        names[u.id] = u.display_name
        totals.setdefault(u.id, 0.0)
        wins.setdefault(u.id, 0)

    scores = (
        db.query(models.Score)
        .filter(models.Score.submission_id.in_(list(sub_by_id.keys())))
        .all()
        if sub_by_id
        else []
    )
    for sc in scores:
        sub = sub_by_id.get(sc.submission_id)
        if sub:
            totals[sub.user_id] = totals.get(sub.user_id, 0.0) + float(sc.value)

    for r in rounds:
        if r.winner_submission_id and r.winner_submission_id in sub_by_id:
            wins[sub_by_id[r.winner_submission_id].user_id] = (
                wins.get(sub_by_id[r.winner_submission_id].user_id, 0) + 1
            )

    entries = [
        schemas.LeaderboardEntry(
            user_id=uid, display_name=names.get(uid, "?"), total_score=round(total, 2), wins=wins.get(uid, 0)
        )
        for uid, total in totals.items()
    ]
    entries.sort(key=lambda e: (-e.wins, -e.total_score, e.display_name))
    return entries


def build_room_state(
    db: Session,
    room: models.Room,
    user: models.User,
) -> schemas.RoomState:
    participant = (
        db.query(models.Participant)
        .filter(
            models.Participant.room_id == room.id,
            models.Participant.user_id == user.id,
        )
        .first()
    )
    role = participant.role if participant else models.ParticipantRole.participant

    current_round: Optional[schemas.RoundOut] = None
    if room.current_round_id:
        rnd = db.get(models.Round, room.current_round_id)
        if rnd:
            current_round = round_to_out(db, rnd)

    past_rounds_q = (
        db.query(models.Round)
        .filter(models.Round.room_id == room.id, models.Round.id != (room.current_round_id or ""))
        .order_by(models.Round.round_number.desc())
        .all()
    )
    past_rounds = [round_to_out(db, r) for r in past_rounds_q]

    return schemas.RoomState(
        room=schemas.RoomSummary.model_validate(room),
        role=role,
        participants=participants_for_room(db, room.id),
        current_round=current_round,
        past_rounds=past_rounds,
        leaderboard=leaderboard_for_room(db, room.id),
    )
