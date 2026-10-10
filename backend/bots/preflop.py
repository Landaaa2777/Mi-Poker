"""Fuerza de la mano inicial y rangos preflop.

Cada una de las 1326 manos iniciales recibe una puntuación (fórmula de Chen)
y con ella un lugar en el ranking: `top_fraction` dice en qué fracción de las
mejores manos está. Un rango es simplemente "las mejores X manos".
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from itertools import combinations

from poker_engine import Card, full_deck

_HIGH_CARD_POINTS = {14: 10.0, 13: 8.0, 12: 7.0, 11: 6.0}
_GAP_PENALTY = {0: 0.0, 1: 1.0, 2: 2.0, 3: 4.0}


def chen_score(first: Card, second: Card) -> float:
    """Puntuación de Chen: AA vale 20 y 72 de distinto palo vale -1."""
    high, low = max(first.rank, second.rank), min(first.rank, second.rank)
    points = _HIGH_CARD_POINTS.get(high, high / 2)
    if high == low:
        return max(points * 2, 5.0)
    if first.suit == second.suit:
        points += 2
    gap = high - low - 1
    points -= _GAP_PENALTY.get(gap, 5.0)
    if gap <= 1 and high < 12:
        points += 1  # conectores bajos: más escaleras posibles
    return float(math.ceil(points))


def _rank_combos() -> tuple[list[tuple[Card, Card]], dict[frozenset[Card], float]]:
    combos = sorted(combinations(full_deck(), 2), key=lambda c: chen_score(*c), reverse=True)
    fractions: dict[frozenset[Card], float] = {}
    start = 0
    while start < len(combos):
        score = chen_score(*combos[start])
        end = start
        while end < len(combos) and chen_score(*combos[end]) == score:
            end += 1
        # Las manos empatadas comparten el mismo lugar: el del final del grupo.
        for combo in combos[start:end]:
            fractions[frozenset(combo)] = end / len(combos)
        start = end
    return combos, fractions


# Todas las manos iniciales, de la mejor a la peor.
RANKED_COMBOS, _TOP_FRACTION = _rank_combos()


def top_fraction(hole_cards: Sequence[Card]) -> float:
    """Fracción de las mejores manos en la que cae esta: 0.005 es AA, 1.0 la peor."""
    return _TOP_FRACTION[frozenset(hole_cards)]


def combos_in_top(fraction: float) -> list[tuple[Card, Card]]:
    """Las manos del rango "mejor `fraction`" (al menos las 6 combinaciones de AA)."""
    count = max(6, min(len(RANKED_COMBOS), round(fraction * len(RANKED_COMBOS))))
    return RANKED_COMBOS[:count]
