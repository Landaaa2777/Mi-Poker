"""Estadísticas de juego de una cuenta. Se llevan aparte por nivel de los rivales."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class HandOutcome:
    """Cómo le fue al jugador en una mano que ha terminado."""

    difficulty: str  # nivel de los bots de la partida
    chips_won: int = 0  # lo que cobró de los botes; 0 si no ganó ninguno
    chips_delta: int = 0  # cuánto cambiaron sus fichas en la mano: cobrado menos apostado
    best_hand: int | None = None  # categoría de la mano que enseñó, si llegó al showdown
    first_hand: bool = False  # era la primera mano de la partida
    game_won: bool = False  # con esta mano dejó sin fichas al último rival


@dataclass(frozen=True)
class LevelStats:
    """Lo acumulado contra un nivel de bots (o contra todos, si `difficulty` va vacío)."""

    difficulty: str = ""
    hands_played: int = 0
    hands_won: int = 0
    biggest_win: int = 0  # lo máximo cobrado en una sola mano
    best_hand: int | None = None  # la mejor categoría enseñada en un showdown
    games_played: int = 0
    games_won: int = 0


def total(levels: Iterable[LevelStats]) -> LevelStats:
    """Todas las partidas juntas, sin distinguir nivel."""
    levels = list(levels)
    shown = [level.best_hand for level in levels if level.best_hand is not None]
    return LevelStats(
        hands_played=sum(level.hands_played for level in levels),
        hands_won=sum(level.hands_won for level in levels),
        biggest_win=max((level.biggest_win for level in levels), default=0),
        best_hand=max(shown, default=None),
        games_played=sum(level.games_played for level in levels),
        games_won=sum(level.games_won for level in levels),
    )
