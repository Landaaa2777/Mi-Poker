"""Nombres y personalidades de los bots.

La personalidad ajusta levemente los umbrales de la estrategia del nivel; no
cambia la información que recibe el bot.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Personality:
    name: str
    style: str  # descripción corta para mostrar en la interfaz
    tightness: float = 1.0  # > 1 juega menos manos, < 1 juega más
    aggression: float = 1.0  # > 1 apuesta y sube más, < 1 pasa e iguala más
    bluff: float = 1.0  # multiplica la frecuencia de faroles


NEUTRAL = Personality("Bot", "equilibrado")

PERSONALITIES: tuple[Personality, ...] = (
    Personality("Granito", "tight pasivo", tightness=1.15, aggression=0.88, bluff=0.80),
    Personality("Ventisca", "tight agresivo", tightness=1.12, aggression=1.15, bluff=1.00),
    Personality("Chispa", "suelto agresivo", tightness=0.88, aggression=1.15, bluff=1.20),
    Personality("Remolino", "suelto pasivo", tightness=0.86, aggression=0.88, bluff=0.85),
    Personality("Brújula", "equilibrado", tightness=1.00, aggression=1.00, bluff=1.00),
    Personality("Zorro Gris", "farolero", tightness=0.95, aggression=1.05, bluff=1.30),
    Personality("Doña Calma", "paciente", tightness=1.10, aggression=0.95, bluff=0.90),
    Personality("Tuerca", "calculador", tightness=1.05, aggression=1.00, bluff=0.90),
    Personality("Relámpago", "impulsivo", tightness=0.90, aggression=1.12, bluff=1.10),
    Personality("Marea", "cambiante", tightness=1.00, aggression=1.06, bluff=1.10),
)


def pick_personalities(count: int, rng: random.Random | None = None) -> list[Personality]:
    """`count` personalidades distintas, para que no se repitan nombres en la mesa."""
    if not 0 <= count <= len(PERSONALITIES):
        raise ValueError(f"Hay {len(PERSONALITIES)} personalidades disponibles")
    return (rng or random).sample(PERSONALITIES, count)
