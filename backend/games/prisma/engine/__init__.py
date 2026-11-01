"""Motor de Prisma, el juego de descarte. Python puro, sin dependencias web."""

from .cards import (
    ACTION_POINTS,
    DARK_COLORS,
    DECK_SIZE,
    DECK_SIZES,
    LIGHT_COLORS,
    WILD_POINTS,
    Color,
    Kind,
    Mode,
    PrismaCard,
    Side,
    full_deck,
)
from .game import MAX_PLAYERS, MIN_PLAYERS, Event, IllegalMove, Phase, Player, PrismaGame
from .rules import KNOCKOUT_POINTS, MERCY_LIMIT, PrismaRules
from .views import Legal, PlayerView, TableView, event_view, table_view

__all__ = [
    "ACTION_POINTS",
    "DARK_COLORS",
    "DECK_SIZE",
    "DECK_SIZES",
    "KNOCKOUT_POINTS",
    "LIGHT_COLORS",
    "MAX_PLAYERS",
    "MERCY_LIMIT",
    "MIN_PLAYERS",
    "WILD_POINTS",
    "Color",
    "Event",
    "IllegalMove",
    "Kind",
    "Legal",
    "Mode",
    "Phase",
    "Player",
    "PlayerView",
    "PrismaCard",
    "PrismaGame",
    "PrismaRules",
    "Side",
    "TableView",
    "event_view",
    "full_deck",
    "table_view",
]
