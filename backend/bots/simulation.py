"""Partidas bot contra bot para medir la fuerza de cada nivel.

Cada mano empieza con las mismas fichas para todos, así el resultado no depende
del tamaño del stack. Cada baraja se juega varias veces rotando los asientos:
todos los bots pasan por las mismas cartas y posiciones, lo que quita buena
parte de la suerte. Se mide en ciegas grandes ganadas cada 100 manos (bb/100).
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from poker_engine import Deck, Game, GameConfig, Hand, full_deck, player_view

from . import LEVELS, create_bot
from .base import Bot
from .personalities import NEUTRAL, PERSONALITIES


@dataclass(slots=True)
class BotResult:
    """Resultado acumulado de un bot, en ciegas grandes."""

    level: str
    hands: int = 0
    won: float = 0.0
    deals: int = 0  # barajas distintas jugadas (cada una, una vez por asiento)
    deal_squared: float = 0.0  # suma de cuadrados de lo ganado con cada baraja

    def add(self, other: BotResult) -> None:
        self.hands += other.hands
        self.won += other.won
        self.deals += other.deals
        self.deal_squared += other.deal_squared

    @property
    def bb_per_100(self) -> float:
        return 100 * self.won / self.hands if self.hands else 0.0

    @property
    def margin(self) -> float:
        """Margen de error (95%) de `bb_per_100`."""
        if self.deals < 2:
            return 0.0
        mean = self.won / self.deals
        variance = max(0.0, self.deal_squared / self.deals - mean * mean)
        return 100 * 1.96 * (variance * self.deals) ** 0.5 / self.hands


def play_hand(game: Game, bots: Mapping[int, Bot], deck: Deck | None = None) -> Hand:
    """Juega una mano completa: cada bot decide solo con su propia vista."""
    hand = game.start_hand(deck)
    while not hand.is_complete:
        seat = hand.to_act.seat
        hand.act(seat, bots[seat].decide(player_view(game, seat)))
    for seat, bot in bots.items():
        bot.observe(player_view(game, seat))
    return hand


def run_match(
    levels: Sequence[str],
    hands: int,
    seed: int,
    simulations: int = 200,
    personalities: bool = True,
    session_hands: int = 200,
    starting_stack: int = 1000,
    small_blind: int = 5,
    big_blind: int = 10,
) -> list[BotResult]:
    """Enfrenta un bot por cada entrada de `levels` durante unas `hands` manos.

    Los bots se crean de nuevo cada `session_hands` manos, como en una partida
    real: lo que un bot haya aprendido de sus rivales no dura para siempre.
    """
    for level in levels:
        if level not in LEVELS:
            raise ValueError(f"Nivel desconocido: {level!r}")
    rng = random.Random(seed)
    results = [BotResult(level) for level in levels]
    seats = len(levels)
    bots: list[Bot] = []

    for deal in range(max(1, hands // seats)):
        if deal % max(1, session_hands // seats) == 0:
            bots = _new_bots(levels, rng, simulations, personalities)
        seating = rng.sample(range(seats), seats)
        cards = full_deck()
        rng.shuffle(cards)
        deal_won = [0.0] * seats

        for shift in range(seats):
            rotated = seating[shift:] + seating[:shift]
            names = tuple(bots[index].name for index in rotated)
            game = Game(GameConfig(names, starting_stack, small_blind, big_blind), button_seat=0)
            play_hand(game, {seat: bots[index] for seat, index in enumerate(rotated)}, Deck(cards))
            if game.total_chips != starting_stack * seats:
                raise AssertionError("La mano no conservó las fichas")
            for seat, index in enumerate(rotated):
                deal_won[index] += (game.players[seat].stack - starting_stack) / big_blind

        for result, won in zip(results, deal_won):
            result.hands += seats
            result.won += won
            result.deals += 1
            result.deal_squared += won * won
    return results


def _new_bots(
    levels: Sequence[str], rng: random.Random, simulations: int, personalities: bool
) -> list[Bot]:
    chosen = rng.sample(PERSONALITIES, len(levels)) if personalities else [NEUTRAL] * len(levels)
    bots = []
    for index, (level, personality) in enumerate(zip(levels, chosen)):
        # Nombre único por asiento aunque se repitan niveles o personalidades.
        named = replace(personality, name=f"{personality.name} #{index + 1}")
        bots.append(create_bot(level, named, random.Random(rng.getrandbits(64)), simulations))
    return bots
