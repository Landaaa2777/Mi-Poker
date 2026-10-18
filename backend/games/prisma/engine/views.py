"""Lo que ve cada jugador de una partida de Prisma.

Cada uno ve sus propias cartas, la de arriba del descarte, el color de la mesa
y cuántas cartas tienen los demás, pero nunca las cartas de los demás ni el
mazo. Las cartas robadas solo las ve quien las roba. Esta vista es lo único que
reciben el navegador y los bots.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cards import PrismaCard
from .game import Event, Phase, PrismaGame


@dataclass(frozen=True)
class PlayerView:
    seat: int
    name: str
    count: int  # cuántas cartas tiene
    score: int
    said_last: bool
    vulnerable: bool  # tiene una carta y no dijo "¡Última!": se le puede pillar


@dataclass(frozen=True)
class Legal:
    """Lo que puede hacer quien mira, ahora mismo."""

    play: tuple[int, ...]  # ids de las cartas que puede jugar
    draw: bool
    pass_turn: bool
    choose_color: bool
    challenge: bool  # puede desafiar (o aceptar) un Camaleón +4
    declare: bool  # puede decir "¡Última!"
    catch: bool  # puede pillar a alguien

    def to_dict(self) -> dict[str, Any]:
        return {
            "play": list(self.play),
            "draw": self.draw,
            "pass": self.pass_turn,
            "choose_color": self.choose_color,
            "challenge": self.challenge,
            "declare": self.declare,
            "catch": self.catch,
        }


@dataclass(frozen=True)
class TableView:
    phase: str
    round_number: int
    direction: int
    turn: int
    dealer: int
    color: str | None
    top: PrismaCard
    discard_count: int
    draw_count: int
    pending_draw: int
    players: tuple[PlayerView, ...]
    viewer_seat: int | None
    hand: tuple[PrismaCard, ...]  # las cartas de quien mira (vacío para un espectador)
    drawn: int | None  # la carta que acaba de robar y aún puede jugar
    legal: Legal | None
    winner: int | None
    game_over: bool
    rules: dict[str, Any]
    events: tuple[dict[str, Any], ...]

    @property
    def me(self) -> PlayerView:
        assert self.viewer_seat is not None
        return self.players[self.viewer_seat]

    def card(self, card_id: int) -> PrismaCard:
        """Una carta de mi mano, por su id."""
        return next(card for card in self.hand if card.id == card_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "round_number": self.round_number,
            "direction": self.direction,
            "turn": self.turn,
            "dealer": self.dealer,
            "color": self.color,
            "top": self.top.to_dict(),
            "discard_count": self.discard_count,
            "draw_count": self.draw_count,
            "pending_draw": self.pending_draw,
            "players": [player.__dict__.copy() for player in self.players],
            "viewer_seat": self.viewer_seat,
            "hand": [card.to_dict() for card in self.hand],
            "drawn": self.drawn,
            "legal": self.legal.to_dict() if self.legal else None,
            "winner": self.winner,
            "game_over": self.game_over,
            "rules": self.rules,
            "events": list(self.events),
        }


def event_view(event: Event, viewer: int | None) -> dict[str, Any]:
    """Un suceso tal como lo ve `viewer`: las cartas robadas, solo si son suyas."""
    own = viewer is not None and event.seat == viewer
    return {
        "kind": event.kind,
        "seat": event.seat,
        "card": event.card.to_dict() if event.card else None,
        "cards": [card.to_dict() for card in event.cards] if own else [],
        "count": event.count,
        "color": event.color,
        "target": event.target,
        "result": event.result,
        "reason": event.reason,
    }


def legal_for(game: PrismaGame, seat: int) -> Legal:
    my_turn = seat == game.turn
    playing = game.phase == Phase.PLAYING and my_turn
    return Legal(
        play=tuple(card.id for card in game.legal_plays(seat)),
        draw=playing and game.drawn is None,
        pass_turn=playing and game.drawn is not None,
        choose_color=game.phase == Phase.CHOOSE_COLOR and my_turn,
        challenge=game.phase == Phase.CHALLENGE and my_turn,
        declare=game.can_declare(seat),
        catch=game.can_catch(seat),
    )


def table_view(game: PrismaGame, viewer_seat: int | None = None) -> TableView:
    """La mesa tal como la ve `viewer_seat` (o un espectador, con None)."""
    rules = game.rules
    return TableView(
        phase=game.phase.value,
        round_number=game.round_number,
        direction=game.direction,
        turn=game.turn,
        dealer=game.dealer,
        color=game.color.value if game.color else None,
        top=game.top,
        discard_count=len(game.discard),
        draw_count=len(game.draw_pile),
        pending_draw=game.pending_draw,
        players=tuple(
            PlayerView(
                seat=player.seat,
                name=player.name,
                count=len(player.hand),
                score=player.score,
                said_last=player.said_last,
                vulnerable=game.vulnerable == player.seat,
            )
            for player in game.players
        ),
        viewer_seat=viewer_seat,
        hand=tuple(game.players[viewer_seat].hand) if viewer_seat is not None else (),
        drawn=game.drawn.id if game.drawn and viewer_seat == game.turn else None,
        legal=legal_for(game, viewer_seat) if viewer_seat is not None else None,
        winner=game.winner,
        game_over=game.game_over,
        rules={
            "challenge": rules.challenge_active,
            "stack_draw2": rules.stack_draw2,
            "stack_draw4": rules.stack_draw4,
            "scoring": rules.scoring,
            "target": rules.target,
            "hand_size": rules.hand_size,
        },
        events=tuple(event_view(event, viewer_seat) for event in game.events),
    )
