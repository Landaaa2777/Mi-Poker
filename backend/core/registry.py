"""La ficha de un juego en el registro de la plataforma.

Cada juego describe aquí quién es y cómo se crea su partida. El registro (la
lista de fichas) está en `games/registry.py`, y el menú principal se construye
leyéndolo: añadir un juego es añadir una ficha, sin tocar el menú.

Ejemplo:

    GAME = GameInfo(
        id="blackjack",
        name="Blackjack",
        description="Suma 21 sin pasarte y gánale al crupier.",
        min_bots=0,
        max_bots=4,
        options=BlackjackConfig,   # el modelo con las opciones configurables
        create=create_session,     # crea la partida en el servidor
        room_options=RoomConfig,   # las opciones de una sala con amigos
    )
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GameInfo:
    """Un juego del menú. Sin `create`, se enseña como "Próximamente"."""

    id: str  # también es su ruta en la web: /poker, /blackjack…
    name: str
    description: str  # una línea para la tarjeta del menú
    min_bots: int = 0
    max_bots: int = 0
    # Modelo (pydantic) con las opciones que se eligen antes de empezar. El
    # servidor valida con él lo que manda el cliente, y de él sale el panel.
    options: type | None = None
    # Crea la partida de una persona. Recibe un `SessionContext`.
    create: Callable[[Any], Any] | None = None
    # Modelo con las opciones de una sala con amigos (las elige el anfitrión).
    # Sin él, el juego no se puede jugar en salas.
    room_options: type | None = None

    @property
    def available(self) -> bool:
        """¿Se puede jugar ya, o todavía es "Próximamente"?"""
        return self.create is not None

    @property
    def players(self) -> tuple[int, int]:
        """Cuántas personas hay en la mesa: el humano más los bots."""
        return 1 + self.min_bots, 1 + self.max_bots
