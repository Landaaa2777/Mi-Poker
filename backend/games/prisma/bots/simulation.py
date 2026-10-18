"""Partidas bot contra bot de Prisma para medir la fuerza de cada nivel.

Cada partida es una ronda entre bots de distintos niveles. Los asientos rotan
de una partida a otra, para que ninguno tenga siempre la ventaja de empezar.
Tras cada jugada, los demás pueden pillar a quien se quedó con una carta sin
decir "¡Última!", cada uno con la probabilidad de su nivel.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from games.prisma.engine import Phase, PrismaGame, PrismaRules, table_view

from . import PrismaBot, create_bot


@dataclass(slots=True)
class LevelResult:
    level: str
    games: int = 0
    wins: int = 0

    @property
    def win_rate(self) -> float:
        return self.wins / self.games if self.games else 0.0

    @property
    def margin(self) -> float:
        """Margen de error (dos desviaciones típicas) de `win_rate`."""
        if not self.games:
            return math.inf
        rate = self.win_rate
        return 2 * math.sqrt(rate * (1 - rate) / self.games)


def apply(game: PrismaGame, seat: int, bot: PrismaBot) -> None:
    """Hace la jugada que decide `bot` en su turno."""
    move = bot.decide(table_view(game, seat))
    if move.kind == "play":
        game.play(seat, move.card, move.color, declare=move.declare)
    elif move.kind == "draw":
        game.draw(seat)
    elif move.kind == "pass":
        game.pass_turn(seat)
    elif move.kind == "choose_color":
        game.choose_color(seat, move.color)
    elif move.kind == "challenge":
        game.challenge(seat)
    else:
        game.accept(seat)


def resolve_last_call(game: PrismaGame, bots: Sequence[PrismaBot], rng: random.Random) -> None:
    """Antes de que actúe el siguiente: quien se olvidó puede darse cuenta, o le pillan."""
    vulnerable = game.vulnerable
    if vulnerable is None:
        return
    if bots[vulnerable].says_last(table_view(game, vulnerable)):
        game.declare_last(vulnerable)
        return
    order = [seat for seat in range(len(bots)) if seat != vulnerable]
    rng.shuffle(order)
    for seat in order:
        if bots[seat].catches(table_view(game, seat)):
            game.catch(seat)
            return


def play_game(levels: Sequence[str], seed: int, rules: PrismaRules | None = None, max_moves: int = 3000) -> int | None:
    """Una ronda entre bots de los niveles dados (uno por asiento). Devuelve el asiento ganador."""
    rng = random.Random(seed)
    game = PrismaGame([f"{level}-{seat}" for seat, level in enumerate(levels)], rules, rng=rng)
    bots = [create_bot(level, game.players[seat].name, random.Random(seed * 31 + seat)) for seat, level in enumerate(levels)]
    game.start_round()
    for _ in range(max_moves):
        if game.phase == Phase.ROUND_OVER:
            return game.winner
        apply(game, game.turn, bots[game.turn])
        resolve_last_call(game, bots, rng)
    return None  # tablas por agotamiento (casi imposible)


def run_tournament(levels: Sequence[str], games: int, seed: int = 2026, rules: PrismaRules | None = None) -> dict[str, LevelResult]:
    """`games` partidas con un bot de cada nivel, rotando los asientos."""
    results = {level: LevelResult(level) for level in levels}
    count = len(levels)
    for number in range(games):
        shift = number % count
        seating = list(levels[shift:]) + list(levels[:shift])
        winner = play_game(seating, seed * 100_003 + number, rules)
        for level in seating:
            results[level].games += 1
        if winner is not None:
            results[seating[winner]].wins += 1
    return results
