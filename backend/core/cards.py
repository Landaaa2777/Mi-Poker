"""Cartas de la baraja francesa de 52 cartas, compartidas por el poker y el blackjack."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

RANK_CHARS = "23456789TJQKA"
SUIT_CHARS = "cdhs"


class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


class Suit(StrEnum):
    CLUBS = "c"
    DIAMONDS = "d"
    HEARTS = "h"
    SPADES = "s"


@dataclass(frozen=True, slots=True)
class Card:
    """Carta inmutable. `rank` va de 2 a 14 (as) y `suit` es una de "cdhs"."""

    rank: int
    suit: str

    def __post_init__(self) -> None:
        if self.rank not in range(2, 15):
            raise ValueError(f"Valor de carta inválido: {self.rank!r}")
        if self.suit not in SUIT_CHARS or len(self.suit) != 1:
            raise ValueError(f"Palo inválido: {self.suit!r}")

    def __str__(self) -> str:
        return RANK_CHARS[self.rank - 2] + self.suit

    def __repr__(self) -> str:
        return f"Card('{self}')"

    @classmethod
    def parse(cls, text: str) -> Card:
        """Crea una carta desde texto como "As", "Td" o "2c"."""
        if len(text) != 2:
            raise ValueError(f"Carta inválida: {text!r}")
        rank_index = RANK_CHARS.find(text[0].upper())
        if rank_index < 0:
            raise ValueError(f"Carta inválida: {text!r}")
        return cls(rank_index + 2, text[1].lower())


def parse_cards(text: str) -> list[Card]:
    """Convierte "As Kd 7h" en una lista de cartas."""
    return [Card.parse(token) for token in text.split()]


def full_deck() -> list[Card]:
    """Las 52 cartas en orden fijo (sin barajar)."""
    return [Card(rank, suit) for suit in SUIT_CHARS for rank in range(2, 15)]
