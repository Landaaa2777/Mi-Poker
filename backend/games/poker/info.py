"""Ficha del poker en el registro de juegos."""

from __future__ import annotations

from core.registry import GameInfo
from core.session import SessionContext

from .protocol import MAX_BOTS, TableConfig
from .session import GameSession


def create_session(context: SessionContext) -> GameSession:
    """Una partida de poker nueva, todavía sin empezar."""
    return GameSession(
        context.bot_delay, context.simulations, context.account, context.player_name
    )


GAME = GameInfo(
    id="poker",
    name="Poker Hold'em",
    description="Texas Hold'em sin límite: farolea, sube y llévate el bote.",
    min_bots=1,
    max_bots=MAX_BOTS,
    options=TableConfig,
    create=create_session,
)
