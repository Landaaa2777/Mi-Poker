"""Conexiones abiertas (WebSocket) de cada sesión iniciada.

Al cerrar una sesión se cortan todas sus conexiones: las de las partidas contra
bots y las de las salas. En el registro se guarda solo el hash del token.
"""

from __future__ import annotations

from fastapi import WebSocket

from accounts import token_hash

SIGNED_OUT = 4401  # código de cierre: sin sesión


class Connections:
    def __init__(self) -> None:
        self._by_session: dict[str, set[WebSocket]] = {}

    def __len__(self) -> int:
        """Cuántas sesiones tienen alguna conexión abierta."""
        return len(self._by_session)

    def add(self, token: str | None, websocket: WebSocket) -> None:
        if token:
            self._by_session.setdefault(token_hash(token), set()).add(websocket)

    def discard(self, token: str | None, websocket: WebSocket) -> None:
        if not token:
            return
        key = token_hash(token)
        sockets = self._by_session.get(key)
        if sockets is not None:
            sockets.discard(websocket)
            if not sockets:
                del self._by_session[key]

    async def close_session(self, token: str) -> None:
        """Corta todas las conexiones de una sesión que se acaba de cerrar."""
        for websocket in self._by_session.pop(token_hash(token), set()):
            try:
                await websocket.close(code=SIGNED_OUT, reason="Sesión cerrada")
            except RuntimeError:
                pass  # ya estaba cerrada
