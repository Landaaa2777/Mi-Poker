"""Ficha del poker en el registro de juegos."""

from __future__ import annotations

from core.registry import GameInfo
from core.room import RoomContext
from core.session import SessionContext

from .protocol import MAX_BOTS, RoomConfig, TableConfig
from .room import PokerRoom
from .session import GameSession


def create_session(context: SessionContext) -> GameSession:
    """Una partida de poker nueva, todavía sin empezar."""
    return GameSession(
        context.bot_delay, context.simulations, context.account, context.player_name
    )


def create_room(context: RoomContext) -> PokerRoom:
    """La partida de una sala, con sus personas ya sentadas."""
    return PokerRoom(context)


GAME = GameInfo(
    id="poker",
    name="Poker Hold'em",
    description="Texas Hold'em sin límite: farolea, sube y llévate el bote.",
    min_bots=1,
    max_bots=MAX_BOTS,
    options=TableConfig,
    create=create_session,
    room_options=RoomConfig,
    create_room=create_room,
)
