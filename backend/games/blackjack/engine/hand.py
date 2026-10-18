"""Cuánto vale una mano de blackjack.

Las figuras (J, Q, K) valen 10, el As vale 11 o 1, y el resto su número. Una
mano es "blanda" cuando cuenta un As como 11 sin pasarse: puede pedir otra
carta sin miedo, porque si se pasara el As pasaría a valer 1.

    >>> from core.cards import parse_cards
    >>> hand_total(parse_cards("Ah 6d"))
    (17, True)
    >>> hand_total(parse_cards("Ah 6d 9c"))
    (16, False)
"""

from __future__ import annotations

from collections.abc import Sequence

from core.cards import Card

BLACKJACK = 21
ACE = 14


def card_value(card: Card) -> int:
    """Valor de una carta: el As cuenta aquí como 11, las figuras como 10."""
    if card.rank == ACE:
        return 11
    return min(card.rank, 10)


def hand_total(cards: Sequence[Card]) -> tuple[int, bool]:
    """El total de la mano y si es blanda (un As cuenta como 11)."""
    total = sum(1 if card.rank == ACE else min(card.rank, 10) for card in cards)
    has_ace = any(card.rank == ACE for card in cards)
    # Un As puede valer 11 (10 más que 1) si así no se pasa de 21.
    if has_ace and total + 10 <= BLACKJACK:
        return total + 10, True
    return total, False


def is_blackjack(cards: Sequence[Card], from_split: bool = False) -> bool:
    """¿Es un blackjack natural? Dos cartas que suman 21, y no después de dividir."""
    return not from_split and len(cards) == 2 and hand_total(cards)[0] == BLACKJACK


def is_bust(cards: Sequence[Card]) -> bool:
    """¿Se ha pasado de 21?"""
    return hand_total(cards)[0] > BLACKJACK
