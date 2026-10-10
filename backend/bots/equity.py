"""Estimación de equity por simulación Monte Carlo.

Solo usa las cartas propias y la mesa: las manos rivales y las cartas que
faltan se sortean entre las que el bot no ha visto.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from poker_engine import Card, evaluate, full_deck

from .preflop import combos_in_top

_BOARD_SIZE = 5
_MAX_TRIES = 30


def estimate_equity(
    hole_cards: Sequence[Card],
    board: Sequence[Card],
    opponents: int,
    simulations: int,
    rng: random.Random,
    ranges: Sequence[float] | None = None,
) -> float:
    """Fracción del bote que gana la mano de media contra `opponents` rivales.

    Los empates cuentan como la parte proporcional. Si se pasa `ranges` (uno
    por rival), la mano de cada rival se sortea solo entre las mejores manos
    iniciales de esa fracción; sin `ranges`, entre todas las posibles.
    """
    if opponents < 1:
        return 1.0
    hole = list(hole_cards)
    known_board = list(board)
    known = set(hole) | set(known_board)
    unseen = [card for card in full_deck() if card not in known]
    missing = _BOARD_SIZE - len(known_board)

    pools = None
    if ranges is not None and any(fraction < 1.0 for fraction in ranges):
        pools = [
            [combo for combo in combos_in_top(fraction) if known.isdisjoint(combo)]
            for fraction in ranges
        ]

    total = 0.0
    for _ in range(simulations):
        if pools is None:
            drawn = rng.sample(unseen, missing + 2 * opponents)
            rival_hands = [drawn[missing + 2 * i : missing + 2 * i + 2] for i in range(opponents)]
            full_board = known_board + drawn[:missing]
        else:
            rival_hands = _draw_from_ranges(pools, rng)
            taken = {card for hand in rival_hands for card in hand}
            drawn = [c for c in rng.sample(unseen, missing + len(taken)) if c not in taken]
            full_board = known_board + drawn[:missing]

        mine = evaluate(hole + full_board)
        tied = 1
        for rival in rival_hands:
            theirs = evaluate(list(rival) + full_board)
            if theirs > mine:
                tied = 0
                break
            if theirs == mine:
                tied += 1
        if tied:
            total += 1 / tied
    return total / simulations


def _draw_from_ranges(
    pools: list[list[tuple[Card, Card]]], rng: random.Random
) -> list[tuple[Card, Card]]:
    """Una mano por rival, cada una de su rango y sin cartas repetidas entre ellas."""
    for _ in range(_MAX_TRIES):
        hands: list[tuple[Card, Card]] = []
        taken: set[Card] = set()
        for pool in pools:
            for _ in range(_MAX_TRIES):
                combo = rng.choice(pool)
                if taken.isdisjoint(combo):
                    hands.append(combo)
                    taken.update(combo)
                    break
            else:
                break
        if len(hands) == len(pools):
            return hands
    raise ValueError("Los rangos de los rivales no son compatibles con las cartas conocidas")
