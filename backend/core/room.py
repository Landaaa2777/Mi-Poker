"""Partidas con varias personas: lo común a las mesas de las salas.

En una sala, la partida tiene varias personas además de los bots:

- Cada una ve solo lo suyo (su vista de la mesa), nunca las cartas de las demás.
- Cada decisión tiene un tiempo (30 segundos). Si se acaba, el servidor juega
  por esa persona lo más prudente, y la partida sigue.
- Desconectarse no es irse: su sitio se guarda y el tiempo corre como siempre.
- Irse (salir de la sala) es abandonar, con las consecuencias de cada juego.

Cada juego escribe su mesa (`games/<juego>/room.py`) a partir de `RoomTable`,
que pone las personas, la cuenta atrás y el bucle que hace jugar a cada uno.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from .bots import BOT_DELAY
from .session import Listener, SessionError

TURN_SECONDS = 30.0  # tiempo para cada decisión
PAUSE_SECONDS = 6.0  # pausa entre una mano (o ronda) y la siguiente, para ver cómo acabó
ROOM_LEVEL = "friends"  # en las estadísticas del poker, las manos jugadas en salas

log = logging.getLogger("mi-poker")


@dataclass(frozen=True)
class Person:
    """Una persona sentada en la partida de una sala."""

    user_id: int
    name: str  # el de su cuenta: es su nombre en la mesa
    account: Any = None  # su cuenta en esta mesa (ver `core.session.TableAccount`)


@dataclass
class RoomContext:
    """Lo que el servidor le da a la mesa de una sala al crearla."""

    people: tuple[Person, ...]  # en el orden en que llegaron a la sala
    options: Any  # el `RoomConfig` del juego, tal como lo dejó el anfitrión
    bot_delay: tuple[float, float] = BOT_DELAY
    simulations: int | None = None  # solo poker: cuántas simulaciones hacen sus bots
    turn_seconds: float = TURN_SECONDS
    pause_seconds: float = PAUSE_SECONDS


class RoomSession(Protocol):
    """La partida de una sala, tal como la usa el servidor."""

    listener: Listener | None  # el servidor lo pone para enterarse de cada cambio
    finished: bool  # la partida terminó: la sala vuelve a la espera

    def state(self, user_id: int) -> dict[str, Any] | None:
        """Lo que ve una persona: la mesa pública y lo suyo."""
        ...

    def handle(self, user_id: int, text: str) -> None:
        """Valida y aplica una intención de una persona (texto JSON).

        Si no se puede, lanza `SessionError` (o un error de validación).
        """
        ...

    def abandon(self, user_id: int) -> None:
        """La persona se va de la partida para siempre."""
        ...

    def seated_chips(self, user_id: int) -> int:
        """Fichas de su cuenta que tiene sentadas en esta mesa (0 si no usa fichas)."""
        ...

    def close(self) -> None:
        """La partida se descarta: que nadie siga jugando."""
        ...


class TurnTimer:
    """La cuenta atrás de la decisión en curso: de quién es y cuánto le queda.

    `seat` es el asiento que tiene que decidir, o None cuando la cuenta atrás es
    de todos a la vez (por ejemplo, las apuestas del blackjack).
    """

    def __init__(self, seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.seconds = seconds
        self.clock = clock
        self.running = False
        self.seat: int | None = None
        self._ends_at = 0.0

    def start(self, seat: int | None) -> None:
        self.running = True
        self.seat = seat
        self._ends_at = self.clock() + self.seconds

    def stop(self) -> None:
        self.running = False
        self.seat = None

    def left(self) -> float:
        return max(0.0, self._ends_at - self.clock()) if self.running else 0.0

    def describe(self) -> dict[str, Any] | None:
        """Para el cliente: de quién es el turno y cuántos segundos le quedan."""
        if not self.running:
            return None
        return {"seat": self.seat, "left": round(self.left(), 1), "total": self.seconds}


class RoomTable:
    """Base de las mesas de las salas: personas, asientos, cuenta atrás y avisos.

    Cada juego pone su lógica en `_step`, que se llama una y otra vez hasta que
    la partida termina: en cada vuelta mira a quién le toca y le hace jugar
    (un bot piensa y juega; una persona tiene su tiempo).
    """

    def __init__(self, context: RoomContext) -> None:
        self.context = context
        self.options = context.options
        # Las personas se sientan primero, en el orden en que llegaron a la sala.
        self.person_at: dict[int, Person] = dict(enumerate(context.people))
        self.seat_of: dict[int, int] = {person.user_id: seat for seat, person in self.person_at.items()}
        self.gone: set[int] = set()  # asientos de personas que se han ido
        self.listener: Listener | None = None
        self.finished = False
        self.timer = TurnTimer(context.turn_seconds)
        self.pause_until: float | None = None  # hasta cuándo dura la pausa entre manos
        self._wake = asyncio.Event()
        self._runner: asyncio.Task | None = None

    # --- Para el servidor ---

    def start(self) -> None:
        """Empieza a jugar. Hay que llamarlo desde el bucle de eventos del servidor."""
        self._runner = asyncio.get_running_loop().create_task(self._run())

    def close(self) -> None:
        if self._runner is not None:
            self._runner.cancel()
            self._runner = None

    def seat(self, user_id: int) -> int:
        """El asiento de una persona que sigue en la partida."""
        seat = self.seat_of.get(user_id)
        if seat is None or seat in self.gone:
            raise SessionError("Ya no estás en esta partida")
        return seat

    def abandon(self, user_id: int) -> None:
        seat = self.seat_of.get(user_id)
        if seat is None or seat in self.gone:
            return
        self.gone.add(seat)
        self._on_abandon(seat)
        if self.timer.running and self.timer.seat == seat:
            self.timer.stop()  # quien se va no gasta su tiempo: se juega por él ya
        self.wake()

    def wake(self) -> None:
        """Algo ha cambiado (una persona ha jugado o se ha ido): el bucle vuelve a mirar."""
        self._wake.set()

    # --- Para cada juego ---

    async def _step(self) -> None:
        raise NotImplementedError

    def _on_abandon(self, seat: int) -> None:
        """Lo que cada juego hace en el momento en que alguien se va."""

    def is_person(self, seat: int) -> bool:
        return seat in self.person_at

    def plays_for_itself(self, seat: int) -> bool:
        """¿Decide este asiento una persona que sigue en la partida?"""
        return seat in self.person_at and seat not in self.gone

    async def _wait_for(self, seat: int | None) -> bool:
        """Espera a que decida `seat` (o todos, con None). Devuelve True si se acabó el tiempo.

        La cuenta atrás empieza la primera vez que se espera esa decisión y sigue
        corriendo aunque el bucle vuelva a mirar (por ejemplo, porque otro dijo
        "¡Última!"). Cuando la persona juega, el juego para la cuenta atrás y la
        siguiente decisión tiene su tiempo entero.
        """
        # Se borra antes de avisar: si alguien juega mientras se avisa, no se pierde.
        self._wake.clear()
        if not self.timer.running or self.timer.seat != seat:
            self.timer.start(seat)
            await self._notify()  # todos ven que empieza su cuenta atrás
        if self._wake.is_set():
            return False
        try:
            await asyncio.wait_for(self._wake.wait(), timeout=self.timer.left())
        except TimeoutError:
            self.timer.stop()
            return True
        return False

    async def _idle(self) -> None:
        """Espera, sin cuenta atrás, a que alguien haga algo (por ejemplo, la primera apuesta)."""
        self._wake.clear()
        if self.timer.running:
            self.timer.stop()
            await self._notify()
        if not self._wake.is_set():
            await self._wake.wait()

    async def _pause(self) -> None:
        """La pausa entre manos o rondas, para que todos vean cómo acabó."""
        seconds = self.context.pause_seconds
        self.pause_until = time.monotonic() + seconds
        await self._notify()
        await asyncio.sleep(seconds)
        self.pause_until = None

    def pause_left(self) -> float | None:
        if self.pause_until is None:
            return None
        return round(max(0.0, self.pause_until - time.monotonic()), 1)

    async def _notify(self) -> None:
        if self.listener is not None:
            await self.listener()

    async def _run(self) -> None:
        try:
            await self._notify()
            while not self.finished:
                await self._step()
        except Exception:
            # Un fallo no puede dejar a todos esperando: la partida se da por
            # terminada y la sala vuelve a la espera.
            log.exception("La partida de una sala se ha roto")
            self.finished = True
        self.timer.stop()
        await self._notify()
