"""Mazo. El barajado usa siempre el generador seguro del sistema operativo."""

from __future__ import annotations

from collections.abc import Iterable

from core.shuffle import SYSTEM_RNG as _SYSTEM_RNG  # el generador seguro, compartido

from .cards import Card, full_deck


class Deck:
    """Mazo de 52 cartas barajado.

    Si se pasa `cards`, el mazo queda en ese orden exacto y no se baraja.
    Eso existe solo para preparar manos concretas en los tests.
    """

    def __init__(self, cards: Iterable[Card] | None = None) -> None:
        if cards is None:
            self._cards = full_deck()
            _SYSTEM_RNG.shuffle(self._cards)
        else:
            self._cards = list(cards)
            if len(set(self._cards)) != len(self._cards):
                raise ValueError("El mazo tiene cartas repetidas")
        self._next = 0

    def __len__(self) -> int:
        """Cartas que quedan por repartir."""
        return len(self._cards) - self._next

    def deal(self, count: int = 1) -> list[Card]:
        if count < 0 or count > len(self):
            raise ValueError(f"No se pueden repartir {count} cartas; quedan {len(self)}")
        dealt = self._cards[self._next : self._next + count]
        self._next += count
        return dealt
