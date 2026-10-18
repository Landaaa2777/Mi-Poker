"""Bots de Prisma. Solo dependen de la vista pública de la mesa."""

from __future__ import annotations

import random

from .levels import EasyBot, ExpertBot, HardBot, MediumBot, Move, PrismaBot, missing_colors

# Niveles de dificultad, del más flojo al más fuerte.
LEVELS: dict[str, type[PrismaBot]] = {
    "easy": EasyBot,
    "medium": MediumBot,
    "hard": HardBot,
    "expert": ExpertBot,
}


def create_bot(level: str, name: str, rng: random.Random | None = None) -> PrismaBot:
    """Crea un bot del nivel indicado ("easy", "medium", "hard" o "expert")."""
    if level not in LEVELS:
        raise ValueError(f"Nivel desconocido: {level!r}. Opciones: {', '.join(LEVELS)}")
    return LEVELS[level](name, rng)


__all__ = [
    "LEVELS",
    "EasyBot",
    "ExpertBot",
    "HardBot",
    "MediumBot",
    "Move",
    "PrismaBot",
    "create_bot",
    "missing_colors",
]
