"""Reusable FastAPI dependencies (auth + role guards)."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from . import models
from .auth import decode_token
from .database import get_db


def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> models.User:
    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user


def get_user_from_token(token: str, db: Session) -> Optional[models.User]:
    """Used by the WS handshake which gets a token in the query string."""
    if not token:
        return None
    user_id = decode_token(token)
    if not user_id:
        return None
    return db.get(models.User, user_id)


def require_participant(
    room_id: str,
    user: models.User,
    db: Session,
) -> models.Participant:
    p = (
        db.query(models.Participant)
        .filter(
            models.Participant.room_id == room_id,
            models.Participant.user_id == user.id,
            models.Participant.is_active.is_(True),
        )
        .first()
    )
    if not p:
        raise HTTPException(status_code=403, detail="You are not a participant of this room")
    return p


def require_host(
    room_id: str,
    user: models.User,
    db: Session,
) -> models.Participant:
    p = require_participant(room_id, user, db)
    if p.role != models.ParticipantRole.host:
        raise HTTPException(status_code=403, detail="Host privileges required")
    return p
