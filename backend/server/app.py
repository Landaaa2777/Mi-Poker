"""Aplicación FastAPI: un WebSocket por invitado y, si existe, la interfaz ya compilada.

    uvicorn server.app:app --reload
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .protocol import CLIENT_MESSAGE, NOTICE, NewGame, NextHand, PlayerAction, options
from .session import BOT_DELAY, GameSession, SessionError

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
MAX_SESSIONS = 500

_GUEST_ID = re.compile(r"[A-Za-z0-9_-]{8,64}")


def create_app(
    bot_delay: tuple[float, float] = BOT_DELAY,
    simulations: int | None = None,
    serve_frontend: bool = True,
) -> FastAPI:
    app = FastAPI(title="mi-poker", description=NOTICE)
    # Partidas en memoria, una por identificador de invitado. Nada se guarda en disco.
    sessions: dict[str, GameSession] = {}
    app.state.sessions = sessions

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "notice": NOTICE}

    @app.websocket("/ws")
    async def play(websocket: WebSocket, guest_id: str = "") -> None:
        if not _GUEST_ID.fullmatch(guest_id):
            await websocket.close(code=4400, reason="Identificador de invitado inválido")
            return
        await websocket.accept()

        session = sessions.get(guest_id)
        if session is None:
            if len(sessions) >= MAX_SESSIONS:
                sessions.pop(next(iter(sessions)))  # se descarta la partida más antigua
            session = sessions[guest_id] = GameSession(bot_delay, simulations)

        send_lock = asyncio.Lock()

        async def send(message: dict) -> None:
            async with send_lock:
                await websocket.send_json(message)

        async def send_state() -> None:
            try:
                await send({"type": "state", "state": session.state()})
            except (WebSocketDisconnect, RuntimeError):
                pass  # el cliente se fue; la partida sigue en memoria

        # La última conexión del invitado es la que recibe el estado.
        session.listener = send_state
        await send({"type": "hello", "options": options(), "state": session.state()})

        try:
            while True:
                text = await websocket.receive_text()
                try:
                    message = CLIENT_MESSAGE.validate_json(text)
                    if isinstance(message, NewGame):
                        session.new_game(message.config)
                    elif isinstance(message, PlayerAction):
                        session.act(message.action, message.amount)
                    elif isinstance(message, NextHand):
                        session.next_hand()
                    else:
                        session.restart()
                except ValidationError as error:
                    await send({"type": "error", "message": _explain(error)})
                except SessionError as error:
                    await send({"type": "error", "message": str(error)})
                else:
                    await send_state()
        except WebSocketDisconnect:
            if session.listener is send_state:
                session.listener = None

    if serve_frontend and FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    return app


def _explain(error: ValidationError) -> str:
    """Primer problema de un mensaje mal formado, en una frase."""
    first = error.errors()[0]
    field = ".".join(str(part) for part in first["loc"] if not str(part).startswith("function"))
    reason = first["msg"].removeprefix("Value error, ")
    return f"Mensaje inválido ({field}): {reason}" if field else f"Mensaje inválido: {reason}"


app = create_app()
