"""Bots de poker. Solo dependen de la vista pública del motor.

Las fichas son virtuales: los bots juegan por entretenimiento, sin dinero real.
"""

from __future__ import annotations

import random

from .base import Bot, Spot
from .easy import EasyBot
from .equity import estimate_equity
from .expert import ExpertBot
from .hard import HardBot
from .medium import MediumBot
from .personalities import NEUTRAL, PERSONALITIES, Personality, pick_personalities

# Niveles de dificultad, del más flojo al más fuerte.
LEVELS: dict[str, type[Bot]] = {
    "easy": EasyBot,
    "medium": MediumBot,
    "hard": HardBot,
    "expert": ExpertBot,
}


def create_bot(
    level: str,
    personality: Personality | None = None,
    rng: random.Random | None = None,
    simulations: int | None = None,
) -> Bot:
    """Crea un bot del nivel indicado ("easy", "medium", "hard" o "expert")."""
    if level not in LEVELS:
        raise ValueError(f"Nivel desconocido: {level!r}. Opciones: {', '.join(LEVELS)}")
    return LEVELS[level](personality, rng, simulations)


__all__ = [
    "LEVELS",
    "NEUTRAL",
    "PERSONALITIES",
    "Bot",
    "EasyBot",
    "ExpertBot",
    "HardBot",
    "MediumBot",
    "Personality",
    "Spot",
    "create_bot",
    "estimate_equity",
    "pick_personalities",
]
