"""Registro de juegos: la lista que ve el menú principal (GET /api/juegos).

Añadir un juego es escribir su carpeta en `games/` y añadir aquí su ficha. Los
que todavía no se pueden jugar salen en el menú como "Próximamente".
"""

from __future__ import annotations

from core.registry import GameInfo

from .blackjack.info import GAME as BLACKJACK
from .poker.info import GAME as POKER
from .prisma.info import GAME as PRISMA

# Juegos que se enseñan como "Próximamente" (una ficha sin `create`). Ahora no
# hay ninguno: las salas con amigos ya existen y tienen su propia tarjeta.
COMING_SOON: tuple[GameInfo, ...] = ()

# El orden es el del menú: primero los que se pueden jugar.
REGISTRY: tuple[GameInfo, ...] = (POKER, BLACKJACK, PRISMA, *COMING_SOON)


def find_game(game_id: str) -> GameInfo | None:
    """La ficha del juego con ese id, o None si no existe."""
    return next((game for game in REGISTRY if game.id == game_id), None)
