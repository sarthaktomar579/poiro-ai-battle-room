"""WebSocket endpoint for a single room.

Handshake
---------
    GET /ws/rooms/{room_id}?token=<JWT>

On connect we authenticate with the token, verify the user is an active
participant, and immediately push a ``room.snapshot`` event so the client
can hydrate its store in one round-trip.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from .. import models, services
from ..database import SessionLocal
from ..deps import get_user_from_token
from ..ws.manager import manager

router = APIRouter()
log = logging.getLogger("poiro.ws")


@router.websocket("/ws/rooms/{room_id}")
async def room_socket(ws: WebSocket, room_id: str, token: str = ""):
    await ws.accept()

    with SessionLocal() as db:  # type: Session
        user = get_user_from_token(token, db)
        if not user:
            await ws.send_text(json.dumps({"type": "error", "payload": {"reason": "unauthenticated"}}))
            await ws.close(code=4401)
            return

        room = db.get(models.Room, room_id)
        if not room:
            await ws.send_text(json.dumps({"type": "error", "payload": {"reason": "not_found"}}))
            await ws.close(code=4404)
            return

        participant = (
            db.query(models.Participant)
            .filter(
                models.Participant.room_id == room.id,
                models.Participant.user_id == user.id,
            )
            .first()
        )
        if not participant:
            await ws.send_text(json.dumps({"type": "error", "payload": {"reason": "forbidden"}}))
            await ws.close(code=4403)
            return

        snapshot = services.build_room_state(db, room, user)

    await manager.connect(room_id, ws)
    try:
        await ws.send_text(
            json.dumps(
                {
                    "type": "room.snapshot",
                    "payload": snapshot.model_dump(mode="json"),
                    "ts": datetime.utcnow().isoformat(),
                },
                default=str,
            )
        )

        while True:
            # We only need to know if the client is still there. We accept
            # pings/no-ops but ignore message content; all writes go through
            # the REST API to keep the source of truth on one path.
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                try:
                    await ws.send_text(json.dumps({"type": "ping", "payload": {}}))
                except Exception:
                    break
                continue

            if msg == "ping":
                await ws.send_text(json.dumps({"type": "pong", "payload": {}}))

    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("WS error for room %s", room_id)
    finally:
        await manager.disconnect(room_id, ws)
