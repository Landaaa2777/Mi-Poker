"""Las reglas de una mesa de blackjack. Todas las fichas son virtuales."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rules:
    """Reglas de la mesa. Los valores por defecto son los de la mayoría de casinos."""

    decks: int = 6
    penetration: float = 0.75  # dónde va la carta de corte
    min_bet: int = 10
    max_bet: int = 500
    bet_step: int = 10  # las apuestas van de 10 en 10: el 3 a 2 y el seguro dan fichas enteras
    dealer_hits_soft_17: bool = False  # por defecto el crupier se planta con 17 blando
    surrender: bool = False  # rendición tardía (tras mirar si el crupier tiene blackjack)
    max_hands: int = 4  # como mucho 4 manos tras dividir
    double_after_split: bool = True
    resplit_aces: bool = False  # los ases divididos no se vuelven a dividir

    def __post_init__(self) -> None:
        if self.bet_step < 2 or self.bet_step % 2:
            raise ValueError("Las apuestas deben ir de un número par de fichas en un número par")
        if not 0 < self.min_bet <= self.max_bet:
            raise ValueError("La apuesta mínima no puede superar a la máxima")
        if self.min_bet % self.bet_step or self.max_bet % self.bet_step:
            raise ValueError(f"Las apuestas límite deben ir de {self.bet_step} en {self.bet_step}")
        if self.max_hands < 1:
            raise ValueError("Hace falta al menos una mano")

    def check_bet(self, bet: int, stack: int) -> str | None:
        """El problema de una apuesta, en una frase, o None si vale."""
        if bet < self.min_bet or bet > self.max_bet:
            return f"La apuesta debe estar entre {self.min_bet} y {self.max_bet}"
        if bet % self.bet_step:
            return f"La apuesta va de {self.bet_step} en {self.bet_step}"
        if bet > stack:
            return "No tienes fichas suficientes para esa apuesta"
        return None
