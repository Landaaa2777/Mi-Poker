"""Rondas bot contra crupier para medir cada nivel del blackjack.

Para comparar niveles con poca suerte de por medio, todos juegan exactamente las
mismas rondas: cada ronda sale de un zapato barajado con su propia semilla, y
cada nivel la juega desde ese mismo zapato. Lo que cambia el resultado son solo
sus decisiones. Todos apuestan siempre la mínima.

El resultado se mide en apuestas ganadas cada 100 rondas (negativo: pierde).
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from core.cards import full_deck
from games.blackjack.engine import BlackjackGame, Phase, Rules, Shoe, table_view

from . import create_bot


@dataclass(slots=True)
class LevelResult:
    level: str
    rounds: int = 0
    won: float = 0.0  # en apuestas mínimas
    squared: float = 0.0

    @property
    def per_100(self) -> float:
        """Apuestas ganadas (o perdidas) cada 100 rondas."""
        return 100 * self.won / self.rounds if self.rounds else 0.0

    @property
    def margin(self) -> float:
        """Margen de error (dos desviaciones típicas) de `per_100`."""
        if self.rounds < 2:
            return math.inf
        mean = self.won / self.rounds
        variance = self.squared / self.rounds - mean * mean
        return 200 * math.sqrt(max(variance, 0.0) / self.rounds)


def play_round(level: str, cards: Sequence, rules: Rules, rng: random.Random) -> float:
    """Una ronda de un bot solo contra el crupier. Devuelve lo ganado en apuestas mínimas."""
    game = BlackjackGame(["Bot"], 1_000_000, rules, shoe=Shoe(cards=cards))
    bot = create_bot(level, "Bot", rng, units=1)
    before = game.seats[0].stack
    game.start_round({0: rules.min_bet})
    while game.phase == Phase.INSURANCE:
        game.insure(0, bot.insure(table_view(game, 0)))
    while game.phase == Phase.PLAYING:
        game.act(0, bot.decide(table_view(game, 0)))
    return (game.seats[0].stack - before) / rules.min_bet


def run_levels(
    levels: Sequence[str], rounds: int, seed: int = 2026, rules: Rules | None = None
) -> dict[str, LevelResult]:
    """Juega `rounds` rondas con cada nivel, todas sobre los mismos zapatos."""
    rules = rules or Rules()
    results = {level: LevelResult(level) for level in levels}
    deck = full_deck() * rules.decks
    for number in range(rounds):
        cards = list(deck)
        random.Random(seed * 1_000_003 + number).shuffle(cards)
        for level in levels:
            won = play_round(level, cards, rules, random.Random(seed + number))
            result = results[level]
            result.rounds += 1
            result.won += won
            result.squared += won * won
    return results


def compare(
    stronger: str, weaker: str, rounds: int, seed: int = 2026, rules: Rules | None = None
) -> tuple[float, float]:
    """Cuánto gana `stronger` a `weaker` cada 100 rondas, jugando las mismas rondas.

    Devuelve la diferencia y su margen de error (dos desviaciones típicas). Al
    jugar los dos con los mismos zapatos, la suerte casi se anula y basta con
    menos rondas para ver quién juega mejor.
    """
    rules = rules or Rules()
    deck = full_deck() * rules.decks
    total = squared = 0.0
    for number in range(rounds):
        cards = list(deck)
        random.Random(seed * 1_000_003 + number).shuffle(cards)
        mine = play_round(stronger, cards, rules, random.Random(seed + number))
        theirs = play_round(weaker, cards, rules, random.Random(seed + number))
        total += mine - theirs
        squared += (mine - theirs) ** 2
    mean = total / rounds
    variance = squared / rounds - mean * mean
    return 100 * mean, 200 * math.sqrt(max(variance, 0.0) / rounds)
