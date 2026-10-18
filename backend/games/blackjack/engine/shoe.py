"""El zapato: varios mazos barajados juntos, con una carta de corte.

Cuando el reparto pasa la carta de corte (hacia el 75 % del zapato), la ronda
en curso se termina con normalidad y se rebaraja todo antes de la siguiente.
Así nunca se juega hasta la última carta.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Iterable

from core.cards import Card, full_deck
from core.shuffle import SYSTEM_RNG


class Shoe:
    """Zapato de `decks` mazos de 52 cartas.

    Si se pasa `cards`, el zapato queda en ese orden exacto y no se baraja: eso
    existe solo para preparar rondas concretas en los tests. Sin `rng`, se
    baraja con el generador seguro del sistema.
    """

    def __init__(
        self,
        decks: int = 6,
        penetration: float = 0.75,
        rng: random.Random | None = None,
        cards: Iterable[Card] | None = None,
        cut: int | None = None,
    ) -> None:
        if decks < 1:
            raise ValueError("El zapato necesita al menos un mazo")
        if not 0.1 <= penetration <= 0.95:
            raise ValueError("La carta de corte va entre el 10 % y el 95 % del zapato")
        self.decks = decks
        self.penetration = penetration
        self._rng = rng
        self._fixed = cards is not None
        self._cards: list[Card] = list(cards) if cards is not None else full_deck() * decks
        self._next = 0
        self.shuffles = 0  # cuántas veces se ha barajado
        if self._fixed:
            self._cut = len(self._cards) if cut is None else cut
        else:
            self._shuffle()

    @property
    def total(self) -> int:
        """Cartas que tiene el zapato completo."""
        return len(self._cards)

    def __len__(self) -> int:
        """Cartas que quedan por repartir."""
        return len(self._cards) - self._next

    @property
    def cut_reached(self) -> bool:
        """¿Ha salido la carta de corte? Entonces hay que rebarajar antes de la próxima ronda."""
        return self._next >= self._cut

    def deal(self, in_play: Iterable[Card] = ()) -> Card:
        """Saca la siguiente carta.

        Si el zapato se acabara a media ronda (con la carta de corte no pasa
        nunca en la práctica), se rebarajan todas las cartas menos las que hay
        sobre la mesa (`in_play`), para que ninguna esté dos veces en juego.
        """
        if self._next >= len(self._cards):
            if self._fixed:
                raise ValueError("El zapato preparado para el test se ha quedado sin cartas")
            # Hasta el próximo rebarajado entre rondas, el zapato queda sin las de la mesa.
            on_table = Counter(in_play)
            remaining = []
            for card in full_deck() * self.decks:
                if on_table[card]:
                    on_table[card] -= 1
                else:
                    remaining.append(card)
            self._cards = remaining
            self._shuffle()
        card = self._cards[self._next]
        self._next += 1
        return card

    def reshuffle(self) -> None:
        """Junta todas las cartas y las vuelve a barajar (entre rondas)."""
        if self._fixed:
            self._next = 0  # un zapato de test vuelve a empezar en el mismo orden
            self.shuffles += 1
            return
        self._cards = full_deck() * self.decks
        self._shuffle()

    def _shuffle(self) -> None:
        rng = self._rng or SYSTEM_RNG
        rng.shuffle(self._cards)
        self._next = 0
        self.shuffles += 1
        # La carta de corte va hacia el 75 %, con un pequeño margen al azar
        # (unas dos cartas por mazo) para que no caiga siempre en el mismo sitio.
        spread = 2 * self.decks
        base = int(len(self._cards) * self.penetration)
        self._cut = max(1, base + rng.randint(-spread, spread))
