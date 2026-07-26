"""In-process WebSocket fan-out for match negotiations.

A single hub keyed by negotiation id (the accepted OpponentApplication id). Good enough for a
single-process deployment; a multi-worker setup would swap the in-memory rooms for Redis pub/sub.
Both the WebSocket endpoint (chat) and the REST handlers (proposal/agreement events) publish here.
"""

import asyncio

from fastapi import WebSocket


class NegotiationHub:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def join(self, room: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms.setdefault(room, set()).add(ws)

    async def leave(self, room: str, ws: WebSocket) -> None:
        async with self._lock:
            conns = self._rooms.get(room)
            if conns:
                conns.discard(ws)
                if not conns:
                    self._rooms.pop(room, None)

    async def broadcast(self, room: str, message: dict) -> None:
        for ws in list(self._rooms.get(room, set())):
            try:
                await ws.send_json(message)
            except Exception:
                # A dead socket will be cleaned up on its own disconnect; don't let one break the rest.
                await self.leave(room, ws)


hub = NegotiationHub()
