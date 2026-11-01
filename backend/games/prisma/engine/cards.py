"""Las cartas de Prisma y los mazos de sus tres modos.

Clásico (108 cartas). Cuatro palos, cada uno con su nombre, su color y una
forma distinta (para distinguirlos también sin ver los colores):

    Panal  hexágono, naranja cobre        Halo    anillo, turquesa
    Cumbre triángulo, violeta             Astro   estrella de cuatro puntas, fucsia

Por palo hay un 0, dos de cada número del 1 al 9 y dos de cada acción:
    Pausa      el siguiente pierde su turno
    Remolino   cambia el sentido del juego
    Carga +2   el siguiente roba 2 y pierde su turno
Y sin palo, 4 Camaleón (eliges el color) y 4 Camaleón +4 (eliges el color y
el siguiente roba 4 y pierde su turno).

Doble cara (112 cartas de dos caras). La cara de luz lleva los palos de
siempre; la de sombra, cartas negras con cuatro palos propios:

    Brasa  rombo, carmesí                 Ámbar   luna, dorado
    Jade   hoja, verde                    Índigo  gota, azul oscuro

Luz: por palo, dos de cada número del 1 al 9 y dos de Carga +1, Remolino,
Pausa y Eclipse; además 4 Camaleón y 4 Camaleón +2. Sombra: por palo, dos de
cada número del 1 al 9 y dos de Carga +5, Remolino, Pausa total y Eclipse;
además 4 Camaleón y 4 Camaleón Sabueso. Cada carta física junta una cara de
luz y una de sombra, emparejadas al azar en cada ronda.

Sin tregua (168 cartas, los palos de siempre). Por palo, dos de cada número
del 0 al 9, tres Pausa, tres Remolino, tres Carga +2, dos Carga +4, tres
Barrido y dos Pausa total; además 8 Camaleón Remolino +4, 4 Camaleón +6,
4 Camaleón +10 y 8 Camaleón Ruleta.

Como hay cartas repetidas, cada carta física lleva un número propio (`id`)
para saber exactamente cuál se juega.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum


class Mode(StrEnum):
    """Los modos de juego de Prisma."""

    CLASICO = "clasico"
    DOBLE = "doble_cara"
    SIN_TREGUA = "sin_tregua"


class Side(StrEnum):
    """La cara que está en juego (solo cambia en Doble cara)."""

    LUZ = "luz"
    SOMBRA = "sombra"


class Color(StrEnum):
    # Los palos de siempre (y los de la cara de luz).
    PANAL = "panal"
    HALO = "halo"
    CUMBRE = "cumbre"
    ASTRO = "astro"
    # Los de la cara de sombra, en Doble cara.
    BRASA = "brasa"
    AMBAR = "ambar"
    JADE = "jade"
    INDIGO = "indigo"


LIGHT_COLORS = (Color.PANAL, Color.HALO, Color.CUMBRE, Color.ASTRO)
DARK_COLORS = (Color.BRASA, Color.AMBAR, Color.JADE, Color.INDIGO)


class Kind(StrEnum):
    NUMBER = "number"
    PAUSA = "pausa"  # salto
    REMOLINO = "remolino"  # cambio de sentido
    CARGA = "carga"  # +2
    CAMALEON = "camaleon"  # comodín de color
    CAMALEON4 = "camaleon4"  # comodín +4
    # Doble cara
    CARGA1 = "carga1"  # +1 (luz)
    CARGA5 = "carga5"  # +5 (sombra)
    ECLIPSE = "eclipse"  # le da la vuelta a toda la mesa
    PAUSA_TOTAL = "pausa_total"  # todos pierden el turno (también en Sin tregua)
    CAMALEON2 = "camaleon2"  # comodín +2 (luz)
    SABUESO = "sabueso"  # comodín: el siguiente roba hasta sacar el color (sombra)
    # Sin tregua
    CARGA4 = "carga4"  # +4 de color
    BARRIDO = "barrido"  # sueltas todas tus cartas de su color
    CAMALEON_REMOLINO4 = "camaleon_remolino4"  # cambia el sentido y el siguiente roba 4
    CAMALEON6 = "camaleon6"  # comodín +6
    CAMALEON10 = "camaleon10"  # comodín +10
    RULETA = "ruleta"  # el siguiente elige color y destapa hasta que sale


WILDS = frozenset(
    {
        Kind.CAMALEON,
        Kind.CAMALEON4,
        Kind.CAMALEON2,
        Kind.SABUESO,
        Kind.CAMALEON_REMOLINO4,
        Kind.CAMALEON6,
        Kind.CAMALEON10,
        Kind.RULETA,
    }
)

# Cuántas cartas hace robar cada carga (las que se pueden acumular en Sin tregua).
DRAW_VALUE = {
    Kind.CARGA1: 1,
    Kind.CARGA: 2,
    Kind.CAMALEON2: 2,
    Kind.CARGA4: 4,
    Kind.CAMALEON4: 4,
    Kind.CAMALEON_REMOLINO4: 4,
    Kind.CARGA5: 5,
    Kind.CAMALEON6: 6,
    Kind.CAMALEON10: 10,
}

# Puntos de cada carta que se queda en la mano al acabar la ronda (los números, su valor).
ACTION_POINTS = 20
WILD_POINTS = 50
# Doble cara tiene su propia tabla (la de la cara en juego al acabar).
DOUBLE_POINTS = {
    Kind.CARGA1: 10,
    Kind.CARGA5: 20,
    Kind.REMOLINO: 20,
    Kind.PAUSA: 20,
    Kind.ECLIPSE: 20,
    Kind.PAUSA_TOTAL: 30,
    Kind.CAMALEON: 40,
    Kind.CAMALEON2: 50,
    Kind.SABUESO: 60,
}

KIND_NAMES = {
    Kind.PAUSA: "Pausa",
    Kind.REMOLINO: "Remolino",
    Kind.CARGA: "Carga +2",
    Kind.CAMALEON: "Camaleón",
    Kind.CAMALEON4: "Camaleón +4",
    Kind.CARGA1: "Carga +1",
    Kind.CARGA5: "Carga +5",
    Kind.ECLIPSE: "Eclipse",
    Kind.PAUSA_TOTAL: "Pausa total",
    Kind.CAMALEON2: "Camaleón +2",
    Kind.SABUESO: "Camaleón Sabueso",
    Kind.CARGA4: "Carga +4",
    Kind.BARRIDO: "Barrido",
    Kind.CAMALEON_REMOLINO4: "Camaleón Remolino +4",
    Kind.CAMALEON6: "Camaleón +6",
    Kind.CAMALEON10: "Camaleón +10",
    Kind.RULETA: "Camaleón Ruleta",
}
COLOR_NAMES = {
    Color.PANAL: "Panal",
    Color.HALO: "Halo",
    Color.CUMBRE: "Cumbre",
    Color.ASTRO: "Astro",
    Color.BRASA: "Brasa",
    Color.AMBAR: "Ámbar",
    Color.JADE: "Jade",
    Color.INDIGO: "Índigo",
}


@dataclass(frozen=True, slots=True)
class PrismaCard:
    """Una carta tal como está en juego: su cara visible y, en Doble cara, la otra (`back`)."""

    id: int  # único en el mazo: distingue las copias de cada carta
    kind: Kind
    color: Color | None = None  # None en los comodines
    number: int | None = None  # solo en las cartas de número
    back: PrismaCard | None = None  # la otra cara (solo en Doble cara)

    @property
    def is_wild(self) -> bool:
        return self.kind in WILDS

    @property
    def draw_value(self) -> int:
        """Cuántas cartas hace robar (0 si no es una carga)."""
        return DRAW_VALUE.get(self.kind, 0)

    @property
    def points(self) -> int:
        """Lo que vale si se queda en la mano al acabar la ronda (Clásico y Sin tregua)."""
        if self.kind == Kind.NUMBER:
            assert self.number is not None
            return self.number
        return WILD_POINTS if self.is_wild else ACTION_POINTS

    def points_in(self, mode: Mode) -> int:
        """Lo que vale en `mode`: Doble cara tiene su propia tabla."""
        if mode == Mode.DOBLE and self.kind != Kind.NUMBER:
            return DOUBLE_POINTS[self.kind]
        return self.points

    def flipped(self) -> PrismaCard:
        """La misma carta, dada la vuelta: la otra cara pasa a estar en juego."""
        if self.back is None:
            raise ValueError("Esta carta solo tiene una cara")
        front = PrismaCard(self.id, self.kind, self.color, self.number)
        return PrismaCard(self.id, self.back.kind, self.back.color, self.back.number, back=front)

    def face(self) -> PrismaCard:
        """Solo la cara en juego, sin la otra (lo que se puede enseñar)."""
        return PrismaCard(self.id, self.kind, self.color, self.number) if self.back else self

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
        """La cara en juego, con su id. La otra cara nunca va aquí (ver las vistas)."""
        return {"id": self.id, "kind": self.kind.value, "color": self.color, "number": self.number}


def face_dict(card: PrismaCard) -> dict:
    """Una cara suelta, sin id: lo que se ve de la otra cara de una carta."""
    return {"kind": card.kind.value, "color": card.color, "number": card.number}


Face = tuple[Kind, Color | None, int | None]


def _faces(colors: tuple[Color, ...], zeros: int, actions: dict[Kind, int], wilds: dict[Kind, int]) -> list[Face]:
    """Las caras de un lado del mazo, en orden fijo: por palo, los ceros, dos de
    cada número del 1 al 9 y las acciones; después, los comodines."""
    faces: list[Face] = []
    for color in colors:
        faces += [(Kind.NUMBER, color, 0)] * zeros
        for number in range(1, 10):
            faces += [(Kind.NUMBER, color, number)] * 2
        for action, copies in actions.items():
            faces += [(action, color, None)] * copies
    for wild, copies in wilds.items():
        faces += [(wild, None, None)] * copies
    return faces


CLASSIC_FACES = _faces(
    LIGHT_COLORS, 1, {Kind.PAUSA: 2, Kind.REMOLINO: 2, Kind.CARGA: 2}, {Kind.CAMALEON: 4, Kind.CAMALEON4: 4}
)
LIGHT_FACES = _faces(
    LIGHT_COLORS,
    0,
    {Kind.CARGA1: 2, Kind.REMOLINO: 2, Kind.PAUSA: 2, Kind.ECLIPSE: 2},
    {Kind.CAMALEON: 4, Kind.CAMALEON2: 4},
)
DARK_FACES = _faces(
    DARK_COLORS,
    0,
    {Kind.CARGA5: 2, Kind.REMOLINO: 2, Kind.PAUSA_TOTAL: 2, Kind.ECLIPSE: 2},
    {Kind.CAMALEON: 4, Kind.SABUESO: 4},
)
RELENTLESS_FACES = _faces(
    LIGHT_COLORS,
    2,
    {Kind.PAUSA: 3, Kind.REMOLINO: 3, Kind.CARGA: 3, Kind.CARGA4: 2, Kind.BARRIDO: 3, Kind.PAUSA_TOTAL: 2},
    {Kind.CAMALEON_REMOLINO4: 8, Kind.CAMALEON6: 4, Kind.CAMALEON10: 4, Kind.RULETA: 8},
)

DECK_SIZES = {Mode.CLASICO: 108, Mode.DOBLE: 112, Mode.SIN_TREGUA: 168}
DECK_SIZE = DECK_SIZES[Mode.CLASICO]  # el del Clásico, por compatibilidad


def full_deck(mode: Mode = Mode.CLASICO, rng: random.Random | None = None) -> list[PrismaCard]:
    """Todas las cartas de `mode`, en orden fijo (sin barajar).

    En Doble cara, cada carta junta una cara de luz y una de sombra. Con `rng`
    las parejas se hacen al azar (así, la cara que se ve de una carta no dice
    nada de la otra); sin él, en un orden fijo, para los tests.
    """
    if mode == Mode.DOBLE:
        dark = list(DARK_FACES)
        if rng is not None:
            rng.shuffle(dark)
        else:
            dark = dark[37:] + dark[:37]  # un desfase fijo, para no emparejar cada carta con su gemela
        return [
            PrismaCard(index, *light, back=PrismaCard(index, *shadow))
            for index, (light, shadow) in enumerate(zip(LIGHT_FACES, dark, strict=True))
        ]
    faces = RELENTLESS_FACES if mode == Mode.SIN_TREGUA else CLASSIC_FACES
    return [PrismaCard(index, *face) for index, face in enumerate(faces)]
