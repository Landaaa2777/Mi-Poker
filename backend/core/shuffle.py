"""Barajado seguro, el mismo para todos los juegos.

Se usa siempre el generador del sistema operativo (`random.SystemRandom`). El
módulo `random` normal es predecible: con unas cuantas cartas vistas se podría
adivinar el resto del mazo. Solo los tests y las simulaciones pasan su propio
generador con semilla, para que el resultado se repita.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from typing import TypeVar

T = TypeVar("T")

# Nunca usar el módulo `random` normal para barajar: es predecible.
SYSTEM_RNG = random.SystemRandom()


def shuffled(items: Iterable[T], rng: random.Random | None = None) -> list[T]:
    """Una copia barajada de `items`. Sin `rng`, con el generador seguro.

    >>> sorted(shuffled([3, 1, 2]))
    [1, 2, 3]
    """
    cards = list(items)
    (rng or SYSTEM_RNG).shuffle(cards)
    return cards
