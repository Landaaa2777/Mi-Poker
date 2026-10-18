"""Motor de Prisma, el juego de descarte. Python puro, sin dependencias web."""

from .cards import (
    ACTION_POINTS,
    DECK_SIZE,
    WILD_POINTS,
    Color,
    Kind,
    PrismaCard,
    full_deck,
)
from .game import MAX_PLAYERS, MIN_PLAYERS, Event, IllegalMove, Phase, Player, PrismaGame
from .rules import PrismaRules
from .views import Legal, PlayerView, TableView, event_view, table_view

__all__ = [
    "ACTION_POINTS",
    "DECK_SIZE",
    "MAX_PLAYERS",
    "MIN_PLAYERS",
    "WILD_POINTS",
    "Color",
    "Event",
    "IllegalMove",
    "Kind",
    "Legal",
    "Phase",
    "Player",
    "PlayerView",
    "PrismaCard",
    "PrismaGame",
    "PrismaRules",
    "TableView",
    "event_view",
    "full_deck",
    "table_view",
]
