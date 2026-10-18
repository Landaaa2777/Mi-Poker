"""Aplicación FastAPI: el menú de juegos, un WebSocket por partida, las salas, las cuentas y la web.

    uvicorn server.app:app --reload

El servidor no sabe jugar a nada en concreto: cada juego trae su partida
(`games/<juego>/session.py`) y aquí solo se guardan, se conectan con el
navegador y se les pasan los mensajes.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import Scope

from accounts import DEFAULT_COST, AccountStore, Cost, HandOutcome, Throttle, User
from core import NOTICE
from core.bots import BOT_DELAY
from core.registry import GameInfo
from core.room import PAUSE_SECONDS, TURN_SECONDS, Person, RoomContext, RoomSession
from core.session import GameSession, SessionContext, SessionError

from .accounts_api import SESSION_COOKIE, account_routes, public_user, same_origin
from .connections import Connections
from .games_api import game_routes
from .partidas import Partidas, owner_key
from .salas import Sala, SalaError, Salas
from .salas_api import sala_routes
from .validation import MAX_MESSAGE, TOO_LONG, explain

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND_DIST = BACKEND.parent / "frontend" / "dist"
# Base de datos de cuentas. Se puede llevar a otro sitio con MI_POKER_DB.
DATABASE = Path(os.environ.get("MI_POKER_DB") or BACKEND / "data" / "mi-poker.db")

log = logging.getLogger("mi-poker")


class SinglePageApp(StaticFiles):
    """Sirve la web compilada.

    Las direcciones de la web (/poker, /blackjack…) no son archivos: para ellas
    se devuelve index.html y es la web quien decide qué enseñar. Así una página
    recargada o un enlace guardado siguen funcionando. Lo que parece un archivo
    (lleva extensión) o es de la API y no existe sigue dando 404.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            # En Windows la ruta llega con "\\": se normaliza antes de mirarla.
            parts = path.replace("\\", "/").split("/")
            if error.status_code != 404 or "." in parts[-1] or parts[0] in ("api", "ws"):
                raise
            return await super().get_response("index.html", scope)


class AccountAtTable:
    """La cuenta de un jugador vista desde una de sus mesas: su saldo y dónde apuntar cada mano.

    `elsewhere` dice cuántas fichas tiene sentadas en sus otras mesas (contra
    bots o en una sala). Una partida no se estropea porque falle la base de
    datos: el fallo se anota en el registro del servidor y la mano sigue.
    """

    def __init__(self, store: AccountStore, user: User, elsewhere: Callable[[], int]) -> None:
        self.store = store
        self.user = user
        self._elsewhere = elsewhere
        self._last_balance = 0

    def balance(self) -> int:
        try:
            self._last_balance = self.store.balance(self.user)
        except Exception:
            log.exception("No se pudo leer el saldo")
        return self._last_balance

    def chips_elsewhere(self) -> int:
        """Fichas sentadas en las otras mesas de la cuenta: no se pueden traer a esta."""
        return self._elsewhere()

    def add_chips(self, chips: int) -> None:
        try:
            self.store.add_chips(self.user, chips)
        except Exception:
            log.exception("No se pudo apuntar el resultado en el saldo")

    def hand_finished(self, outcome: HandOutcome) -> None:
        try:
            self.store.record_hand(self.user, outcome)
        except Exception:
            log.exception("No se pudo guardar el resultado de una mano")

    def hand_abandoned(self, chips: int) -> None:
        try:
            self.store.add_chips(self.user, -chips)
        except Exception:
            log.exception("No se pudo descontar una mano dejada a medias")


def create_app(
    bot_delay: tuple[float, float] = BOT_DELAY,
    simulations: int | None = None,
    serve_frontend: bool = True,
    database: Path | str = DATABASE,
    password_cost: Cost = DEFAULT_COST,
    frontend_dist: Path = FRONTEND_DIST,
    require_account: bool = True,
    turn_seconds: float = TURN_SECONDS,
    pause_seconds: float = PAUSE_SECONDS,
) -> FastAPI:
    """La aplicación. `require_account` en falso deja jugar como invitado (solo
    para desarrollo y tests: el juego de verdad exige cuenta). `turn_seconds` y
    `pause_seconds` son el tiempo por decisión y la pausa entre manos de las
    salas; los tests los acortan."""
    app = FastAPI(title="mi-poker", description=NOTICE)
    # Partidas en memoria, una por identidad y juego. No se guardan en disco.
    partidas = Partidas()
    app.state.partidas = partidas
    accounts = AccountStore(database, password_cost)
    app.state.accounts = accounts
    # Salas con amigos, también en memoria.
    salas = Salas()
    app.state.salas = salas
    # Conexiones abiertas de cada sesión iniciada, para cortarlas al cerrarla.
    connections = Connections()
    app.state.connections = connections

    def elsewhere(user: User, owner: str, partida_id: str = "") -> int:
        """Fichas de una cuenta sentadas en sus mesas contra bots (menos `partida_id`) y en salas."""
        return partidas.chips_elsewhere(owner, partida_id) + salas.seated_chips(user.id)

    def make_session(game: GameInfo, owner: str, partida_id: str, user: User | None) -> GameSession:
        """La partida nueva de un juego, con la cuenta de su dueño si la tiene."""
        assert game.create is not None
        account = (
            AccountAtTable(accounts, user, lambda: elsewhere(user, owner, partida_id))
            if user
            else None
        )
        context = SessionContext(
            account=account,
            player_name=user.username if user else None,
            bot_delay=bot_delay,
            simulations=simulations,
        )
        return game.create(context)

    app.include_router(account_routes(accounts, Throttle(), connections.close_session))
    app.include_router(game_routes(accounts, partidas, make_session, require_account))
    def make_room(sala: Sala) -> RoomSession:
        """La partida de una sala, con todas sus personas sentadas.

        En los juegos con fichas, cada persona lleva a la mesa las fichas
        iniciales desde su saldo: si a alguien no le llegan, no se empieza.
        """
        assert sala.game.create_room is not None
        stake = getattr(sala.options, "starting_stack", 0)  # los juegos con fichas lo tienen
        people = []
        for member in sala.members.values():
            user = member.user
            owner = owner_key(user, None)
            assert owner is not None
            # Al sentarse en la sala, solo cuentan como "en otra mesa" las de sus partidas contra bots.
            account = AccountAtTable(
                accounts, user, lambda owner=owner: partidas.chips_elsewhere(owner, "")
            )
            if stake:
                free = account.balance() - account.chips_elsewhere()
                if free < stake:
                    raise SalaError(
                        f"A {user.username} no le llegan las fichas: tiene {free} libres"
                        f" y la mesa pide {stake}"
                    )
            people.append(Person(user.id, user.username, account))
        context = RoomContext(
            people=tuple(people),
            options=sala.options,
            bot_delay=bot_delay,
            simulations=simulations,
            turn_seconds=turn_seconds,
            pause_seconds=pause_seconds,
        )
        return sala.game.create_room(context)

    app.include_router(sala_routes(accounts, salas, connections, make_room))

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "notice": NOTICE}

    @app.websocket("/ws/{game_id}/{partida_id}")
    async def play(websocket: WebSocket, game_id: str, partida_id: str, guest_id: str = "") -> None:
        if not same_origin(websocket.headers):
            await websocket.close(code=4403, reason="Origen no permitido")
            return
        token = websocket.cookies.get(SESSION_COOKIE)
        user = await asyncio.to_thread(accounts.user_for_token, token)
        if user is None and require_account:
            await websocket.close(code=4401, reason="Entra en tu cuenta para jugar")
            return
        owner = owner_key(user, guest_id)
        if owner is None:
            await websocket.close(code=4400, reason="Identificador de invitado inválido")
            return
        partida = partidas.get(partida_id)
        # Solo su dueño puede jugar una partida, y solo a su juego.
        if partida is None or partida.owner != owner or partida.game != game_id:
            await websocket.close(code=4404, reason="Partida no encontrada")
            return
        await websocket.accept()
        if user is not None:
            connections.add(token, websocket)

        session = partida.session
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
                "game": game_id,
                "options": session.options(),
                "user": await asyncio.to_thread(public_user, accounts, user),
                # Con cuenta, fichas sentadas en sus otras mesas: no se pueden traer a esta.
                "elsewhere": elsewhere(user, owner, partida_id) if user else 0,
                "state": session.state(),
            }
        )

        try:
            while True:
                text = await websocket.receive_text()
                if len(text) > MAX_MESSAGE:
                    await send({"type": "error", "message": TOO_LONG})
                    continue
                try:
                    session.handle(text)
                except ValidationError as error:
                    await send({"type": "error", "message": explain(error)})
                except SessionError as error:
                    await send({"type": "error", "message": str(error)})
                else:
                    await send_state()
        except WebSocketDisconnect:
            if session.listener is send_state:
                session.listener = None
        finally:
            connections.discard(token, websocket)

    if serve_frontend and frontend_dist.is_dir():
        app.mount("/", SinglePageApp(directory=frontend_dist, html=True), name="frontend")
    return app


app = create_app()
