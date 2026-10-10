"""Mensajes entre cliente y servidor.

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

`user` es la cuenta con la que se ha conectado, o null si juega como invitado.
Las cuentas van por HTTP: ver `accounts_api.py`.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from bots import LEVELS
from poker_engine import MAX_PLAYERS, ActionType

NOTICE = "Solo para entretenimiento. Sin dinero real."
MAX_BOTS = MAX_PLAYERS - 1
MAX_STACK = 1_000_000

Level = Literal["easy", "medium", "hard", "expert"]


class TableConfig(BaseModel):
    """Lo que se elige en el panel antes de empezar. Las fichas son virtuales."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    bots: int = Field(3, ge=1, le=MAX_BOTS)
    difficulty: Level = "medium"
    starting_stack: int = Field(1000, ge=1, le=MAX_STACK)
    small_blind: int = Field(5, ge=1, le=MAX_STACK)
    big_blind: int = Field(10, ge=1, le=MAX_STACK)
    player_name: str = Field("Tú", min_length=1, max_length=16)

    @model_validator(mode="after")
    def _check_blinds(self) -> TableConfig:
        if self.small_blind > self.big_blind:
            raise ValueError("La ciega pequeña no puede superar a la grande")
        if self.starting_stack < self.big_blind:
            raise ValueError("Las fichas iniciales deben cubrir al menos la ciega grande")
        return self


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
