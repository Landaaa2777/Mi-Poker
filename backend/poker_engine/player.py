"""Estado de un asiento de la mesa."""

from __future__ import annotations

from dataclasses import dataclass, field

from .cards import Card


@dataclass
class Player:
    seat: int
    name: str
    stack: int
    hole_cards: list[Card] = field(default_factory=list)
    bet: int = 0  # apostado en la ronda de apuestas actual
    contributed: int = 0  # aportado al bote en toda la mano
    folded: bool = False
    in_hand: bool = False  # recibió cartas en la mano actual

    @property
    def live(self) -> bool:
        """Sigue disputando el bote."""
        return self.in_hand and not self.folded

    @property
    def all_in(self) -> bool:
        return self.live and self.stack == 0

    @property
    def can_act(self) -> bool:
        return self.live and self.stack > 0

    def commit(self, amount: int) -> int:
        """Pasa fichas del stack a la apuesta; devuelve lo realmente puesto."""
        amount = min(amount, self.stack)
        self.stack -= amount
        self.bet += amount
        self.contributed += amount
        return amount

    def reset_for_hand(self) -> None:
        self.hole_cards = []
        self.bet = 0
        self.contributed = 0
        self.folded = False
        self.in_hand = self.stack > 0
