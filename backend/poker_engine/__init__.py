"""Motor de Texas Hold'em No-Limit. Python puro, sin dependencias web.

Las fichas son virtuales y solo existen en memoria durante la partida.
"""

from .actions import Action, ActionType, IllegalActionError
from .betting import LegalActions
from .cards import Card, Rank, Suit, full_deck, parse_cards
from .deck import Deck
from .evaluator import CATEGORY_NAMES, HandCategory, HandValue, evaluate
from .game import MAX_PLAYERS, MIN_PLAYERS, Game, GameConfig, GameStateError
from .hand import Hand, HandEvent, HandResult, Phase
from .player import Player
from .pots import Pot, PotAward, award_pots, build_pots
from .views import SeatView, TableView, player_view, public_view

__all__ = [
    "CATEGORY_NAMES",
    "MAX_PLAYERS",
    "MIN_PLAYERS",
    "Action",
    "ActionType",
    "Card",
    "Deck",
    "Game",
    "GameConfig",
    "GameStateError",
    "Hand",
    "HandCategory",
    "HandEvent",
    "HandResult",
    "HandValue",
    "IllegalActionError",
    "LegalActions",
    "Phase",
    "Player",
    "Pot",
    "PotAward",
    "Rank",
    "SeatView",
    "Suit",
    "TableView",
    "award_pots",
    "build_pots",
    "evaluate",
    "full_deck",
    "parse_cards",
    "player_view",
    "public_view",
]
