"""Ficha de Prisma en el registro de juegos."""

from __future__ import annotations

from core.registry import GameInfo
from core.session import SessionContext

from .protocol import MAX_BOTS, PrismaConfig
from .session import PrismaSession


def create_session(context: SessionContext) -> PrismaSession:
    """Una partida de Prisma nueva, todavía sin empezar."""
    return PrismaSession(context.bot_delay, context.player_name)


GAME = GameInfo(
    id="prisma",
    name="Prisma",
    description="Suelta todas tus cartas antes que nadie: color, número o comodín.",
    min_bots=1,
    max_bots=MAX_BOTS,
    options=PrismaConfig,
    create=create_session,
)
