"""Aplicación FastAPI: un WebSocket por jugador, las cuentas y la interfaz ya compilada.

    uvicorn server.app:app --reload
"""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from accounts import DEFAULT_COST, AccountStore, Cost, Throttle, token_hash

from .accounts_api import SESSION_COOKIE, account_routes, public_user, same_origin
from .protocol import CLIENT_MESSAGE, NOTICE, NewGame, NextHand, PlayerAction, options
from .session import BOT_DELAY, GameSession, SessionError

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND_DIST = BACKEND.parent / "frontend" / "dist"
# Base de datos de cuentas. Se puede llevar a otro sitio con MI_POKER_DB.
DATABASE = Path(os.environ.get("MI_POKER_DB") or BACKEND / "data" / "mi-poker.db")
MAX_SESSIONS = 500

_GUEST_ID = re.compile(r"[A-Za-z0-9_-]{8,64}")


def create_app(
    bot_delay: tuple[float, float] = BOT_DELAY,
    simulations: int | None = None,
    serve_frontend: bool = True,
    database: Path | str = DATABASE,
    password_cost: Cost = DEFAULT_COST,
) -> FastAPI:
    app = FastAPI(title="mi-poker", description=NOTICE)
    # Partidas en memoria, una por jugador: por cuenta o, sin ella, por
    # identificador de invitado. Las partidas no se guardan en disco.
    sessions: dict[str, GameSession] = {}
    app.state.sessions = sessions
    accounts = AccountStore(database, password_cost)
    app.state.accounts = accounts
    # Conexiones abiertas de cada sesión iniciada, para cortarlas al cerrarla.
    connections: dict[str, set[WebSocket]] = {}
    app.state.connections = connections

    async def close_connections(token: str) -> None:
        for websocket in connections.pop(token_hash(token), set()):
            try:
                await websocket.close(code=4401, reason="Sesión cerrada")
            except RuntimeError:
                pass  # ya estaba cerrada

    app.include_router(account_routes(accounts, Throttle(), close_connections))

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "notice": NOTICE}

    @app.websocket("/ws")
    async def play(websocket: WebSocket, guest_id: str = "") -> None:
        if not same_origin(websocket.headers):
            await websocket.close(code=4403, reason="Origen no permitido")
            return
        token = websocket.cookies.get(SESSION_COOKIE)
        user = await asyncio.to_thread(accounts.user_for_token, token)
        if user is None and not _GUEST_ID.fullmatch(guest_id):
            await websocket.close(code=4400, reason="Identificador de invitado inválido")
            return
        await websocket.accept()
        if user is not None and token:
            connections.setdefault(token_hash(token), set()).add(websocket)

        # Los identificadores de invitado no llevan ":", así que no chocan con las cuentas.
        key = f"user:{user.id}" if user else guest_id
        session = sessions.get(key)
        if session is None:
            if len(sessions) >= MAX_SESSIONS:
                sessions.pop(next(iter(sessions)))  # se descarta la partida más antigua
            session = sessions[key] = GameSession(bot_delay, simulations)

        send_lock = asyncio.Lock()

        async def send(message: dict) -> None:
            async with send_lock:
                await websocket.send_json(message)

        async def send_state() -> None:
            try:
                await send({"type": "state", "state": session.state()})
            except (WebSocketDisconnect, RuntimeError):
                pass  # el cliente se fue; la partida sigue en memoria

        # La última conexión del jugador es la que recibe el estado.
        session.listener = send_state
        await send(
            {
                "type": "hello",
                "options": options(),
                "user": public_user(user),
                "state": session.state(),
            }
        )

        try:
            while True:
                text = await websocket.receive_text()
                try:
                    message = CLIENT_MESSAGE.validate_json(text)
                    if isinstance(message, NewGame):
                        config = message.config
                        if user is not None:
                            # Con cuenta, el nombre en la mesa es el suyo, diga lo que diga el cliente.
                            config = config.model_copy(update={"player_name": user.username})
                        session.new_game(config)
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
        finally:
            open_sockets = connections.get(token_hash(token)) if token else None
            if open_sockets is not None:
                open_sockets.discard(websocket)
                if not open_sockets:
                    del connections[token_hash(token)]

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
