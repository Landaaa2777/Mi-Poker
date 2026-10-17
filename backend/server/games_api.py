"""Juegos y partidas por HTTP.

    GET  /api/juegos                         los juegos del menú, con sus opciones
    GET  /api/partidas?guest_id=...          mis partidas abiertas y si siguen en curso
    POST /api/partidas  {"game": "poker", "guest_id": "..."}
                                             mi partida de ese juego (si no hay, se crea)

La partida es de quien la pide: la cuenta de la cookie de sesión o, sin ella,
el identificador de invitado. La respuesta de POST trae su id, con el que el
navegador se conecta a /ws/{juego}/{partida_id}.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from accounts import AccountStore, User
from core.registry import GameInfo
from core.session import GameSession
from games.registry import REGISTRY, find_game

from .accounts_api import SESSION_COOKIE, same_origin
from .options import describe_options
from .partidas import Partida, Partidas, owner_key

# Crea la partida de un juego para un dueño: (juego, dueño, id de la partida, cuenta) -> partida
MakeSession = Callable[[GameInfo, str, str, User | None], GameSession]


class PartidaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    game: str = Field(max_length=32)
    guest_id: str = Field("", max_length=64)


def describe_game(game: GameInfo) -> dict[str, Any]:
    """Lo que el menú sabe de un juego."""
    low, high = game.players
    return {
        "id": game.id,
        "name": game.name,
        "description": game.description,
        "min_bots": game.min_bots,
        "max_bots": game.max_bots,
        "min_players": low,
        "max_players": high,
        "available": game.available,
        "options": describe_options(game.options) if game.options else [],
    }


def describe_partida(partida: Partida) -> dict[str, Any]:
    return {
        "game": partida.game,
        "partida_id": partida.id,
        "in_progress": partida.session.in_progress,
    }


def game_routes(store: AccountStore, partidas: Partidas, make_session: MakeSession) -> APIRouter:
    router = APIRouter(prefix="/api")

    def failure(status: int, message: str) -> JSONResponse:
        return JSONResponse({"message": message}, status_code=status)

    @router.get("/juegos")
    def games() -> list[dict[str, Any]]:
        return [describe_game(game) for game in REGISTRY]

    @router.get("/partidas")
    def my_partidas(request: Request, guest_id: str = "") -> dict[str, Any]:
        user = store.user_for_token(request.cookies.get(SESSION_COOKIE))
        owner = owner_key(user, guest_id)
        mine = partidas.of_owner(owner) if owner else []
        return {"partidas": [describe_partida(partida) for partida in mine]}

    @router.post("/partidas")
    def open_partida(request: Request, body: PartidaRequest) -> JSONResponse:
        if not same_origin(request.headers):
            return failure(403, "Petición rechazada")
        game = find_game(body.game)
        if game is None:
            return failure(404, "Ese juego no existe")
        if not game.available:
            return failure(409, "Ese juego todavía no está disponible")
        user = store.user_for_token(request.cookies.get(SESSION_COOKIE))
        owner = owner_key(user, body.guest_id)
        if owner is None:
            return failure(400, "Identificador de invitado inválido")
        partida = partidas.open(
            owner, game.id, lambda partida_id: make_session(game, owner, partida_id, user)
        )
        return JSONResponse(describe_partida(partida))

    return router
