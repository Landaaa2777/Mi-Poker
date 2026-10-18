"""Ficha del blackjack en el registro de juegos."""

from __future__ import annotations

from core.registry import GameInfo
from core.room import RoomContext
from core.session import SessionContext

from .protocol import MAX_BOTS, BlackjackConfig, RoomConfig
from .room import BlackjackRoom
from .session import BlackjackSession


def create_session(context: SessionContext) -> BlackjackSession:
    """Una mesa de blackjack nueva, todavía sin nadie sentado."""
    return BlackjackSession(context.bot_delay, context.account, context.player_name)


def create_room(context: RoomContext) -> BlackjackRoom:
    """La partida de una sala, con sus personas ya sentadas."""
    return BlackjackRoom(context)


GAME = GameInfo(
    id="blackjack",
    name="Blackjack",
    description="Suma 21 sin pasarte y gánale al crupier.",
    min_bots=0,
    max_bots=MAX_BOTS,
    options=BlackjackConfig,
    create=create_session,
    room_options=RoomConfig,
    create_room=create_room,
)
