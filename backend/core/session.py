"""Lo que el servidor espera de la partida de cualquier juego.

El servidor no sabe jugar a nada: guarda las partidas, las conecta con el
navegador y les pasa los mensajes. Cada juego trae su propia partida
(`games/<juego>/session.py`), que cumple este contrato.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from .bots import BOT_DELAY

# Se llama cada vez que cambia el estado de la partida, para enviárselo al jugador.
Listener = Callable[[], Awaitable[None]]


class SessionError(Exception):
    """La intención del cliente no se puede cumplir; el mensaje es para mostrarlo."""


class TableAccount(Protocol):
    """Lo que una partida con fichas necesita de la cuenta del jugador.

    Un invitado no tiene cuenta: sus fichas solo existen en la partida.
    """

    def balance(self) -> int:
        """Fichas de la cuenta, contando las que tiene en todas sus mesas."""
        ...

    def chips_elsewhere(self) -> int:
        """Fichas sentadas en sus otras mesas: no se pueden llevar a esta."""
        ...

    def add_chips(self, chips: int) -> None:
        """Suma al saldo lo ganado en una ronda, o resta lo perdido si es negativo."""
        ...


@dataclass
class SessionContext:
    """Lo que el servidor le da a la partida de un juego al crearla."""

    account: Any = None  # la cuenta del jugador (un `TableAccount`), o None si es invitado
    player_name: str | None = None  # con cuenta, su nombre: lo pone el servidor
    bot_delay: tuple[float, float] = BOT_DELAY
    simulations: int | None = None  # solo poker: cuántas simulaciones hacen sus bots


class GameSession(Protocol):
    """La partida de un juego, en memoria, tal como la usa el servidor."""

    listener: Listener | None  # el servidor lo pone para enterarse de cada cambio

    def options(self) -> dict[str, Any]:
        """Opciones y límites para el panel de configuración (van en el "hello")."""
        ...

    def state(self) -> dict[str, Any] | None:
        """Lo que ve el jugador ahora mismo; None si aún no hay partida."""
        ...

    def handle(self, text: str) -> None:
        """Valida y aplica una intención del cliente, recibida como texto JSON.

        Si no se puede, lanza `SessionError` (o un error de validación) y la
        partida queda como estaba.
        """
        ...

    @property
    def in_progress(self) -> bool:
        """¿Hay una partida empezada que todavía no ha terminado?"""
        ...

    def seated_chips(self) -> int:
        """Fichas de la cuenta que hay sentadas en esta mesa (0 si no usa fichas)."""
        ...

    def close(self) -> None:
        """La partida se descarta: que los bots dejen de jugar."""
        ...
