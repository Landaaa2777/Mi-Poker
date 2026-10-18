"""Bots del blackjack. Solo dependen de la vista pública de la mesa.

Las fichas son virtuales: los bots juegan por entretenimiento, sin dinero real.
"""

from __future__ import annotations

import random

from .levels import BlackjackBot, EasyBot, ExpertBot, HardBot, MediumBot
from .strategy import basic_strategy, resolve, strategy_code

# Niveles de dificultad, del más flojo al más fuerte.
LEVELS: dict[str, type[BlackjackBot]] = {
    "easy": EasyBot,
    "medium": MediumBot,
    "hard": HardBot,
    "expert": ExpertBot,
}


def create_bot(
    level: str, name: str, rng: random.Random | None = None, units: int | None = None
) -> BlackjackBot:
    """Crea un bot del nivel indicado ("easy", "medium", "hard" o "expert")."""
    if level not in LEVELS:
        raise ValueError(f"Nivel desconocido: {level!r}. Opciones: {', '.join(LEVELS)}")
    return LEVELS[level](name, rng, units)


__all__ = [
    "LEVELS",
    "BlackjackBot",
    "EasyBot",
    "ExpertBot",
    "HardBot",
    "MediumBot",
    "basic_strategy",
    "create_bot",
    "resolve",
    "strategy_code",
]
