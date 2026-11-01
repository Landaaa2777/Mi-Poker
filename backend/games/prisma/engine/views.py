"""Lo que ve cada jugador de una partida de Prisma.

Cada uno ve sus propias cartas, la de arriba del descarte, el color de la mesa
y cuántas cartas tienen los demás, pero nunca las cartas de los demás ni el
mazo. Las cartas robadas solo las ve quien las roba. Esta vista es lo único que
reciben el navegador y los bots.

En Doble cara, como al sostener cartas de dos caras, cada uno ve además la
otra cara de las cartas de los demás (y la de la carta de arriba del mazo),
pero nunca la otra cara de las suyas. Esas caras no van con el id de la carta,
sino con un alias al azar de la ronda: así se puede seguir cada carta en la
mano de un rival sin poder relacionarla con las que ya se han jugado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cards import Mode, PrismaCard, face_dict
from .game import Event, Phase, PrismaGame


@dataclass(frozen=True)
class PlayerView:
    seat: int
    name: str
    count: int  # cuántas cartas tiene
    score: int
    said_last: bool
    vulnerable: bool  # tiene una carta y no dijo "¡Última!": se le puede pillar
    # Doble cara: la otra cara de sus cartas, que ven los demás (vacío para quien mira).
    backs: tuple[dict[str, Any], ...] = ()
    out: bool = False  # Sin tregua: eliminado de la ronda por llegar a 25 cartas


@dataclass(frozen=True)
class Legal:
    """Lo que puede hacer quien mira, ahora mismo."""

    play: tuple[int, ...]  # ids de las cartas que puede jugar
    draw: bool
    pass_turn: bool
    choose_color: bool
    challenge: bool  # puede desafiar (o aceptar) un comodín restringido
    declare: bool  # puede decir "¡Última!"
    catch: bool  # puede pillar a alguien
    roulette: bool = False  # Sin tregua: le ha tocado la Ruleta y elige el color

    def to_dict(self) -> dict[str, Any]:
        return {
            "play": list(self.play),
            "draw": self.draw,
            "pass": self.pass_turn,
            "choose_color": self.choose_color,
            "challenge": self.challenge,
            "declare": self.declare,
            "catch": self.catch,
            "roulette": self.roulette,
        }


@dataclass(frozen=True)
class TableView:
    mode: str
    side: str  # la cara en juego: "luz" o "sombra"
    colors: tuple[str, ...]  # los colores que hay en juego (los que se pueden elegir)
    phase: str
    round_number: int
    direction: int
    turn: int
    dealer: int
    color: str | None
    top: PrismaCard
    discard_count: int
    draw_count: int
    deck_back: dict[str, Any] | None  # Doble cara: la otra cara de la carta de arriba del mazo
    pending_draw: int
    pending_min: int  # Sin tregua: la carga mínima con la que se puede acumular
    aside_count: int  # Sin tregua: cartas apartadas de los eliminados (vuelven al rebarajar)
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
            "mode": self.mode,
            "side": self.side,
            "colors": list(self.colors),
            "phase": self.phase,
            "round_number": self.round_number,
            "direction": self.direction,
            "turn": self.turn,
            "dealer": self.dealer,
            "color": self.color,
            "top": self.top.to_dict(),
            "discard_count": self.discard_count,
            "draw_count": self.draw_count,
            "deck_back": self.deck_back,
            "pending_draw": self.pending_draw,
            "pending_min": self.pending_min,
            "aside_count": self.aside_count,
            "players": [{**player.__dict__, "backs": list(player.backs)} for player in self.players],
            "viewer_seat": self.viewer_seat,
            "hand": [card.to_dict() for card in self.hand],
            "drawn": self.drawn,
            "legal": self.legal.to_dict() if self.legal else None,
            "winner": self.winner,
            "game_over": self.game_over,
            "rules": self.rules,
            "events": list(self.events),
        }


# Sucesos cuyas cartas ve todo el mundo: las que destapa la Ruleta y las que se
# suelta con un Barrido. Las robadas y las repartidas, solo su dueño.
PUBLIC_CARDS = frozenset({"reveal", "sweep"})


def event_view(event: Event, viewer: int | None, aliases: dict[int, int] | None = None) -> dict[str, Any]:
    """Un suceso tal como lo ve `viewer`: las cartas robadas, solo si son suyas.

    Tras un Eclipse, un 7 o un 0, `cards` es cómo le queda la mano a quien mira,
    y `backs` (en Doble cara) la otra cara que ve de las manos de los demás.
    """
    view: dict[str, Any] = {"backs": {}}
    if event.hands:
        cards = [card.to_dict() for card in event.hands[viewer]] if viewer is not None else []
        if aliases:
            view["backs"] = {
                str(seat): [{"key": aliases[card.id], **face_dict(card.back)} for card in hand if card.back]
                for seat, hand in enumerate(event.hands)
                if seat != viewer
            }
    else:
        shown = event.kind in PUBLIC_CARDS or (viewer is not None and event.seat == viewer)
        cards = [card.to_dict() for card in event.cards] if shown else []
    return {
        **view,
        "kind": event.kind,
        "seat": event.seat,
        "card": event.card.to_dict() if event.card else None,
        "cards": cards,
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
        roulette=game.phase == Phase.ROULETTE and my_turn,
    )


def backs_of(game: PrismaGame, seat: int, viewer_seat: int | None) -> tuple[dict[str, Any], ...]:
    """La otra cara de las cartas de `seat`, tal como la ve `viewer_seat` (nunca la suya)."""
    if game.mode != Mode.DOBLE or seat == viewer_seat:
        return ()
    return tuple(
        {"key": game.aliases[card.id], **face_dict(card.back)}
        for card in game.players[seat].hand
        if card.back is not None
    )


def table_view(game: PrismaGame, viewer_seat: int | None = None) -> TableView:
    """La mesa tal como la ve `viewer_seat` (o un espectador, con None)."""
    rules = game.rules
    deck_top = game.draw_pile[-1] if game.draw_pile else None
    return TableView(
        mode=game.mode.value,
        side=game.side.value,
        colors=tuple(color.value for color in game.colors),
        phase=game.phase.value,
        round_number=game.round_number,
        direction=game.direction,
        turn=game.turn,
        dealer=game.dealer,
        color=game.color.value if game.color else None,
        top=game.top.face(),
        discard_count=len(game.discard),
        draw_count=len(game.draw_pile),
        deck_back=face_dict(deck_top.back) if deck_top is not None and deck_top.back is not None else None,
        pending_draw=game.pending_draw,
        pending_min=game.pending_min,
        aside_count=len(game.set_aside),
        players=tuple(
            PlayerView(
                seat=player.seat,
                name=player.name,
                count=len(player.hand),
                score=player.score,
                said_last=player.said_last,
                vulnerable=game.vulnerable == player.seat,
                backs=backs_of(game, player.seat, viewer_seat),
                out=player.seat in game.out,
            )
            for player in game.players
        ),
        viewer_seat=viewer_seat,
        # Solo la cara en juego: la otra cara de las propias cartas no se ve.
        hand=tuple(card.face() for card in game.players[viewer_seat].hand) if viewer_seat is not None else (),
        drawn=game.drawn.id if game.drawn and viewer_seat == game.turn else None,
        legal=legal_for(game, viewer_seat) if viewer_seat is not None else None,
        winner=game.winner,
        game_over=game.game_over,
        rules={
            "mode": rules.mode.value,
            "challenge": rules.challenge_active,
            "stack_draw2": rules.stack_draw2,
            "stack_draw4": rules.stack_draw4,
            "scoring": rules.scoring,
            "target": rules.target,
            "hand_size": rules.hand_size,
        },
        events=tuple(event_view(event, viewer_seat, game.aliases) for event in game.events),
    )
