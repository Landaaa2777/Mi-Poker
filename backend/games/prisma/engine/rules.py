"""Las reglas de una partida de Prisma: el modo de juego y sus opciones."""

from __future__ import annotations

from dataclasses import dataclass

from .cards import DECK_SIZES, Mode

MERCY_LIMIT = 25  # Sin tregua: con estas cartas o más, eliminado de la ronda
KNOCKOUT_POINTS = 250  # Sin tregua: puntos para el ganador por cada eliminado


@dataclass(frozen=True)
class PrismaRules:
    mode: Mode = Mode.CLASICO
    hand_size: int = 7  # cartas al empezar cada ronda
    # Desafío de los comodines que hacen robar y solo se juegan sin el color de
    # la mesa (el +4 del Clásico; el +2 y el Sabueso de Doble cara). Activado,
    # como en el clásico: se pueden jugar de farol y el siguiente puede
    # desafiarlos; sin él, el servidor no deja jugarlos si tienes ese color.
    challenge: bool = True
    stack_draw2: bool = False  # Clásico, opción de la casa: acumular Carga +2 sobre Carga +2
    stack_draw4: bool = False  # Clásico, opción de la casa: acumular +4 sobre +4 (sin desafío)
    scoring: bool = False  # jugar a puntos varias rondas hasta la meta
    target: int = 500  # puntos para ganar la partida, si se juega a puntos
    catch_penalty: int = 2  # cartas por no decir "¡Última!" a tiempo

    def __post_init__(self) -> None:
        if not 1 <= self.hand_size <= 10:
            raise ValueError("Se reparten entre 1 y 10 cartas a cada jugador")
        if self.target < 1:
            raise ValueError("La meta tiene que ser de al menos 1 punto")
        if self.mode != Mode.CLASICO and (self.stack_draw2 or self.stack_draw4):
            raise ValueError("Las opciones de acumular son solo del modo Clásico")

    @property
    def challenge_active(self) -> bool:
        """¿Se pueden desafiar los comodines restringidos?

        En Sin tregua no hay comodines restringidos. En el Clásico, el desafío no
        casa con acumular +4 (las dos cosas juntas no tienen sentido).
        """
        if self.mode == Mode.SIN_TREGUA:
            return False
        return self.challenge and not self.stack_draw4

    @property
    def deck_size(self) -> int:
        return DECK_SIZES[self.mode]

    @property
    def relentless(self) -> bool:
        return self.mode == Mode.SIN_TREGUA

    @property
    def double(self) -> bool:
        return self.mode == Mode.DOBLE
