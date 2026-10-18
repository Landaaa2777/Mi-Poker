"""Los bots del blackjack, del más flojo al más fuerte.

Todos reciben solo la vista de la mesa que tiene cualquier jugador (sus cartas,
las de los demás, que en el blackjack van boca arriba, y la carta vista del
crupier). Nunca ven la carta tapada ni el zapato, y ninguno cuenta cartas.

- Fácil: decisiones erráticas.
- Medio: una versión incompleta de la estrategia básica.
- Difícil: la estrategia básica correcta para las reglas de la mesa.
- Experto: como Difícil, más un ajuste según las cartas de su propia mano.
"""

from __future__ import annotations

import random

from core.bots import LEVEL_NAMES
from core.cards import Card
from core.shuffle import SYSTEM_RNG
from games.blackjack.engine import Action, Rules, TableView, card_value, hand_total

from .strategy import basic_strategy

BET_UNITS = (1, 1, 2, 2, 3, 5)  # cada bot apuesta siempre lo mismo: una de estas veces la mínima


class BlackjackBot:
    """Base de todos los niveles: cómo apostar y leer su mano de la vista."""

    level = "medium"

    def __init__(self, name: str, rng: random.Random | None = None, units: int | None = None) -> None:
        self.name = name
        self.rng = rng or SYSTEM_RNG
        # Apuesta fija: siempre las mismas veces la apuesta mínima.
        self.units = units if units is not None else self.rng.choice(BET_UNITS)

    @property
    def level_name(self) -> str:
        return LEVEL_NAMES[self.level]

    def bet(self, view: TableView) -> int | None:
        """Cuánto apuesta en la próxima ronda; None si no le quedan fichas."""
        rules = view.rules
        stack = view.seat(view.viewer_seat).stack
        bet = min(rules["min_bet"] * self.units, rules["max_bet"], stack)
        bet -= bet % rules["bet_step"]
        return bet if bet >= rules["min_bet"] else None

    def insure(self, view: TableView) -> bool:
        """¿Se asegura cuando el crupier enseña un As? La buena respuesta es casi siempre no."""
        return False

    def decide(self, view: TableView) -> Action:
        raise NotImplementedError

    # --- Para leer la vista ---

    @staticmethod
    def my_cards(view: TableView) -> list[Card]:
        hand = view.seat(view.viewer_seat).hands[view.to_act_hand]
        return [Card.parse(text) for text in hand.cards]

    @staticmethod
    def dealer_up(view: TableView) -> Card:
        return Card.parse(view.dealer_up)

    @staticmethod
    def legal(view: TableView) -> list[Action]:
        if view.legal_actions is None:
            raise ValueError("No es el turno de este bot")
        return [Action(action) for action in view.legal_actions]

    @staticmethod
    def rules_of(view: TableView) -> Rules:
        rules = view.rules
        return Rules(
            decks=rules["decks"],
            min_bet=rules["min_bet"],
            max_bet=rules["max_bet"],
            bet_step=rules["bet_step"],
            dealer_hits_soft_17=rules["dealer_hits_soft_17"],
            surrender=rules["surrender"],
            max_hands=rules["max_hands"],
            double_after_split=rules["double_after_split"],
        )


class EasyBot(BlackjackBot):
    """Errático: pide o se planta según le da, dobla y divide sin criterio y se asegura a menudo."""

    level = "easy"

    def insure(self, view: TableView) -> bool:
        return self.rng.random() < 0.5

    def decide(self, view: TableView) -> Action:
        legal = self.legal(view)
        if self.rng.random() < 0.2:
            return self.rng.choice(legal)  # a veces, cualquier cosa
        total = hand_total(self.my_cards(view))[0]
        if Action.SPLIT in legal and self.rng.random() < 0.5:
            return Action.SPLIT
        if Action.DOUBLE in legal and self.rng.random() < 0.15:
            return Action.DOUBLE
        # Se planta a partir de un número distinto cada vez, entre 12 y 17.
        return Action.HIT if total < self.rng.randint(12, 17) else Action.STAND


class MediumBot(BlackjackBot):
    """La estrategia básica a medias: lo más conocido, sin los matices."""

    level = "medium"

    def decide(self, view: TableView) -> Action:
        legal = self.legal(view)
        cards = self.my_cards(view)
        up = card_value(self.dealer_up(view))
        total, soft = hand_total(cards)
        if Action.SPLIT in legal and card_value(cards[0]) in (8, 11):
            return Action.SPLIT  # solo divide ases y ochos
        if soft:
            return Action.HIT if total <= 17 else Action.STAND
        if total <= 9:
            return Action.HIT
        if total <= 11:
            if Action.DOUBLE in legal and up <= 9:
                return Action.DOUBLE
            return Action.HIT
        if total <= 16:
            # Se planta si el crupier enseña una carta floja (2 a 6) y pide si no.
            return Action.STAND if up <= 6 else Action.HIT
        return Action.STAND


class HardBot(BlackjackBot):
    """La estrategia básica correcta para las reglas de la mesa."""

    level = "hard"

    def decide(self, view: TableView) -> Action:
        return basic_strategy(self.my_cards(view), self.dealer_up(view), self.rules_of(view), self.legal(view))


class ExpertBot(HardBot):
    """Estrategia básica más un ajuste según su propia mano (sigue sin contar cartas).

    Con 16 de tres cartas o más contra un 10 del crupier se planta: las cartas
    pequeñas que ya tiene hacen más probable que la siguiente lo pase de 21.
    """

    level = "expert"

    def decide(self, view: TableView) -> Action:
        cards = self.my_cards(view)
        total, soft = hand_total(cards)
        up = card_value(self.dealer_up(view))
        if not soft and total == 16 and len(cards) >= 3 and up == 10 and Action.STAND in self.legal(view):
            return Action.STAND
        return super().decide(view)
