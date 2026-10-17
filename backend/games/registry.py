"""Registro de juegos: la lista que ve el menú principal (GET /api/juegos).

Añadir un juego es escribir su carpeta en `games/` y añadir aquí su ficha. Los
que todavía no se pueden jugar salen en el menú como "Próximamente".
"""

from __future__ import annotations

from core.registry import GameInfo

from .poker.info import GAME as POKER

COMING_SOON = (
    GameInfo(
        id="blackjack",
        name="Blackjack",
        description="Suma 21 sin pasarte y gánale al crupier.",
        min_bots=0,
        max_bots=4,
    ),
    GameInfo(
        id="prisma",
        name="Prisma",
        description="Suelta todas tus cartas antes que nadie: color, número o comodín.",
        min_bots=1,
        max_bots=5,
    ),
    GameInfo(
        id="minijuegos",
        name="Minijuegos",
        description="Juegos rápidos para ganar fichas.",
    ),
    GameInfo(
        id="salas",
        name="Salas con amigos",
        description="Partidas en línea con otras personas.",
    ),
)

# El orden es el del menú: primero los que se pueden jugar.
REGISTRY: tuple[GameInfo, ...] = (POKER, *COMING_SOON)


def find_game(game_id: str) -> GameInfo | None:
    """La ficha del juego con ese id, o None si no existe."""
    return next((game for game in REGISTRY if game.id == game_id), None)
