"""Interfaz común de los bots.

Un bot recibe únicamente una `TableView` (la mesa pública más sus propias
cartas) y devuelve fold, call o raise con monto. Nunca ve cartas ajenas ni el
mazo: cambiar de nivel cambia la estrategia, no la información.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from functools import cached_property

from poker_engine import Action, ActionType, Card, LegalActions, SeatView, TableView

from .personalities import NEUTRAL, Personality

FOLD = Action(ActionType.FOLD)
CALL = Action(ActionType.CALL)  # el motor lo trata como "pasar" si no hay nada que igualar


class Spot:
    """La situación del bot en su turno, calculada solo a partir de su vista."""

    def __init__(self, view: TableView) -> None:
        if view.legal_actions is None or view.viewer_seat is None:
            raise ValueError("No es el turno de este bot")
        self.view = view
        self.legal: LegalActions = view.legal_actions
        self.me: SeatView = next(s for s in view.seats if s.seat == view.viewer_seat)
        self.hole: tuple[Card, ...] = view.hole_cards
        self.board: tuple[Card, ...] = view.board
        self.preflop = view.phase == "preflop"
        self.street = view.phase
        self.big_blind = view.big_blind
        self.pot = view.pot
        self.to_call = self.legal.call_amount
        self.stack = self.me.stack

    @cached_property
    def rivals(self) -> list[SeatView]:
        """Rivales que siguen disputando el bote."""
        return [
            s for s in self.view.seats if s.seat != self.me.seat and s.status in ("active", "all_in")
        ]

    @property
    def opponents(self) -> int:
        return len(self.rivals)

    @cached_property
    def players_dealt(self) -> int:
        return sum(s.status != "out" for s in self.view.seats)

    @property
    def pot_odds(self) -> float:
        """Equity mínima para que igualar no pierda fichas."""
        return self.to_call / (self.pot + self.to_call) if self.to_call else 0.0

    @property
    def bet_fraction(self) -> float:
        """Tamaño de la apuesta a igualar, como fracción del bote que había antes."""
        before = self.pot - self.to_call
        return self.to_call / before if self.to_call and before > 0 else 0.0

    @cached_property
    def _street_actions(self) -> list[tuple[int, str]]:
        actions: list[tuple[int, str]] = []
        for event in self.view.events:
            if event.kind == "board":
                actions = []
            elif event.kind == "action" and event.seat is not None:
                actions.append((event.seat, event.action))
        return actions

    @property
    def raises(self) -> int:
        """Apuestas y subidas en esta calle (las ciegas no cuentan)."""
        return sum(action == "raise" for _, action in self._street_actions)

    @property
    def limpers(self) -> int:
        return sum(action == "call" for _, action in self._street_actions) if self.preflop else 0

    @property
    def aggressor_seat(self) -> int | None:
        """Quién hizo la última apuesta o subida de esta calle."""
        raisers = [seat for seat, action in self._street_actions if action == "raise"]
        return raisers[-1] if raisers else None

    @cached_property
    def preflop_aggressor_seat(self) -> int | None:
        last = None
        for event in self.view.events:
            if event.kind == "board":
                break
            if event.kind == "action" and event.action == "raise":
                last = event.seat
        return last

    @cached_property
    def _postflop_order(self) -> list[int]:
        """Asientos con cartas, empezando a la izquierda del botón."""
        seats = [s.seat for s in self.view.seats if s.status != "out"]
        button = self.view.button_seat or 0
        return [s for s in seats if s > button] + [s for s in seats if s <= button]

    @cached_property
    def seats_behind(self) -> int:
        """Rivales que todavía pueden actuar después del bot en esta calle."""
        order = self._postflop_order
        if self.preflop:
            # Preflop empieza a hablar el jugador tras la ciega grande.
            order = order[::-1] if len(order) == 2 else order[2:] + order[:2]
        can_act = {s.seat for s in self.view.seats if s.status == "active"}
        mine = order.index(self.me.seat)
        return sum(seat in can_act for seat in order[mine + 1 :])

    @property
    def in_position(self) -> bool:
        """El bot habla el último después del flop."""
        order = self._postflop_order
        live = {s.seat for s in self.rivals}
        return not any(seat in live for seat in order[order.index(self.me.seat) + 1 :])

    def bet_to(self, pot_fraction: float) -> int:
        """Apuesta total que equivale a apostar esa fracción del bote tras igualar."""
        return round(self.view.current_bet + pot_fraction * (self.pot + self.to_call))

    def blinds_to(self, big_blinds: float) -> int:
        return round(big_blinds * self.big_blind)


class Bot(ABC):
    """Base de todos los niveles. Cada nivel implementa solo `_choose`."""

    level: str = ""
    level_name: str = ""
    default_simulations: int = 0  # simulaciones Monte Carlo por decisión (0 = no usa)

    def __init__(
        self,
        personality: Personality | None = None,
        rng: random.Random | None = None,
        simulations: int | None = None,
    ) -> None:
        self.personality = personality or NEUTRAL
        self.rng = rng or random.Random()
        self.simulations = self.default_simulations if simulations is None else simulations

    @property
    def name(self) -> str:
        return self.personality.name

    def decide(self, view: TableView) -> Action:
        """Decide la jugada del bot. Siempre devuelve una acción legal."""
        spot = Spot(view)
        return _legalize(self._choose(spot), spot.legal)

    def observe(self, view: TableView) -> None:
        """Aviso opcional al terminar cada mano, con la misma vista de siempre."""

    @abstractmethod
    def _choose(self, spot: Spot) -> Action:
        """Devuelve FOLD, CALL o un RAISE con el monto total deseado."""

    def _chance(self, probability: float) -> bool:
        return self.rng.random() < probability

    def _raise(self, spot: Spot, amount: float) -> Action:
        """Sube a `amount`; si eso compromete casi todo el stack, va all-in."""
        legal = spot.legal
        if not legal.can_raise:
            return CALL
        amount = max(legal.min_raise_to, min(legal.max_raise_to, round(amount)))
        if amount - spot.me.bet >= 0.7 * spot.stack:
            amount = legal.max_raise_to
        return Action(ActionType.RAISE, amount)


def _legalize(action: Action, legal: LegalActions) -> Action:
    """Convierte la intención del bot en una acción que el motor acepta."""
    if action.type is ActionType.FOLD:
        return CALL if legal.can_check else FOLD
    if action.type is ActionType.RAISE and legal.can_raise:
        amount = max(legal.min_raise_to, min(legal.max_raise_to, int(action.amount)))
        return Action(ActionType.RAISE, amount)
    return CALL
