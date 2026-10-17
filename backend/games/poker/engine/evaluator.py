"""Evaluador de manos: la mejor mano de 5 cartas entre 5, 6 o 7."""

from __future__ import annotations

from collections.abc import Sequence
from enum import IntEnum

from .cards import Card


class HandCategory(IntEnum):
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10


CATEGORY_NAMES = {
    HandCategory.HIGH_CARD: "Carta alta",
    HandCategory.PAIR: "Pareja",
    HandCategory.TWO_PAIR: "Doble pareja",
    HandCategory.THREE_OF_A_KIND: "Trío",
    HandCategory.STRAIGHT: "Escalera",
    HandCategory.FLUSH: "Color",
    HandCategory.FULL_HOUSE: "Full",
    HandCategory.FOUR_OF_A_KIND: "Póker",
    HandCategory.STRAIGHT_FLUSH: "Escalera de color",
    HandCategory.ROYAL_FLUSH: "Escalera real",
}

# (categoría, desempates de mayor a menor importancia). Dos valores se comparan
# directamente con <, > y ==; valores iguales significan empate exacto.
HandValue = tuple[HandCategory, tuple[int, ...]]

_FIVE_IN_A_ROW = 0b11111


def _straight_high(rank_mask: int) -> int:
    """Carta más alta de la mejor escalera en la máscara de valores, o 0."""
    if rank_mask & (1 << 14):
        rank_mask |= 1 << 1  # el as también vale como 1 (A-2-3-4-5)
    for high in range(14, 4, -1):
        if (rank_mask >> (high - 4)) & _FIVE_IN_A_ROW == _FIVE_IN_A_ROW:
            return high
    return 0


def evaluate(cards: Sequence[Card]) -> HandValue:
    """Valor de la mejor mano de 5 cartas que se puede formar con `cards`."""
    count = len(cards)
    if not 5 <= count <= 7:
        raise ValueError(f"Se necesitan entre 5 y 7 cartas, no {count}")
    if len(set(cards)) != count:
        raise ValueError("Hay cartas repetidas")

    rank_counts: dict[int, int] = {}
    suit_counts: dict[str, int] = {}
    rank_mask = 0
    for card in cards:
        rank_counts[card.rank] = rank_counts.get(card.rank, 0) + 1
        suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1
        rank_mask |= 1 << card.rank

    flush_ranks: list[int] | None = None
    for suit, suited in suit_counts.items():
        if suited >= 5:
            flush_ranks = sorted((c.rank for c in cards if c.suit == suit), reverse=True)
            flush_mask = 0
            for rank in flush_ranks:
                flush_mask |= 1 << rank
            high = _straight_high(flush_mask)
            if high == 14:
                return (HandCategory.ROYAL_FLUSH, (high,))
            if high:
                return (HandCategory.STRAIGHT_FLUSH, (high,))
            break

    # Valores ordenados por repeticiones y luego por valor: el grupo más fuerte primero.
    by_count = sorted(rank_counts, key=lambda r: (rank_counts[r], r), reverse=True)
    top = by_count[0]
    top_count = rank_counts[top]

    if top_count == 4:
        kicker = max(r for r in rank_counts if r != top)
        return (HandCategory.FOUR_OF_A_KIND, (top, kicker))

    if top_count == 3 and rank_counts[by_count[1]] >= 2:
        return (HandCategory.FULL_HOUSE, (top, by_count[1]))

    if flush_ranks is not None:
        return (HandCategory.FLUSH, tuple(flush_ranks[:5]))

    high = _straight_high(rank_mask)
    if high:
        return (HandCategory.STRAIGHT, (high,))

    if top_count == 3:
        kickers = sorted((r for r in rank_counts if r != top), reverse=True)[:2]
        return (HandCategory.THREE_OF_A_KIND, (top, *kickers))

    if top_count == 2:
        second = by_count[1]
        if rank_counts[second] == 2:
            kicker = max(r for r in rank_counts if r != top and r != second)
            return (HandCategory.TWO_PAIR, (top, second, kicker))
        kickers = sorted((r for r in rank_counts if r != top), reverse=True)[:3]
        return (HandCategory.PAIR, (top, *kickers))

    return (HandCategory.HIGH_CARD, tuple(sorted(rank_counts, reverse=True)[:5]))
