"""Mensajes del blackjack entre cliente y servidor, por el WebSocket /ws/blackjack/{partida_id}.

El cliente envía intenciones:
    {"type": "new_game", "config": {...}}     sentarse a una mesa nueva
    {"type": "bet", "amount": 100}            apostar y repartir la ronda
    {"type": "action", "action": "hit"}       hit, stand, double, split o surrender
    {"type": "insurance", "take": true}       asegurarse (o no) cuando el crupier enseña un As
    {"type": "restart"}                       volver a empezar con la misma configuración

El servidor responde como en todos los juegos: "hello" al conectar, "state"
tras cada cambio y "error" si una intención no se puede cumplir. La carta
tapada del crupier no viaja hasta que se destapa, y el zapato nunca.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from core.bots import LEVEL_NAMES
from core.options import describe_options

MAX_BOTS = 4
MAX_STACK = 1_000_000

Level = Literal["easy", "medium", "hard", "expert"]

LEVEL_CHOICES = [
    {"value": "easy", "label": "Fácil", "description": "Juega a corazonadas: pide y dobla sin criterio."},
    {"value": "medium", "label": "Medio", "description": "Sabe lo básico, pero se salta los matices."},
    {"value": "hard", "label": "Difícil", "description": "Sigue la estrategia básica al pie de la letra."},
    {"value": "expert", "label": "Experto", "description": "Estrategia básica con algún ajuste fino."},
]


class BlackjackConfig(BaseModel):
    """Lo que se elige antes de sentarse. Las fichas son virtuales."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # El título y los "extras" de cada campo son para el panel de opciones.
    bots: int = Field(2, ge=0, le=MAX_BOTS, title="Bots en la mesa")
    difficulty: Level = Field(
        "medium", title="Dificultad de los bots", json_schema_extra={"choices": LEVEL_CHOICES}
    )
    starting_stack: int = Field(
        1000,
        ge=10,
        le=MAX_STACK,
        multiple_of=10,
        title="Fichas iniciales",
        json_schema_extra={"presets": [500, 1000, 2000, 5000]},
    )
    min_bet: int = Field(
        10,
        ge=10,
        le=10_000,
        multiple_of=10,
        title="Apuesta mínima",
        json_schema_extra={"presets": [10, 20, 50, 100]},
    )
    max_bet: int = Field(
        500,
        ge=10,
        le=100_000,
        multiple_of=10,
        title="Apuesta máxima",
        json_schema_extra={"presets": [200, 500, 1000, 5000]},
    )
    dealer_hits_soft_17: bool = Field(
        False,
        title="El crupier pide con 17 blando",
        description="Si no, se planta con cualquier 17.",
    )
    surrender: bool = Field(
        False,
        title="Rendición tardía",
        description="Rendirte con tus dos primeras cartas te devuelve la mitad de la apuesta.",
    )
    player_name: str = Field(
        "Tú", min_length=1, max_length=16, title="Tu nombre", json_schema_extra={"hidden": True}
    )

    @model_validator(mode="after")
    def _check_bets(self) -> BlackjackConfig:
        if self.min_bet > self.max_bet:
            raise ValueError("La apuesta mínima no puede superar a la máxima")
        if self.starting_stack < self.min_bet:
            raise ValueError("Las fichas iniciales deben cubrir al menos la apuesta mínima")
        return self


class NewGame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["new_game"]
    config: BlackjackConfig = BlackjackConfig()


class Bet(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["bet"]
    amount: int = Field(ge=0)


class PlayerAction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["action"]
    action: Literal["hit", "stand", "double", "split", "surrender"]


class Insurance(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["insurance"]
    take: bool


class Restart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["restart"]


ClientMessage = Annotated[
    NewGame | Bet | PlayerAction | Insurance | Restart, Field(discriminator="type")
]
CLIENT_MESSAGE = TypeAdapter(ClientMessage)


def options() -> dict:
    """Opciones y límites del panel de configuración."""
    return {
        "levels": [{"id": level, "name": name} for level, name in LEVEL_NAMES.items()],
        "max_bots": MAX_BOTS,
        "max_stack": MAX_STACK,
        "defaults": BlackjackConfig().model_dump(),
        "fields": describe_options(BlackjackConfig),
    }
