"""Lo que comparten los bots de todos los juegos.

Cada juego tiene sus propios bots, pero todos siguen la misma idea:

- Reciben solo la vista pública de la mesa más lo suyo (sus propias cartas).
  Nunca ven cartas ocultas ajenas, ni el mazo, ni la carta tapada del crupier.
- Devuelven una acción con su método `decide(vista)`.
- Cambiar de nivel cambia la estrategia, nunca la información que reciben.
- "Piensan" un rato antes de actuar, como haría una persona.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from typing import Any, Protocol

BOT_DELAY = (0.8, 2.5)  # segundos que un bot "piensa" antes de actuar

# Niveles de dificultad, del más flojo al más fuerte, con su nombre en pantalla.
LEVEL_NAMES = {"easy": "Fácil", "medium": "Medio", "hard": "Difícil", "expert": "Experto"}

# Nombres originales para los asientos de los bots del blackjack y de Prisma.
# (Los del poker van con su personalidad, en `games/poker/bots/personalities.py`.)
BOT_NAMES = (
    "Brisa",
    "Cobalto",
    "Lince",
    "Olivo",
    "Pimienta",
    "Sauce",
    "Trueno",
    "Vela",
    "Coral",
    "Halcón",
    "Musgo",
    "Pizarra",
)


class Bot(Protocol):
    """Lo que tiene cualquier bot: su nivel y una forma de decidir."""

    level: str

    def decide(self, view: Any) -> Any:
        """Recibe su vista de la mesa y devuelve la acción que quiere hacer."""
        ...


def pick_names(count: int, taken: Iterable[str] = (), rng: random.Random | None = None) -> list[str]:
    """`count` nombres distintos para los bots, sin repetir ninguno de `taken`.

    >>> len(set(pick_names(4)))
    4
    """
    used = {name.casefold() for name in taken}
    free = [name for name in BOT_NAMES if name.casefold() not in used]
    if count > len(free):
        raise ValueError(f"Solo hay {len(free)} nombres libres para los bots")
    return (rng or random).sample(free, count)
