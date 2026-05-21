"""In-process WebSocket connection registry + broadcast helpers.

This is the single source of truth for "who is listening to which room".
It is intentionally small and unaware of business logic: it just knows
"given a room_id, here are the websockets to push events to".

Realtime event model
--------------------
Every payload sent over a room socket has shape::

    {"type": "<event-name>", "payload": {...}, "ts": "<iso>"}

Names are stable (see ``events.py``) so the client switch is exhaustive.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, room_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[room_id].add(ws)

    async def disconnect(self, room_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[room_id].discard(ws)
            if not self._rooms[room_id]:
                self._rooms.pop(room_id, None)

    async def broadcast(self, room_id: str, event_type: str, payload: dict) -> None:
        message = json.dumps(
            {
                "type": event_type,
                "payload": payload,
                "ts": datetime.utcnow().isoformat(),
            },
            default=str,
        )
        # Snapshot under the lock so we can iterate safely
        async with self._lock:
            targets = list(self._rooms.get(room_id, ()))

        if not targets:
            return

        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._rooms.get(room_id, set()).discard(ws)


manager = ConnectionManager()
