"""Ficha del blackjack en el registro de juegos."""

from __future__ import annotations

from core.registry import GameInfo
from core.session import SessionContext

from .protocol import MAX_BOTS, BlackjackConfig, RoomConfig
from .session import BlackjackSession


def create_session(context: SessionContext) -> BlackjackSession:
    """Una mesa de blackjack nueva, todavía sin nadie sentado."""
    return BlackjackSession(context.bot_delay, context.account, context.player_name)


GAME = GameInfo(
    id="blackjack",
    name="Blackjack",
    description="Suma 21 sin pasarte y gánale al crupier.",
    min_bots=0,
    max_bots=MAX_BOTS,
    options=BlackjackConfig,
    create=create_session,
    room_options=RoomConfig,
)
