"""Acciones que puede enviar un jugador (humano o bot)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ActionType(StrEnum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass(frozen=True, slots=True)
class Action:
    """Intención de un jugador.

    En RAISE, `amount` es el total al que queda su apuesta en la ronda
    ("raise 400" = subir a 400), no el incremento. También sirve para abrir
    la apuesta cuando nadie ha apostado. En el resto de acciones se ignora.
    """

    type: ActionType
    amount: int = 0


class IllegalActionError(ValueError):
    """La acción no está permitida en el estado actual de la mano."""
