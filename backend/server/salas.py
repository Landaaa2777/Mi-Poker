"""Salas privadas: partidas en línea con otras personas.

Quien crea la sala (el anfitrión) elige el juego y sus opciones, y recibe un
código corto, por ejemplo `K7P2QX`. Los demás entran con el código o abriendo
el enlace `/sala/K7P2QX`. Mientras se espera, todos ven en tiempo real quién
está; el anfitrión decide las opciones y cuándo se empieza.

Cuando el anfitrión empieza, la sala crea la partida del juego (`create_room`
de su ficha), con todas las personas sentadas. Al terminar, la sala vuelve a
la espera y se puede jugar otra.

Cada persona está como mucho en una sala. Desconectarse no es salir: el sitio
se guarda y se puede volver con el mismo enlace. Salir con la partida empezada
es abandonarla, con las consecuencias de cada juego, y ya no se puede volver a
ella. Una sala en la que no queda nadie conectado se cierra sola al cabo de un
rato.

Todo vive en memoria, como las partidas contra bots: al apagar el servidor, las
salas desaparecen. Este módulo no sabe nada de FastAPI.
"""

from __future__ import annotations

import asyncio
import re
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from accounts import User
from core.options import describe_options
from core.registry import GameInfo
from core.room import RoomSession

# Sin 0, O, 1, I ni L: no se confunden al leerlos o dictarlos.
CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CODE_LENGTH = 6  # 31^6: casi 900 millones de códigos posibles
MIN_PEOPLE = 2  # una sala es para jugar con alguien
MAX_SALAS = 200
IDLE_SECONDS = 30 * 60  # sin nadie conectado durante este rato, la sala se cierra

_CODE = re.compile(f"[{CODE_ALPHABET}]{{{CODE_LENGTH}}}")


class SalaError(Exception):
    """No se puede hacer lo que se pide; el mensaje es para mostrarlo."""


class SalaNotFound(SalaError):
    pass


class SalaStatus(StrEnum):
    WAITING = "waiting"  # en la sala de espera
    PLAYING = "playing"  # la partida ha empezado


def normalize_code(text: str) -> str | None:
    """El código tal como se guarda, o None si no puede ser un código.

    Se aceptan minúsculas, espacios y guiones: " k7p-2qx " es "K7P2QX".
    """
    code = re.sub(r"[\s-]", "", text).upper()
    return code if _CODE.fullmatch(code) else None


def new_code(taken: Callable[[str], bool]) -> str:
    """Un código al azar que no esté en uso."""
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if not taken(code):
            return code


# Le manda a una conexión lo que ve ahora mismo (de la sala, o de la partida).
Push = Callable[[], Awaitable[None]]
# Cierra una conexión, con su código y su motivo.
Close = Callable[[int, str], Awaitable[None]]
# Crea la partida de una sala; si no se puede (por ejemplo, alguien no tiene
# fichas suficientes), lanza `SalaError`.
MakeRoom = Callable[["Sala"], RoomSession]

LEFT = 4000  # código de cierre: has salido de la sala (o se ha cerrado)


@dataclass(eq=False)
class Viewer:
    """Una conexión abierta a la sala: de quién es y cómo se le avisa."""

    user_id: int
    push: Push  # lo que ve de la sala
    push_state: Push  # lo que ve de la partida
    close: Close


@dataclass
class Member:
    user: User
    joined_at: float


@dataclass(eq=False)
class Sala:
    """Una sala: su juego, sus opciones, quién está y quién la lleva."""

    code: str
    game: GameInfo
    host_id: int
    options: BaseModel
    members: dict[int, Member] = field(default_factory=dict)  # por id, en orden de llegada
    status: SalaStatus = SalaStatus.WAITING
    session: RoomSession | None = None  # la partida en curso, o la última que se jugó
    viewers: list[Viewer] = field(default_factory=list)
    idle_since: float | None = None  # desde cuándo no hay nadie conectado

    @property
    def max_people(self) -> int:
        return self.game.players[1]

    def connected(self, user_id: int) -> bool:
        return any(viewer.user_id == user_id for viewer in self.viewers)

    # --- Opciones ---

    def configure(self, user_id: int, game: GameInfo, options: dict[str, Any]) -> None:
        """El anfitrión cambia el juego o sus opciones antes de empezar."""
        if user_id != self.host_id:
            raise SalaError("Solo el anfitrión puede cambiar las opciones")
        if self.status != SalaStatus.WAITING:
            raise SalaError("La partida ya ha empezado")
        if game.room_options is None:
            raise SalaError("Ese juego no se puede jugar en una sala")
        if len(self.members) > game.players[1]:
            raise SalaError(f"En {game.name} caben como mucho {game.players[1]} personas")
        chosen = game.room_options.model_validate(options)  # salta si no valen
        room_for_bots = game.players[1] - len(self.members)
        if chosen.bots > room_for_bots:
            raise SalaError(f"Con {len(self.members)} personas caben como mucho {room_for_bots} bots")
        self.game = game
        self.options = chosen

    def _fit_bots(self) -> None:
        """Las personas tienen preferencia: si al entrar alguien no caben los bots, sobran bots."""
        room_for_bots = self.max_people - len(self.members)
        if self.options.bots > room_for_bots:
            self.options = self.options.model_copy(update={"bots": room_for_bots})

    # --- Avisos ---

    def describe(self, viewer_id: int) -> dict[str, Any]:
        """Lo que ve de la sala uno de sus miembros. Solo nombres: nada de cuentas ni correos."""
        host = self.members[self.host_id].user.username if self.host_id in self.members else None
        return {
            "code": self.code,
            "game": self.game.id,
            "game_name": self.game.name,
            "status": self.status.value,
            "you": self.members[viewer_id].user.username if viewer_id in self.members else None,
            "host": host,
            "members": [
                {
                    "name": member.user.username,
                    "connected": self.connected(member.user.id),
                    "host": member.user.id == self.host_id,
                }
                for member in self.members.values()
            ],
            "min_people": MIN_PEOPLE,
            "max_people": self.max_people,
            "options": self.options.model_dump(exclude={"player_name"}),
            "fields": describe_options(type(self.options)),
            "can_start": self.status == SalaStatus.WAITING and len(self.members) >= MIN_PEOPLE,
            # Ya se jugó una partida: su mesa final se sigue viendo hasta la siguiente.
            "game_over": self.session is not None and self.session.finished,
        }

    async def broadcast(self) -> None:
        """Cada conexión recibe lo que ve de la sala. Una conexión que falla no frena a las demás."""
        await asyncio.gather(*(viewer.push() for viewer in list(self.viewers)))

    async def broadcast_state(self) -> None:
        """Cada conexión recibe lo que ve de la partida. Si ha terminado, la sala vuelve a la espera."""
        await asyncio.gather(*(viewer.push_state() for viewer in list(self.viewers)))
        if self.status == SalaStatus.PLAYING and self.session is not None and self.session.finished:
            self.status = SalaStatus.WAITING
            await self.broadcast()

    async def close_viewers(self, user_id: int | None, reason: str) -> None:
        """Cierra las conexiones de una persona (o de todas, con None)."""
        leaving = [v for v in self.viewers if user_id is None or v.user_id == user_id]
        self.viewers = [v for v in self.viewers if v not in leaving]
        for viewer in leaving:
            await viewer.close(LEFT, reason)


class Salas:
    """Todas las salas abiertas del servidor."""

    def __init__(self, limit: int = MAX_SALAS, clock: Callable[[], float] = time.monotonic) -> None:
        self.limit = limit
        self.clock = clock
        self._by_code: dict[str, Sala] = {}

    def __len__(self) -> int:
        return len(self._by_code)

    def get(self, text: str) -> Sala | None:
        code = normalize_code(text)
        return self._by_code.get(code) if code else None

    def of_user(self, user_id: int) -> Sala | None:
        """La sala en la que está una persona, si está en alguna."""
        return next((sala for sala in self._by_code.values() if user_id in sala.members), None)

    def seated_chips(self, user_id: int) -> int:
        """Fichas de su cuenta sentadas en partidas de salas.

        Se mira en todas, no solo en la suya: quien acaba de irse puede tener
        aún fichas en juego en la mano que se termina sin él.
        """
        return sum(
            sala.session.seated_chips(user_id)
            for sala in self._by_code.values()
            if sala.session is not None
        )

    async def create(self, game: GameInfo, host: User) -> Sala:
        """Una sala nueva con `host` de anfitrión. Si estaba esperando en otra, sale de ella."""
        if game.room_options is None:
            raise SalaError("Ese juego no se puede jugar en una sala")
        await self._leave_waiting_room(host)
        self.sweep()
        if len(self._by_code) >= self.limit:
            raise SalaError("Hay demasiadas salas abiertas. Prueba otra vez en un rato.")
        code = new_code(lambda candidate: candidate in self._by_code)
        now = self.clock()
        sala = Sala(code, game, host.id, game.room_options(), idle_since=now)
        sala.members[host.id] = Member(host, now)
        self._by_code[code] = sala
        return sala

    async def join(self, text: str, user: User) -> Sala:
        """Entra en una sala con su código. Quien ya es miembro vuelve a su sitio."""
        self.sweep()
        sala = self.get(text)
        if sala is None:
            raise SalaNotFound("No hay ninguna sala con ese código")
        if user.id in sala.members:
            return sala  # vuelve: el sitio era suyo
        if sala.status != SalaStatus.WAITING:
            raise SalaError("La partida de esta sala ya ha empezado")
        if len(sala.members) >= sala.max_people:
            raise SalaError("La sala está llena")
        await self._leave_waiting_room(user)
        sala.members[user.id] = Member(user, self.clock())
        sala._fit_bots()
        await sala.broadcast()
        return sala

    async def start(self, sala: Sala, user_id: int, make_room: MakeRoom) -> None:
        """El anfitrión empieza la partida, con todas las personas de la sala sentadas."""
        if user_id != sala.host_id:
            raise SalaError("Solo el anfitrión puede empezar la partida")
        if sala.status != SalaStatus.WAITING:
            raise SalaError("La partida ya ha empezado")
        if len(sala.members) < MIN_PEOPLE:
            raise SalaError("Hacen falta al menos dos personas para empezar")
        if sala.game.create_room is None:
            raise SalaError("Ese juego no se puede jugar en una sala")
        session = make_room(sala)  # salta con SalaError si alguien no puede sentarse
        if sala.session is not None:
            sala.session.close()  # la partida anterior, ya terminada
        session.listener = sala.broadcast_state
        sala.session = session
        sala.status = SalaStatus.PLAYING
        await sala.broadcast()
        session.start()

    async def leave(self, sala: Sala, user_id: int) -> None:
        """Sale de la sala. Si era el anfitrión, lo pasa a ser quien llegó antes.

        Con la partida empezada, salir es abandonarla: cada juego decide qué pasa
        con su sitio, y ya no se puede volver a ella.
        """
        if user_id not in sala.members:
            return
        if sala.status == SalaStatus.PLAYING and sala.session is not None:
            sala.session.abandon(user_id)
        del sala.members[user_id]
        await sala.close_viewers(user_id, "Has salido de la sala")
        if not sala.members:
            await self.close(sala, "La sala se ha cerrado")
            return
        if sala.host_id == user_id:
            sala.host_id = next(iter(sala.members))
        await sala.broadcast()

    async def close(self, sala: Sala, reason: str) -> None:
        self._by_code.pop(sala.code, None)
        if sala.session is not None:
            sala.session.close()
        await sala.close_viewers(None, reason)

    def connect(self, sala: Sala, viewer: Viewer) -> None:
        sala.viewers.append(viewer)
        sala.idle_since = None

    def disconnect(self, sala: Sala, viewer: Viewer) -> None:
        if viewer in sala.viewers:
            sala.viewers.remove(viewer)
        if not sala.viewers:
            sala.idle_since = self.clock()

    def sweep(self) -> None:
        """Cierra las salas en las que hace rato que no hay nadie conectado."""
        now = self.clock()
        for code, sala in list(self._by_code.items()):
            if not sala.viewers and sala.idle_since is not None and now - sala.idle_since > IDLE_SECONDS:
                del self._by_code[code]
                if sala.session is not None:
                    sala.session.close()

    async def _leave_waiting_room(self, user: User) -> None:
        """Cada persona está en una sola sala: para entrar en otra, sale de la que esperaba."""
        current = self.of_user(user.id)
        if current is None:
            return
        if current.status != SalaStatus.WAITING:
            raise SalaError(f"Ya estás jugando en la sala {current.code}")
        await self.leave(current, user.id)
