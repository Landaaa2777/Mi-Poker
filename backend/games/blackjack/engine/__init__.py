"""Motor de blackjack. Python puro, sin dependencias web.

Las fichas son virtuales y solo existen en memoria durante la partida.
"""

from .game import (
    MAX_SEATS,
    Action,
    BlackjackGame,
    Event,
    HandStatus,
    IllegalActionError,
    Phase,
    PlayerHand,
    Result,
    Seat,
)
from .hand import BLACKJACK, card_value, hand_total, is_blackjack, is_bust
from .rules import Rules
from .shoe import Shoe
from .views import HandView, SeatView, TableView, table_view

__all__ = [
    "BLACKJACK",
    "MAX_SEATS",
    "Action",
    "BlackjackGame",
    "Event",
    "HandStatus",
    "HandView",
    "IllegalActionError",
    "Phase",
    "PlayerHand",
    "Result",
    "Rules",
    "Seat",
    "SeatView",
    "Shoe",
    "TableView",
    "card_value",
    "hand_total",
    "is_blackjack",
    "is_bust",
    "table_view",
]
