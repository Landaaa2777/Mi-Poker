"""Lectura rápida de la mano después del flop, sin simulación.

Clasifica la mano hecha (pareja alta, trío, proyecto...) mirando cuánto
aportan las cartas propias, y cuenta los outs de los proyectos.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from poker_engine import Card, HandCategory, evaluate

_FLUSH_DRAW_OUTS = 9
_OPEN_ENDED_OUTS = 8
_GUTSHOT_OUTS = 4


@dataclass(frozen=True, slots=True)
class HandRead:
    category: HandCategory
    strength: float  # 0 = nada, 1 = imbatible; ver la escala en `read_hand`
    outs: int  # cartas que completan un proyecto de color o escalera

    def draw_equity(self, cards_to_come: int) -> float:
        """Regla del 2 y del 4: cada out vale un 2% por carta que falta."""
        return min(0.6, self.outs * 0.02 * cards_to_come)


def _has_straight(ranks: set[int]) -> bool:
    if 14 in ranks:
        ranks = ranks | {1}
    return any(all(r + i in ranks for i in range(5)) for r in range(1, 11))


def _straight_outs(hole: Sequence[Card], board: Sequence[Card]) -> int:
    board_ranks = {c.rank for c in board}
    ranks = board_ranks | {c.rank for c in hole}
    if _has_straight(ranks):
        return 0
    completing = sum(
        _has_straight(ranks | {rank}) and not _has_straight(board_ranks | {rank})
        for rank in range(2, 15)
        if rank not in ranks
    )
    if completing >= 2:
        return _OPEN_ENDED_OUTS
    return _GUTSHOT_OUTS if completing else 0


def _flush_outs(hole: Sequence[Card], board: Sequence[Card]) -> int:
    for suit, count in Counter(c.suit for c in [*hole, *board]).items():
        if count == 4 and any(c.suit == suit for c in hole):
            return _FLUSH_DRAW_OUTS
    return 0


def read_hand(hole: Sequence[Card], board: Sequence[Card]) -> HandRead:
    """Clasifica la mano del bot en la mesa actual (flop, turn o river).

    Escala de `strength`: 0.9+ escalera o mejor, o trío con pareja de mano;
    0.85 doble pareja; 0.65-0.8 pareja máxima u overpair; 0.4-0.55 parejas
    menores; 0.1-0.25 nada. Una mano que solo "juega la mesa" cuenta como nada.
    """
    category, _ = evaluate([*hole, *board])
    board_counts = Counter(c.rank for c in board)
    board_ranks = sorted(board_counts, reverse=True)
    hole_ranks = sorted((c.rank for c in hole), reverse=True)
    pocket_pair = hole_ranks[0] == hole_ranks[1]
    # Valores de la mesa con los que alguna carta propia hace pareja o más.
    matched = [rank for rank in board_ranks if rank in hole_ranks]
    board_suited = max(Counter(c.suit for c in board).values())

    if len(board) == 5 and evaluate(board) == evaluate([*hole, *board]):
        strength = 0.15  # juega la mesa: como mucho empata
    elif category >= HandCategory.FULL_HOUSE:
        strength = 0.97
    elif category is HandCategory.FLUSH:
        suit = Counter(c.suit for c in [*hole, *board]).most_common(1)[0][0]
        best_own = max((c.rank for c in hole if c.suit == suit), default=0)
        # Con cuatro del palo en la mesa, un color bajo pierde a menudo.
        strength = 0.93 if board_suited <= 3 or best_own >= 12 else 0.7
    elif category is HandCategory.STRAIGHT:
        strength = 0.9 if board_suited <= 3 else 0.6
    elif category is HandCategory.THREE_OF_A_KIND:
        if pocket_pair and matched:
            strength = 0.92
        elif matched:
            strength = 0.86
        else:
            strength = 0.25  # el trío está en la mesa: lo tiene todo el mundo
    elif category is HandCategory.TWO_PAIR:
        own_pairs = len(matched) + (pocket_pair and not matched)
        if len(matched) == 2 and not pocket_pair:
            strength = 0.86
        elif own_pairs:
            # Una de las parejas es de la mesa: en la práctica es una sola pareja.
            strength = _pair_strength(hole_ranks, board_ranks, matched, pocket_pair) - 0.03
        else:
            strength = 0.2
    elif category is HandCategory.PAIR:
        if pocket_pair or matched:
            strength = _pair_strength(hole_ranks, board_ranks, matched, pocket_pair)
        else:
            strength = 0.25 if hole_ranks[0] == 14 else 0.15
    else:
        if hole_ranks[0] == 14:
            strength = 0.25
        else:
            strength = 0.2 if hole_ranks[1] > board_ranks[0] else 0.12

    if board_suited >= 4 and category < HandCategory.FLUSH:
        strength = min(strength, 0.6)

    outs = 0
    if len(board) < 5 and category < HandCategory.STRAIGHT:
        outs = _flush_outs(hole, board) + _straight_outs(hole, board)
    return HandRead(category, strength, outs)


def _pair_strength(
    hole_ranks: list[int], board_ranks: list[int], matched: list[int], pocket_pair: bool
) -> float:
    """Fuerza de una pareja según su altura respecto a la mesa."""
    pair_rank = hole_ranks[0] if pocket_pair else matched[0]
    higher_on_board = sum(rank > pair_rank for rank in board_ranks)
    if higher_on_board == 0:
        if pocket_pair:
            return 0.78  # overpair
        kicker = next(rank for rank in hole_ranks if rank != pair_rank)
        return 0.72 if kicker >= 11 else 0.65  # pareja máxima
    if higher_on_board == 1:
        return 0.52
    return 0.4
