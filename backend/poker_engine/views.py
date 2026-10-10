"""Vistas de la mesa: lo único que pueden ver los bots y el cliente.

Una vista contiene la información pública más, como mucho, las cartas del
jugador que mira. Las cartas ajenas solo aparecen si se mostraron en el
showdown, y el mazo nunca forma parte de una vista.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from typing import Any

from .betting import LegalActions
from .cards import Card
from .game import Game
from .hand import HandEvent, HandResult
from .player import Player


@dataclass(frozen=True, slots=True)
class SeatView:
    seat: int
    name: str
    stack: int
    bet: int
    contributed: int
    status: str  # active, folded, all_in u out
    hole_cards: tuple[Card, ...] | None  # None si están ocultas para quien mira


@dataclass(frozen=True, slots=True)
class TableView:
    hand_number: int
    phase: str | None  # None antes de la primera mano
    button_seat: int | None
    small_blind: int
    big_blind: int
    board: tuple[Card, ...]
    pot: int
    current_bet: int
    to_act_seat: int | None
    seats: tuple[SeatView, ...]
    events: tuple[HandEvent, ...]
    result: HandResult | None
    viewer_seat: int | None
    hole_cards: tuple[Card, ...]  # cartas propias de quien mira
    legal_actions: LegalActions | None  # solo si es el turno de quien mira

    def to_dict(self) -> dict[str, Any]:
        """Versión de solo tipos básicos, lista para enviar como JSON."""
        return _plain(self)


def _plain(value: Any) -> Any:
    if isinstance(value, Card):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _status(player: Player, game: Game) -> str:
    hand = game.hand
    if hand is None:
        return "active" if player.stack > 0 else "out"
    if not player.in_hand or (hand.is_complete and player.stack == 0):
        return "out"
    if player.folded:
        return "folded"
    if player.all_in:
        return "all_in"
    return "active"


def player_view(game: Game, viewer_seat: int | None) -> TableView:
    """Vista de la mesa para un asiento, o solo la parte pública si es None."""
    hand = game.hand
    shown = hand.result.shown_hands if hand is not None and hand.result is not None else {}

    seats = []
    for player in game.players:
        if player.seat in shown:
            visible: tuple[Card, ...] | None = shown[player.seat]
        elif player.seat == viewer_seat and player.in_hand:
            visible = tuple(player.hole_cards)
        else:
            visible = None
        seats.append(
            SeatView(
                player.seat,
                player.name,
                player.stack,
                player.bet,
                player.contributed,
                _status(player, game),
                visible,
            )
        )

    to_act = hand.to_act if hand is not None else None
    viewer = next((p for p in game.players if p.seat == viewer_seat), None)
    own_cards = tuple(viewer.hole_cards) if viewer is not None and viewer.in_hand else ()
    viewer_to_act = hand is not None and to_act is not None and to_act.seat == viewer_seat

    return TableView(
        hand_number=game.hand_number,
        phase=hand.phase.value if hand is not None else None,
        button_seat=game.button_seat,
        small_blind=game.config.small_blind,
        big_blind=game.config.big_blind,
        board=tuple(hand.board) if hand is not None else (),
        pot=hand.pot if hand is not None else 0,
        current_bet=hand.current_bet if hand is not None else 0,
        to_act_seat=to_act.seat if to_act is not None else None,
        seats=tuple(seats),
        events=tuple(hand.events) if hand is not None else (),
        result=hand.result if hand is not None else None,
        viewer_seat=viewer_seat,
        hole_cards=own_cards,
        legal_actions=hand.legal_actions() if hand is not None and viewer_to_act else None,
    )


def public_view(game: Game) -> TableView:
    """Vista sin cartas privadas de nadie."""
    return player_view(game, None)
