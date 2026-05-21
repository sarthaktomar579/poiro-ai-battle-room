"""Room lifecycle endpoints (create, join, get state, list mine)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import events as ev
from .. import models, schemas, services
from ..database import get_db
from ..deps import get_current_user
from ..ws.manager import manager

router = APIRouter(prefix="/rooms", tags=["rooms"])


def _emit(db: Session, room_id: str, event_type: str, payload: dict) -> None:
    db.add(models.Event(room_id=room_id, type=event_type, payload=payload))


@router.post("", response_model=schemas.RoomState)
async def create_room(
    req: schemas.CreateRoomRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    code = services.generate_room_code(db)
    room = models.Room(
        code=code,
        name=req.name.strip(),
        prompt=req.prompt.strip(),
        host_id=user.id,
        status=models.RoomStatus.lobby,
    )
    db.add(room)
    db.flush()

    db.add(
        models.Participant(
            room_id=room.id, user_id=user.id, role=models.ParticipantRole.host
        )
    )
    _emit(
        db,
        room.id,
        ev.ROOM_PARTICIPANT_JOINED,
        {"user_id": user.id, "display_name": user.display_name, "role": "host"},
    )
    db.commit()
    db.refresh(room)

    return services.build_room_state(db, room, user)


@router.post("/join", response_model=schemas.RoomState)
async def join_room(
    req: schemas.JoinRoomRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    code = req.code.strip().upper()
    room = db.query(models.Room).filter(models.Room.code == code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.status == models.RoomStatus.ended:
        raise HTTPException(status_code=410, detail="This room has ended")

    existing = (
        db.query(models.Participant)
        .filter(
            models.Participant.room_id == room.id,
            models.Participant.user_id == user.id,
        )
        .first()
    )
    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.commit()
        # Idempotent join: return current state for reconnecting users.
        return services.build_room_state(db, room, user)

    if room.host_id == user.id:
        # Host re-joining their own room is fine, but they're already host.
        return services.build_room_state(db, room, user)

    db.add(
        models.Participant(
            room_id=room.id,
            user_id=user.id,
            role=models.ParticipantRole.participant,
        )
    )
    _emit(
        db,
        room.id,
        ev.ROOM_PARTICIPANT_JOINED,
        {"user_id": user.id, "display_name": user.display_name, "role": "participant"},
    )
    db.commit()

    await manager.broadcast(
        room.id,
        ev.ROOM_PARTICIPANT_JOINED,
        {"user_id": user.id, "display_name": user.display_name, "role": "participant"},
    )
    return services.build_room_state(db, room, user)


@router.get("/mine", response_model=List[schemas.RoomSummary])
def my_rooms(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    rows = (
        db.query(models.Room)
        .join(models.Participant, models.Participant.room_id == models.Room.id)
        .filter(models.Participant.user_id == user.id)
        .order_by(models.Room.created_at.desc())
        .all()
    )
    # Deduplicate (host has both ownership and participant rows).
    seen = set()
    out: List[schemas.RoomSummary] = []
    for r in rows:
        if r.id in seen:
            continue
        seen.add(r.id)
        out.append(schemas.RoomSummary.model_validate(r))
    return out


@router.get("/by-code/{code}", response_model=schemas.RoomState)
def get_room_by_code(
    code: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    room = db.query(models.Room).filter(models.Room.code == code.upper()).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Authorisation: only participants of the room can see full state.
    p = (
        db.query(models.Participant)
        .filter(
            models.Participant.room_id == room.id,
            models.Participant.user_id == user.id,
        )
        .first()
    )
    if not p:
        raise HTTPException(status_code=403, detail="Join the room first")
    return services.build_room_state(db, room, user)


@router.post("/{room_id}/end", response_model=schemas.RoomState)
async def end_room(
    room_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    room = db.get(models.Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.host_id != user.id:
        raise HTTPException(status_code=403, detail="Only the host can end the room")

    room.status = models.RoomStatus.ended
    _emit(db, room.id, ev.ROOM_STATE_CHANGED, {"status": room.status.value})
    db.commit()

    await manager.broadcast(room.id, ev.ROOM_STATE_CHANGED, {"status": room.status.value})
    return services.build_room_state(db, room, user)
