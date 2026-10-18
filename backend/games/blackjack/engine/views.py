"""Lo que ve cada jugador de la mesa de blackjack.

Las cartas de los jugadores van boca arriba (en el blackjack todos las ven),
pero la segunda carta del crupier va tapada hasta que la destapa, y el zapato
no se ve nunca. Esta vista es lo único que reciben el navegador y los bots.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .game import BlackjackGame, Event, Phase, PlayerHand, Seat
from .hand import hand_total


@dataclass(frozen=True)
class HandView:
    cards: tuple[str, ...]
    bet: int
    total: int
    soft: bool
    status: str
    result: str | None
    payout: int
    doubled: bool
    from_split: bool


@dataclass(frozen=True)
class SeatView:
    seat: int
    name: str
    stack: int
    hands: tuple[HandView, ...]
    insurance: int
    insurance_pending: bool
    can_bet: bool  # le quedan fichas para la apuesta mínima


@dataclass(frozen=True)
class TableView:
    phase: str
    round_number: int
    rules: dict[str, Any]
    dealer_cards: tuple[str | None, ...]  # None = la carta tapada
    dealer_total: int  # de las cartas que se ven
    dealer_soft: bool
    hole_hidden: bool
    seats: tuple[SeatView, ...]
    to_act_seat: int | None
    to_act_hand: int | None
    viewer_seat: int | None
    legal_actions: tuple[str, ...] | None  # solo si le toca a quien mira
    insurance_offered: bool  # quien mira tiene que decidir si se asegura
    shoe_remaining: int
    shoe_total: int
    cut_reached: bool
    events: tuple[dict[str, Any], ...]

    @property
    def dealer_up(self) -> str | None:
        """La carta del crupier que se ve desde el principio."""
        return self.dealer_cards[0] if self.dealer_cards else None

    def seat(self, index: int) -> SeatView:
        return self.seats[index]

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "round_number": self.round_number,
            "rules": self.rules,
            "dealer": {
                "cards": list(self.dealer_cards),
                "total": self.dealer_total,
                "soft": self.dealer_soft,
                "hole_hidden": self.hole_hidden,
            },
            "seats": [
                {
                    "seat": seat.seat,
                    "name": seat.name,
                    "stack": seat.stack,
                    "hands": [hand.__dict__ | {"cards": list(hand.cards)} for hand in seat.hands],
                    "insurance": seat.insurance,
                    "insurance_pending": seat.insurance_pending,
                    "can_bet": seat.can_bet,
                }
                for seat in self.seats
            ],
            "to_act_seat": self.to_act_seat,
            "to_act_hand": self.to_act_hand,
            "viewer_seat": self.viewer_seat,
            "legal_actions": list(self.legal_actions) if self.legal_actions is not None else None,
            "insurance_offered": self.insurance_offered,
            "shoe": {
                "remaining": self.shoe_remaining,
                "total": self.shoe_total,
                "cut_reached": self.cut_reached,
            },
            "events": list(self.events),
        }


def _hand_view(hand: PlayerHand) -> HandView:
    return HandView(
        cards=tuple(str(card) for card in hand.cards),
        bet=hand.bet,
        total=hand.total,
        soft=hand.soft,
        status=hand.status.value,
        result=hand.result.value if hand.result else None,
        payout=hand.payout,
        doubled=hand.doubled,
        from_split=hand.from_split,
    )


def _seat_view(game: BlackjackGame, seat: Seat) -> SeatView:
    return SeatView(
        seat=seat.seat,
        name=seat.name,
        stack=seat.stack,
        hands=tuple(_hand_view(hand) for hand in seat.hands),
        insurance=seat.insurance,
        insurance_pending=seat.insurance_pending,
        can_bet=game.can_bet(seat.seat),
    )


def _event(event: Event) -> dict[str, Any]:
    return {
        "kind": event.kind,
        "seat": event.seat,
        "hand": event.hand,
        "card": str(event.card) if event.card is not None else None,
        "amount": event.amount,
        "action": event.action,
        "result": event.result,
    }


def table_view(game: BlackjackGame, viewer_seat: int | None = None) -> TableView:
    """La mesa tal como la ve `viewer_seat` (o un espectador, con None)."""
    hidden = not game.hole_revealed and len(game.dealer) > 1
    visible = game.dealer[:1] if hidden else game.dealer
    total, soft = hand_total(visible) if visible else (0, False)
    dealer_cards = tuple(str(card) for card in visible) + ((None,) if hidden else ())
    to_act = game.to_act
    legal = None
    if viewer_seat is not None and to_act is not None and to_act[0] == viewer_seat:
        legal = tuple(action.value for action in game.legal_actions(viewer_seat))
    rules = game.rules
    return TableView(
        phase=game.phase.value,
        round_number=game.round_number,
        rules={
            "min_bet": rules.min_bet,
            "max_bet": rules.max_bet,
            "bet_step": rules.bet_step,
            "decks": rules.decks,
            "dealer_hits_soft_17": rules.dealer_hits_soft_17,
            "surrender": rules.surrender,
            "max_hands": rules.max_hands,
            "double_after_split": rules.double_after_split,
        },
        dealer_cards=dealer_cards,
        dealer_total=total,
        dealer_soft=soft,
        hole_hidden=hidden,
        seats=tuple(_seat_view(game, seat) for seat in game.seats),
        to_act_seat=to_act[0] if to_act else None,
        to_act_hand=to_act[1] if to_act else None,
        viewer_seat=viewer_seat,
        legal_actions=legal,
        insurance_offered=(
            viewer_seat is not None
            and game.phase == Phase.INSURANCE
            and game.seats[viewer_seat].insurance_pending
        ),
        shoe_remaining=len(game.shoe),
        shoe_total=game.shoe.total,
        cut_reached=game.shoe.cut_reached,
        events=tuple(_event(event) for event in game.events),
    )
