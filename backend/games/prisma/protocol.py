"""Mensajes de Prisma entre cliente y servidor, por el WebSocket /ws/prisma/{partida_id}.

El cliente envía intenciones:
    {"type": "new_game", "config": {...}}            empezar una partida
    {"type": "play", "card": 17, "color": "halo", "declare": true}
                                                      jugar una carta (el color, solo en los comodines;
                                                      "declare" dice "¡Última!" a la vez)
    {"type": "draw"}                                  robar
    {"type": "pass"}                                  quedarse la carta robada y pasar
    {"type": "color", "color": "astro"}               elegir el color de la carta inicial
    {"type": "challenge"} / {"type": "accept"}        desafiar o aceptar un Camaleón +4
    {"type": "last"}                                  decir "¡Última!"
    {"type": "catch"}                                 pillar a quien no lo dijo
    {"type": "next_round"}                            siguiente ronda (si se juega a puntos)
    {"type": "restart"}                               empezar otra partida igual

Nunca viajan las cartas de los demás ni el mazo: solo cuántas tiene cada uno.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from core.bots import LEVEL_NAMES
from core.options import describe_options

MAX_BOTS = 5

Level = Literal["easy", "medium", "hard", "expert"]
ColorName = Literal["panal", "halo", "cumbre", "astro"]

LEVEL_CHOICES = [
    {"value": "easy", "label": "Fácil", "description": "Juega cualquier carta y se olvida de avisar."},
    {"value": "medium", "label": "Medio", "description": "Suelta primero lo que más vale."},
    {"value": "hard", "label": "Difícil", "description": "Recuerda qué colores te faltan y guarda sus comodines."},
    {"value": "expert", "label": "Experto", "description": "Además cierra bien la mano y nunca se despista."},
]


class PrismaConfig(BaseModel):
    """Lo que se elige antes de empezar."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    bots: int = Field(3, ge=1, le=MAX_BOTS, title="Rivales")
    difficulty: Level = Field(
        "medium", title="Dificultad de los bots", json_schema_extra={"choices": LEVEL_CHOICES}
    )
    challenge: bool = Field(
        True,
        title="Desafío del Camaleón +4",
        description="El +4 se puede jugar de farol y el siguiente puede desafiarlo, como en el clásico.",
    )
    scoring: bool = Field(
        False,
        title="Jugar a puntos",
        description="Varias rondas: quien gana suma lo que valen las cartas de los demás.",
    )
    target: int = Field(
        500,
        ge=50,
        le=2000,
        multiple_of=50,
        title="Meta de puntos",
        json_schema_extra={"presets": [200, 300, 500, 1000]},
    )
    stack_draw2: bool = Field(
        False,
        title="Acumular Carga +2",
        description="Opción de la casa: una Carga +2 sobre otra pasa la cuenta al siguiente.",
    )
    stack_draw4: bool = Field(
        False,
        title="Acumular Camaleón +4",
        description="Opción de la casa: un +4 sobre otro. Con ella no hay desafío.",
    )
    player_name: str = Field(
        "Tú", min_length=1, max_length=16, title="Tu nombre", json_schema_extra={"hidden": True}
    )


class NewGame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["new_game"]
    config: PrismaConfig = PrismaConfig()


class Play(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["play"]
    card: int = Field(ge=0, le=107)
    color: ColorName | None = None
    declare: bool = False


class ChooseColor(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["color"]
    color: ColorName


class Simple(BaseModel):
    """Intenciones sin más datos."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["draw", "pass", "challenge", "accept", "last", "catch", "next_round", "restart"]


ClientMessage = Annotated[NewGame | Play | ChooseColor | Simple, Field(discriminator="type")]
CLIENT_MESSAGE = TypeAdapter(ClientMessage)


def options() -> dict:
    """Opciones del panel de configuración."""
    return {
        "levels": [{"id": level, "name": name} for level, name in LEVEL_NAMES.items()],
        "max_bots": MAX_BOTS,
        "defaults": PrismaConfig().model_dump(),
        "fields": describe_options(PrismaConfig),
    }
