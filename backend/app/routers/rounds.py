"""Round + submission + scoring endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import events as ev
from .. import models, schemas, services
from ..database import get_db
from ..deps import get_current_user, require_host, require_participant
from ..workers.job_worker import job_queue
from ..ws.manager import manager

router = APIRouter(prefix="/rooms/{room_id}", tags=["rounds"])


def _get_room(db: Session, room_id: str) -> models.Room:
    room = db.get(models.Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


# ---------- Rounds ----------


@router.post("/rounds", response_model=schemas.RoundOut)
async def start_round(
    room_id: str,
    req: schemas.StartRoundRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    room = _get_room(db, room_id)
    require_host(room.id, user, db)

    if room.status in (models.RoomStatus.in_round,):
        raise HTTPException(status_code=409, detail="A round is already in progress")
    if room.status == models.RoomStatus.ended:
        raise HTTPException(status_code=410, detail="Room has ended")

    next_number = (
        (db.query(models.Round).filter(models.Round.room_id == room.id).count() or 0) + 1
    )
    prompt = (req.prompt or room.prompt).strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Round prompt cannot be empty")

    rnd = models.Round(
        room_id=room.id,
        round_number=next_number,
        prompt=prompt,
        status=models.RoundStatus.open,
    )
    db.add(rnd)
    db.flush()

    room.current_round_id = rnd.id
    room.status = models.RoomStatus.in_round
    db.add(
        models.Event(
            room_id=room.id,
            type=ev.ROUND_STARTED,
            payload={
                "round_id": rnd.id,
                "round_number": rnd.round_number,
                "prompt": rnd.prompt,
            },
        )
    )
    db.commit()
    db.refresh(rnd)

    out = services.round_to_out(db, rnd)
    await manager.broadcast(
        room.id,
        ev.ROUND_STARTED,
        {
            "round_id": rnd.id,
            "round_number": rnd.round_number,
            "prompt": rnd.prompt,
            "room_status": room.status.value,
        },
    )
    return out


# ---------- Submissions ----------


@router.post("/rounds/{round_id}/submissions", response_model=schemas.SubmissionOut)
async def create_submission(
    room_id: str,
    round_id: str,
    req: schemas.SubmitRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    room = _get_room(db, room_id)
    participant = require_participant(room.id, user, db)

    if participant.role == models.ParticipantRole.host:
        # Backend-enforced rule from the assignment: host cannot submit.
        raise HTTPException(status_code=403, detail="Hosts cannot submit entries")

    rnd = db.get(models.Round, round_id)
    if not rnd or rnd.room_id != room.id:
        raise HTTPException(status_code=404, detail="Round not found in this room")
    if rnd.status != models.RoundStatus.open:
        raise HTTPException(status_code=409, detail="Round is not accepting submissions")

    existing = (
        db.query(models.Submission)
        .filter(
            models.Submission.round_id == rnd.id,
            models.Submission.user_id == user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="You have already submitted for this round")

    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Submission prompt cannot be empty")

    submission = models.Submission(round_id=rnd.id, user_id=user.id, prompt=prompt)
    db.add(submission)
    db.flush()

    job = models.Job(
        submission_id=submission.id,
        status=models.JobStatus.queued,
        attempt=1,
    )
    db.add(job)
    db.flush()

    sub_payload = {
        "submission_id": submission.id,
        "round_id": rnd.id,
        "user_id": user.id,
        "display_name": user.display_name,
        "prompt": submission.prompt,
    }
    db.add(
        models.Event(
            room_id=room.id,
            type=ev.ROUND_SUBMISSION_CREATED,
            payload=sub_payload,
        )
    )
    db.add(
        models.Event(
            room_id=room.id,
            type=ev.JOB_QUEUED,
            payload={"job_id": job.id, "submission_id": submission.id, "attempt": 1},
        )
    )
    db.commit()
    db.refresh(submission)

    out = services.submission_to_out(db, submission)
    await manager.broadcast(room.id, ev.ROUND_SUBMISSION_CREATED, sub_payload)
    await manager.broadcast(
        room.id,
        ev.JOB_QUEUED,
        {"job_id": job.id, "submission_id": submission.id, "attempt": 1},
    )
    await job_queue.enqueue(job.id)
    return out


# ---------- Scoring ----------


@router.post("/rounds/{round_id}/score", response_model=schemas.RoundOut)
async def score_submission(
    room_id: str,
    round_id: str,
    req: schemas.ScoreRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    room = _get_room(db, room_id)
    require_host(room.id, user, db)

    rnd = db.get(models.Round, round_id)
    if not rnd or rnd.room_id != room.id:
        raise HTTPException(status_code=404, detail="Round not found in this room")
    if rnd.status not in (models.RoundStatus.scoring, models.RoundStatus.completed):
        raise HTTPException(
            status_code=409,
            detail="Round is not in scoring state yet",
        )

    submission = db.get(models.Submission, req.submission_id)
    if not submission or submission.round_id != rnd.id:
        raise HTTPException(status_code=404, detail="Submission not in this round")

    score = (
        db.query(models.Score)
        .filter(models.Score.submission_id == submission.id)
        .first()
    )
    if score:
        score.value = req.value
        score.note = req.note
        score.scored_by_user_id = user.id
    else:
        score = models.Score(
            submission_id=submission.id,
            value=req.value,
            note=req.note,
            scored_by_user_id=user.id,
        )
        db.add(score)

    db.add(
        models.Event(
            room_id=room.id,
            type=ev.SCORE_RECORDED,
            payload={
                "submission_id": submission.id,
                "value": req.value,
                "round_id": rnd.id,
            },
        )
    )
    db.commit()

    out = services.round_to_out(db, rnd)
    await manager.broadcast(
        room.id,
        ev.SCORE_RECORDED,
        {
            "submission_id": submission.id,
            "value": req.value,
            "round_id": rnd.id,
        },
    )
    return out


@router.post("/rounds/{round_id}/winner", response_model=schemas.RoomState)
async def pick_winner(
    room_id: str,
    round_id: str,
    req: schemas.PickWinnerRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    room = _get_room(db, room_id)
    require_host(room.id, user, db)

    rnd = db.get(models.Round, round_id)
    if not rnd or rnd.room_id != room.id:
        raise HTTPException(status_code=404, detail="Round not found in this room")
    if rnd.status not in (models.RoundStatus.scoring, models.RoundStatus.completed):
        raise HTTPException(status_code=409, detail="Round is not in scoring state yet")

    submission = db.get(models.Submission, req.submission_id)
    if not submission or submission.round_id != rnd.id:
        raise HTTPException(status_code=404, detail="Submission not in this round")

    rnd.winner_submission_id = submission.id
    rnd.status = models.RoundStatus.completed
    rnd.ended_at = datetime.utcnow()
    room.status = models.RoomStatus.lobby
    room.current_round_id = None

    db.add(
        models.Event(
            room_id=room.id,
            type=ev.WINNER_PICKED,
            payload={"round_id": rnd.id, "submission_id": submission.id},
        )
    )
    db.add(
        models.Event(
            room_id=room.id,
            type=ev.ROUND_COMPLETED,
            payload={"round_id": rnd.id},
        )
    )
    db.commit()

    await manager.broadcast(
        room.id,
        ev.WINNER_PICKED,
        {"round_id": rnd.id, "submission_id": submission.id},
    )
    await manager.broadcast(
        room.id,
        ev.ROUND_COMPLETED,
        {"round_id": rnd.id, "room_status": room.status.value},
    )
    return services.build_room_state(db, room, user)
