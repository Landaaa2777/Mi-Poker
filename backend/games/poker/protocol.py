"""Mensajes del poker entre cliente y servidor, por el WebSocket /ws/poker/{partida_id}.

El cliente envía intenciones:
    {"type": "new_game", "config": {...}}     empezar una partida
    {"type": "action", "action": "raise", "amount": 400}
    {"type": "next_hand"}                     repartir la siguiente mano
    {"type": "restart"}                       reiniciar con la misma configuración

El servidor responde:
    {"type": "hello", "options": {...}, "user": {...} | null, "state": {...} | null}
                                                                 al conectar
    {"type": "state", "state": {...}}                            tras cada cambio
    {"type": "error", "message": "..."}                          intención rechazada

`user` es la cuenta con la que se ha conectado ({"username", "balance"}), o
null si juega como invitado. Con cuenta, cada estado lleva además "balance":
sus fichas en ese momento, contando las de la mesa; para un invitado es null.
Las cuentas van por HTTP: ver `accounts_api.py`.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from core import NOTICE
from games.poker.bots import LEVELS
from games.poker.engine import MAX_PLAYERS, ActionType

MAX_BOTS = MAX_PLAYERS - 1
MAX_STACK = 1_000_000

Level = Literal["easy", "medium", "hard", "expert"]

# Cómo juega cada nivel, en una frase, para el panel de opciones.
LEVEL_CHOICES = [
    {"value": "easy", "label": "Fácil", "description": "Juega casi todas las manos y paga de más."},
    {"value": "medium", "label": "Medio", "description": "Elige sus manos y respeta las apuestas grandes."},
    {"value": "hard", "label": "Difícil", "description": "Calcula sus probabilidades y a veces farolea."},
    {"value": "expert", "label": "Experto", "description": "Además observa cómo juegas y se adapta a ti."},
]


class TableConfig(BaseModel):
    """Lo que se elige en el panel antes de empezar. Las fichas son virtuales."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # El título y los "extras" de cada campo son para el panel de opciones del menú.
    bots: int = Field(3, ge=1, le=MAX_BOTS, title="Bots")
    difficulty: Level = Field(
        "medium", title="Dificultad", json_schema_extra={"choices": LEVEL_CHOICES}
    )
    starting_stack: int = Field(
        1000,
        ge=1,
        le=MAX_STACK,
        title="Fichas iniciales",
        json_schema_extra={"presets": [500, 1000, 2000, 5000]},
    )
    small_blind: int = Field(5, ge=1, le=MAX_STACK, title="Ciega pequeña")
    big_blind: int = Field(10, ge=1, le=MAX_STACK, title="Ciega grande")
    player_name: str = Field(
        "Tú", min_length=1, max_length=16, title="Tu nombre", json_schema_extra={"hidden": True}
    )

    @model_validator(mode="after")
    def _check_blinds(self) -> TableConfig:
        if self.small_blind > self.big_blind:
            raise ValueError("La ciega pequeña no puede superar a la grande")
        if self.starting_stack < self.big_blind:
            raise ValueError("Las fichas iniciales deben cubrir al menos la ciega grande")
        return self


class RoomConfig(TableConfig):
    """Opciones de una sala con amigos: las de siempre, pero los bots son opcionales.

    El nombre de cada persona en la mesa es el de su cuenta; el que traiga el
    modelo no se usa.
    """

    bots: int = Field(0, ge=0, le=MAX_BOTS, title="Bots")


class NewGame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["new_game"]
    config: TableConfig = TableConfig()


class PlayerAction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["action"]
    action: ActionType
    amount: int = Field(0, ge=0)


class NextHand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["next_hand"]


class Restart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["restart"]


ClientMessage = Annotated[
    NewGame | PlayerAction | NextHand | Restart, Field(discriminator="type")
]
CLIENT_MESSAGE = TypeAdapter(ClientMessage)


def options() -> dict:
    """Opciones y límites del panel de configuración."""
    defaults = TableConfig()
    return {
        "notice": NOTICE,
        "levels": [{"id": level, "name": bot.level_name} for level, bot in LEVELS.items()],
        "max_bots": MAX_BOTS,
        "max_stack": MAX_STACK,
        "defaults": defaults.model_dump(),
    }
