"""Las cartas de Prisma: 108, con cuatro palos de color y comodines.

Cada palo tiene su nombre, su color y una forma distinta (para distinguirlos
también sin ver los colores):

    Panal  hexágono, naranja cobre        Halo    anillo, turquesa
    Cumbre triángulo, violeta             Astro   estrella de cuatro puntas, fucsia

Por palo hay un 0, dos de cada número del 1 al 9 y dos de cada acción:
    Pausa      el siguiente pierde su turno
    Remolino   cambia el sentido del juego
    Carga +2   el siguiente roba 2 y pierde su turno
Y sin palo, 4 Camaleón (eliges el color) y 4 Camaleón +4 (eliges el color y
el siguiente roba 4 y pierde su turno).

Como hay cartas repetidas, cada una lleva un número propio (`id`, de 0 a 107)
para saber exactamente cuál se juega.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Color(StrEnum):
    PANAL = "panal"
    HALO = "halo"
    CUMBRE = "cumbre"
    ASTRO = "astro"


class Kind(StrEnum):
    NUMBER = "number"
    PAUSA = "pausa"  # salto
    REMOLINO = "remolino"  # cambio de sentido
    CARGA = "carga"  # +2
    CAMALEON = "camaleon"  # comodín de color
    CAMALEON4 = "camaleon4"  # comodín +4


ACTIONS = (Kind.PAUSA, Kind.REMOLINO, Kind.CARGA)
WILDS = (Kind.CAMALEON, Kind.CAMALEON4)

# Puntos de cada carta que se queda en la mano al acabar la ronda.
ACTION_POINTS = 20
WILD_POINTS = 50

KIND_NAMES = {
    Kind.PAUSA: "Pausa",
    Kind.REMOLINO: "Remolino",
    Kind.CARGA: "Carga +2",
    Kind.CAMALEON: "Camaleón",
    Kind.CAMALEON4: "Camaleón +4",
}
COLOR_NAMES = {Color.PANAL: "Panal", Color.HALO: "Halo", Color.CUMBRE: "Cumbre", Color.ASTRO: "Astro"}


@dataclass(frozen=True, slots=True)
class PrismaCard:
    id: int  # único en el mazo: distingue las dos copias de cada carta
    kind: Kind
    color: Color | None = None  # None en los comodines
    number: int | None = None  # solo en las cartas de número

    @property
    def is_wild(self) -> bool:
        return self.kind in WILDS

    @property
    def points(self) -> int:
        """Lo que vale si se queda en la mano al acabar la ronda."""
        if self.kind == Kind.NUMBER:
            assert self.number is not None
            return self.number
        return WILD_POINTS if self.is_wild else ACTION_POINTS

    @property
    def code(self) -> str:
        """Nombre corto, sin el id: "panal-7", "halo-pausa", "camaleon4"."""
        if self.is_wild:
            return self.kind.value
        assert self.color is not None
        detail = str(self.number) if self.kind == Kind.NUMBER else self.kind.value
        return f"{self.color.value}-{detail}"

    def __str__(self) -> str:
        return self.code

    def name(self) -> str:
        """Cómo se dice en español: "Panal 7", "Halo Pausa", "Camaleón +4"."""
        if self.is_wild:
            return KIND_NAMES[self.kind]
        assert self.color is not None
        detail = str(self.number) if self.kind == Kind.NUMBER else KIND_NAMES[self.kind]
        return f"{COLOR_NAMES[self.color]} {detail}"

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind.value, "color": self.color, "number": self.number}


def full_deck() -> list[PrismaCard]:
    """Las 108 cartas, en orden fijo (sin barajar)."""
    cards: list[PrismaCard] = []

    def add(kind: Kind, color: Color | None = None, number: int | None = None) -> None:
        cards.append(PrismaCard(len(cards), kind, color, number))

    for color in Color:
        add(Kind.NUMBER, color, 0)
        for number in range(1, 10):
            add(Kind.NUMBER, color, number)
            add(Kind.NUMBER, color, number)
        for action in ACTIONS:
            add(action, color)
            add(action, color)
    for _ in range(4):
        add(Kind.CAMALEON)
    for _ in range(4):
        add(Kind.CAMALEON4)
    return cards


DECK_SIZE = 108
