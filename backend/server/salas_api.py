"""Salas con amigos por HTTP y WebSocket.

    POST /api/salas                 {"game": "poker"}   crea una sala; quien la crea es el anfitrión
    GET  /api/salas/mia                                  la sala en la que estoy, si estoy en alguna
    POST /api/salas/{código}                             entro en la sala (o vuelvo a ella)
    POST /api/salas/{código}/salir                       salgo de la sala
    WS   /ws/sala/{código}                               la sala en tiempo real

Hace falta cuenta para todo. Un código que no existe cuenta como intento
fallido: si se repiten, se frenan, para que no se puedan ir probando códigos.

Por el WebSocket:
    servidor -> {"type": "sala", "sala": {...}}          lo que veo de la sala, en cada cambio
                {"type": "state", "state": {...}}        lo que veo de la partida, en cada cambio
                {"type": "error", "message": "..."}
    cliente  -> {"type": "configure", "game": "poker", "options": {...}}   solo el anfitrión
                {"type": "start"}                        empezar la partida (el anfitrión)
                {"type": "leave"}                        salir de la sala (o abandonar la partida)
                cualquier otro mensaje es una jugada: va a la partida, como en la
                partida contra bots ({"type": "action", ...}, {"type": "bet", ...}…)
"""

from __future__ import annotations

import asyncio
import json
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from accounts import AccountStore, Throttle, User
from core.session import SessionError
from games.registry import find_game

from .accounts_api import SESSION_COOKIE, same_origin
from .connections import SIGNED_OUT, Connections
from .salas import MakeRoom, Sala, SalaError, SalaNotFound, Salas, Viewer
from .validation import MAX_MESSAGE, TOO_LONG, explain

NEED_ACCOUNT = "Entra en tu cuenta para jugar con amigos"


class NewSala(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    game: str = Field(max_length=32)


class Configure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["configure"]
    game: str | None = Field(None, max_length=32)  # sin él, el mismo juego
    options: dict[str, Any] = {}


class Start(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["start"]


class Leave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["leave"]


SALA_MESSAGE = TypeAdapter(Annotated[Configure | Start | Leave, Field(discriminator="type")])
SALA_TYPES = {"configure", "start", "leave"}  # lo demás son jugadas de la partida


def message_type(text: str) -> str | None:
    """El "type" de un mensaje JSON, sin validar nada más; None si no se entiende."""
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data.get("type") if isinstance(data, dict) and isinstance(data.get("type"), str) else None


def summary(sala: Sala) -> dict[str, Any]:
    """Lo justo para saber a qué sala ir: su código, su juego y si ya se juega."""
    return {"code": sala.code, "game": sala.game.id, "status": sala.status.value}


def sala_routes(
    store: AccountStore, salas: Salas, connections: Connections, make_room: MakeRoom
) -> APIRouter:
    router = APIRouter()
    # Códigos que no existen: tras 10 en un minuto desde la misma dirección, a esperar.
    throttle = Throttle(max_failures=10, window=60.0)

    def failure(status: int, message: str, **headers: str) -> JSONResponse:
        return JSONResponse({"message": message}, status_code=status, headers=headers)

    async def signed_in(request: Request) -> User | None:
        return await asyncio.to_thread(store.user_for_token, request.cookies.get(SESSION_COOKIE))

    # Las rutas son asíncronas a propósito: así todas tocan las salas desde el
    # mismo hilo que los WebSocket, y no hace falta ningún cerrojo.

    @router.post("/api/salas")
    async def create(request: Request, body: NewSala) -> JSONResponse:
        if not same_origin(request.headers):
            return failure(403, "Petición rechazada")
        user = await signed_in(request)
        if user is None:
            return failure(401, NEED_ACCOUNT)
        game = find_game(body.game)
        if game is None:
            return failure(404, "Ese juego no existe")
        try:
            sala = await salas.create(game, user)
        except SalaError as error:
            return failure(409, str(error))
        return JSONResponse(summary(sala), status_code=201)

    @router.get("/api/salas/mia")
    async def mine(request: Request) -> dict[str, Any]:
        user = await signed_in(request)
        if user is None:
            return {"sala": None}
        salas.sweep()
        sala = salas.of_user(user.id)
        return {"sala": summary(sala) if sala else None}

    @router.post("/api/salas/{code}")
    async def join(request: Request, code: str) -> JSONResponse:
        if not same_origin(request.headers):
            return failure(403, "Petición rechazada")
        user = await signed_in(request)
        if user is None:
            return failure(401, NEED_ACCOUNT)
        key = request.client.host if request.client else ""
        wait = throttle.wait_seconds(key)
        if wait:
            return failure(
                429, f"Demasiados intentos. Espera {wait} segundos.", **{"Retry-After": str(wait)}
            )
        try:
            sala = await salas.join(code, user)
        except SalaNotFound as error:
            throttle.fail(key)
            return failure(404, str(error))
        except SalaError as error:
            return failure(409, str(error))
        return JSONResponse(summary(sala))

    @router.post("/api/salas/{code}/salir")
    async def leave(request: Request, code: str) -> JSONResponse:
        if not same_origin(request.headers):
            return failure(403, "Petición rechazada")
        user = await signed_in(request)
        if user is None:
            return failure(401, NEED_ACCOUNT)
        sala = salas.get(code)
        if sala is None or user.id not in sala.members:
            return failure(404, "No estás en esa sala")
        try:
            await salas.leave(sala, user.id)
        except SalaError as error:
            return failure(409, str(error))
        return JSONResponse({"sala": None})

    @router.websocket("/ws/sala/{code}")
    async def live(websocket: WebSocket, code: str) -> None:
        if not same_origin(websocket.headers):
            await websocket.close(code=4403, reason="Origen no permitido")
            return
        token = websocket.cookies.get(SESSION_COOKIE)
        user = await asyncio.to_thread(store.user_for_token, token)
        if user is None:
            await websocket.close(code=SIGNED_OUT, reason=NEED_ACCOUNT)
            return
        sala = salas.get(code)
        # A quien no es miembro no se le dice si la sala existe.
        if sala is None or user.id not in sala.members:
            await websocket.close(code=4404, reason="Sala no encontrada")
            return
        await websocket.accept()
        connections.add(token, websocket)
        send_lock = asyncio.Lock()

        async def send(message: dict[str, Any]) -> None:
            async with send_lock:
                await websocket.send_json(message)

        async def push() -> None:
            try:
                await send({"type": "sala", "sala": sala.describe(user.id)})
            except (WebSocketDisconnect, RuntimeError):
                pass  # se fue: se limpia al salir del bucle

        async def push_state() -> None:
            session = sala.session
            if session is None:
                return
            try:
                await send({"type": "state", "state": session.state(user.id)})
            except (WebSocketDisconnect, RuntimeError):
                pass

        async def close(code: int, reason: str) -> None:
            try:
                await websocket.close(code=code, reason=reason)
            except RuntimeError:
                pass  # ya estaba cerrada

        viewer = Viewer(user.id, push, push_state, close)
        salas.connect(sala, viewer)
        await sala.broadcast()  # todos ven que ha llegado (o que ha vuelto)
        await push_state()  # y quien vuelve a una partida empezada, ve su mesa
        try:
            while True:
                text = await websocket.receive_text()
                if len(text) > MAX_MESSAGE:
                    await send({"type": "error", "message": TOO_LONG})
                    continue
                try:
                    if message_type(text) not in SALA_TYPES:
                        # Una jugada: la partida la valida y la aplica, y todos ven el cambio.
                        session = sala.session
                        if session is None or session.finished:
                            raise SalaError("La partida no ha empezado")
                        session.handle(user.id, text)
                        await sala.broadcast_state()
                        continue
                    message = SALA_MESSAGE.validate_json(text)
                    if isinstance(message, Leave):
                        await salas.leave(sala, user.id)  # también cierra esta conexión
                        break
                    if isinstance(message, Start):
                        await salas.start(sala, user.id, make_room)
                        continue
                    game = find_game(message.game) if message.game else sala.game
                    if game is None:
                        raise SalaError("Ese juego no existe")
                    sala.configure(user.id, game, message.options)
                    await sala.broadcast()
                except ValidationError as error:
                    await send({"type": "error", "message": explain(error)})
                except (SalaError, SessionError) as error:
                    await send({"type": "error", "message": str(error)})
        except WebSocketDisconnect:
            pass
        finally:
            salas.disconnect(sala, viewer)
            connections.discard(token, websocket)
            if user.id in sala.members:
                # Desconectarse no es salir: los demás ven que no está, y su sitio sigue ahí.
                await sala.broadcast()

    return router
