"""Mensajes de Prisma entre cliente y servidor, por el WebSocket /ws/prisma/{partida_id}.

El cliente envía intenciones:
    {"type": "new_game", "config": {...}}            empezar una partida
    {"type": "play", "card": 17, "color": "halo", "declare": true, "target": 2}
                                                      jugar una carta (el color, solo en los comodines;
                                                      "declare" dice "¡Última!" a la vez; "target",
                                                      con quién se cambia la mano con el 7 de Sin tregua)
    {"type": "draw"}                                  robar
    {"type": "pass"}                                  quedarse la carta robada y pasar
    {"type": "color", "color": "astro"}               elegir el color (carta inicial, o tras un Eclipse)
    {"type": "roulette", "color": "halo"}             Sin tregua: el color que paras con la Ruleta
    {"type": "challenge"} / {"type": "accept"}        desafiar o aceptar un Camaleón +4
    {"type": "last"}                                  decir "¡Última!"
    {"type": "catch"}                                 pillar a quien no lo dijo
    {"type": "next_round"}                            siguiente ronda (si se juega a puntos)
    {"type": "restart"}                               empezar otra partida igual

Nunca viajan las cartas de los demás ni el mazo: solo cuántas tiene cada uno.
En Doble cara, además, la otra cara de las cartas de los demás, que en ese
modo está a la vista (ver engine/views.py).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from core.bots import LEVEL_NAMES
from core.options import describe_options

from .engine import Mode, PrismaRules

MAX_BOTS = 5
MAX_CARD_ID = 167  # el mazo más grande, el de Sin tregua, tiene 168 cartas

Level = Literal["easy", "medium", "hard", "expert"]
ModeName = Literal["clasico", "doble_cara", "sin_tregua"]
# Los palos de siempre y los de la cara de sombra de Doble cara.
ColorName = Literal["panal", "halo", "cumbre", "astro", "brasa", "ambar", "jade", "indigo"]

MODE_CHOICES = [
    {"value": "clasico", "label": "Clásico", "description": "Las reglas de siempre, con 108 cartas."},
    {
        "value": "doble_cara",
        "label": "Doble cara",
        "description": "Cartas de luz y de sombra: el Eclipse le da la vuelta a toda la mesa.",
    },
    {
        "value": "sin_tregua",
        "label": "Sin tregua",
        "description": "168 cartas, cargas que se acumulan, +10, la Ruleta y fuera con 25 cartas.",
    },
]

LEVEL_CHOICES = [
    {"value": "easy", "label": "Fácil", "description": "Juega cualquier carta y se olvida de avisar."},
    {"value": "medium", "label": "Medio", "description": "Suelta primero lo que más vale."},
    {"value": "hard", "label": "Difícil", "description": "Recuerda qué colores te faltan y guarda sus comodines."},
    {"value": "expert", "label": "Experto", "description": "Además cierra bien la mano y nunca se despista."},
]


class PrismaConfig(BaseModel):
    """Lo que se elige antes de empezar."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mode: ModeName = Field("clasico", title="Modo de juego", json_schema_extra={"choices": MODE_CHOICES})
    bots: int = Field(3, ge=1, le=MAX_BOTS, title="Rivales")
    difficulty: Level = Field(
        "medium", title="Dificultad de los bots", json_schema_extra={"choices": LEVEL_CHOICES}
    )
    challenge: bool = Field(
        True,
        title="Desafío de los comodines",
        description="El Camaleón +4 (y en Doble cara, el +2 y el Sabueso) se puede jugar de farol y desafiar.",
        json_schema_extra={"when": {"mode": ["clasico", "doble_cara"]}},
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
        description="Lo habitual: 500 (en Sin tregua, 1000).",
        json_schema_extra={"presets": [200, 300, 500, 1000], "when": {"scoring": [True]}},
    )
    stack_draw2: bool = Field(
        False,
        title="Acumular Carga +2",
        description="Opción de la casa del Clásico: una Carga +2 sobre otra pasa la cuenta al siguiente.",
        json_schema_extra={"when": {"mode": ["clasico"]}},
    )
    stack_draw4: bool = Field(
        False,
        title="Acumular Camaleón +4",
        description="Opción de la casa del Clásico: un +4 sobre otro. Con ella no hay desafío.",
        json_schema_extra={"when": {"mode": ["clasico"]}},
    )
    player_name: str = Field(
        "Tú", min_length=1, max_length=16, title="Tu nombre", json_schema_extra={"hidden": True}
    )


class RoomConfig(PrismaConfig):
    """Opciones de una sala con amigos: las de siempre, pero los bots son opcionales.

    El nombre de cada persona en la mesa es el de su cuenta.
    """

    bots: int = Field(0, ge=0, le=MAX_BOTS, title="Bots")


def rules_for(config: PrismaConfig) -> PrismaRules:
    """Las reglas de una partida con estas opciones. Las de la casa (acumular) solo
    cuentan en el Clásico; en los otros modos se ignoran."""
    mode = Mode(config.mode)
    classic = mode == Mode.CLASICO
    return PrismaRules(
        mode=mode,
        challenge=config.challenge,
        stack_draw2=config.stack_draw2 and classic,
        stack_draw4=config.stack_draw4 and classic,
        scoring=config.scoring,
        target=config.target,
    )


class NewGame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["new_game"]
    config: PrismaConfig = PrismaConfig()


class Play(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["play"]
    card: int = Field(ge=0, le=MAX_CARD_ID)
    color: ColorName | None = None
    declare: bool = False
    target: int | None = Field(None, ge=0, le=MAX_BOTS)  # con quién se cambia la mano (el 7)


class ChooseColor(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["color"]
    color: ColorName


class Roulette(BaseModel):
    """Sin tregua: el color que para la Ruleta que me ha tocado."""

    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["roulette"]
    color: ColorName


class Simple(BaseModel):
    """Intenciones sin más datos."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["draw", "pass", "challenge", "accept", "last", "catch", "next_round", "restart"]


ClientMessage = Annotated[NewGame | Play | ChooseColor | Roulette | Simple, Field(discriminator="type")]
CLIENT_MESSAGE = TypeAdapter(ClientMessage)


def options() -> dict:
    """Opciones del panel de configuración."""
    return {
        "levels": [{"id": level, "name": name} for level, name in LEVEL_NAMES.items()],
        "max_bots": MAX_BOTS,
        "defaults": PrismaConfig().model_dump(),
        "fields": describe_options(PrismaConfig),
    }
