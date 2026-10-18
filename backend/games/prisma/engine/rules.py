"""Las reglas de una partida de Prisma: las del clásico, con sus opciones."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrismaRules:
    hand_size: int = 7  # cartas al empezar cada ronda
    # Desafío del Camaleón +4 (activado, como en el clásico). Con él, el +4 se
    # puede jugar de farol y el siguiente puede desafiarlo; sin él, el servidor
    # no deja jugarlo si tienes cartas del color que hay en la mesa.
    challenge: bool = True
    stack_draw2: bool = False  # opción de la casa: acumular Carga +2 sobre Carga +2
    stack_draw4: bool = False  # opción de la casa: acumular +4 sobre +4 (sin desafío)
    scoring: bool = False  # jugar a puntos varias rondas hasta la meta
    target: int = 500  # puntos para ganar la partida, si se juega a puntos
    catch_penalty: int = 2  # cartas por no decir "¡Última!" a tiempo

    def __post_init__(self) -> None:
        if not 1 <= self.hand_size <= 10:
            raise ValueError("Se reparten entre 1 y 10 cartas a cada jugador")
        if self.target < 1:
            raise ValueError("La meta tiene que ser de al menos 1 punto")

    @property
    def challenge_active(self) -> bool:
        """El desafío solo funciona si no se acumulan +4 (las dos cosas juntas no casan)."""
        return self.challenge and not self.stack_draw4
