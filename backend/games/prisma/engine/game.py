"""Una partida de Prisma: rondas, turnos, efectos de las cartas y puntos. Python puro.

Las reglas son las del juego de descarte clásico:

- En tu turno juegas una carta del mismo color, del mismo número o del mismo
  símbolo que la de la mesa, o un comodín. En vez de jugar puedes robar una
  carta; si la robada sirve, puedes jugarla en ese mismo turno o quedártela.
- Pausa salta al siguiente; Remolino cambia el sentido (con dos jugadores es
  como una Pausa); Carga +2 hace robar 2 al siguiente, que pierde su turno.
- Camaleón: eliges el color. Camaleón +4: eliges el color y el siguiente roba
  4 y pierde su turno; solo se puede jugar sin cartas del color de la mesa. Con
  el desafío activado se puede jugar de farol, y el siguiente puede desafiarlo.
- Al quedarte con una carta hay que decir "¡Última!" antes de que juegue el
  siguiente; si te pillan sin decirlo, robas 2.
- Gana la ronda quien se queda sin cartas. Si se juega a puntos, se lleva lo
  que valen las cartas que les quedan a los demás.

Las cartas nunca se crean ni se pierden: mazo + descarte + manos = 108 siempre.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from core.shuffle import SYSTEM_RNG

from .cards import DECK_SIZE, Color, Kind, PrismaCard, full_deck
from .rules import PrismaRules

MIN_PLAYERS = 2
MAX_PLAYERS = 6


class Phase(StrEnum):
    CHOOSE_COLOR = "choose_color"  # la carta inicial fue un Camaleón: el primero elige color
    PLAYING = "playing"
    CHALLENGE = "challenge"  # el siguiente decide si desafía un Camaleón +4
    ROUND_OVER = "round_over"


class IllegalMove(ValueError):
    """La jugada no está permitida; el mensaje dice por qué."""


@dataclass
class Player:
    seat: int
    name: str
    hand: list[PrismaCard] = field(default_factory=list)
    score: int = 0  # puntos acumulados (si se juega a puntos)
    said_last: bool = False  # dijo "¡Última!" por la carta que le queda


@dataclass(frozen=True)
class Event:
    """Algo que pasa en la ronda. El registro de eventos solo crece."""

    kind: str
    seat: int | None = None
    card: PrismaCard | None = None  # la carta jugada o volteada (pública)
    cards: tuple[PrismaCard, ...] = ()  # cartas robadas o repartidas: solo las ve su dueño
    count: int = 0
    color: Color | None = None  # el color de la mesa en ese momento
    target: int | None = None  # el otro jugador implicado (quien pilla, a quién se desafía)
    result: str = ""
    reason: str = ""


@dataclass(frozen=True)
class Wild4Play:
    """El último Camaleón +4 jugado, por si lo desafían."""

    seat: int
    illegal: bool  # tenía cartas del color de la mesa: era un farol


class PrismaGame:
    """La mesa: jugadores, mazo, descarte y la ronda en curso."""

    def __init__(
        self,
        names: Sequence[str],
        rules: PrismaRules | None = None,
        rng: random.Random | None = None,
    ) -> None:
        if not MIN_PLAYERS <= len(names) <= MAX_PLAYERS:
            raise ValueError(f"Se juega de {MIN_PLAYERS} a {MAX_PLAYERS} jugadores")
        self.rules = rules or PrismaRules()
        # Solo los tests y las simulaciones pasan un generador con semilla.
        self.rng = rng or SYSTEM_RNG
        self.players = [Player(seat, name) for seat, name in enumerate(names)]
        self.draw_pile: list[PrismaCard] = []  # la carta de arriba es la última
        self.discard: list[PrismaCard] = []  # la de arriba es la última
        self.color: Color | None = None  # color que hay que seguir
        self.direction = 1  # 1 o -1
        self.turn = 0
        self.dealer = self.rng.randrange(len(names)) - 1  # la primera ronda reparte el siguiente
        self.phase = Phase.ROUND_OVER  # todavía no ha empezado ninguna ronda
        self.round_number = 0
        self.events: list[Event] = []
        self.pending_draw = 0  # cartas acumuladas (solo con las opciones de la casa)
        self.pending_kind: Kind | None = None
        self.drawn: PrismaCard | None = None  # robada este turno y que aún se puede jugar
        self.wild4: Wild4Play | None = None
        self.vulnerable: int | None = None  # se quedó con una carta sin decir "¡Última!"
        self.armed: set[int] = set()  # dijeron "¡Última!" antes de jugar su penúltima carta
        self.winner: int | None = None
        # Turnos seguidos en los que no se pudo robar nada (sin mazo ni descarte que
        # rebarajar) y nadie jugó: con una vuelta entera, la ronda está trancada.
        self.dry_turns = 0

    # --- Consultas ---

    @property
    def top(self) -> PrismaCard:
        return self.discard[-1]

    @property
    def game_over(self) -> bool:
        """¿Se acabó la partida? Sin puntos, cada ronda es una partida."""
        if self.phase != Phase.ROUND_OVER or self.winner is None:
            return False
        return not self.rules.scoring or any(p.score >= self.rules.target for p in self.players)

    def total_cards(self) -> int:
        """Mazo + descarte + manos: tiene que ser siempre 108."""
        return len(self.draw_pile) + len(self.discard) + sum(len(p.hand) for p in self.players)

    def next_seat(self, seat: int, steps: int = 1) -> int:
        return (seat + self.direction * steps) % len(self.players)

    def can_play(self, seat: int, card: PrismaCard) -> bool:
        """¿Casa `card` con la mesa, para `seat`, ahora mismo?"""
        if self.pending_draw:
            # Con cartas acumuladas solo vale acumular otra igual (o robarlas todas).
            return card.kind == self.pending_kind
        if card.kind == Kind.CAMALEON:
            return True
        if card.kind == Kind.CAMALEON4:
            if self.rules.challenge_active:
                return True  # se puede jugar de farol: el desafío lo castiga
            return not self._has_color(seat, self.color, excluding=card)
        if card.color == self.color:
            return True
        top = self.top
        if card.kind == Kind.NUMBER:
            return top.kind == Kind.NUMBER and top.number == card.number
        return card.kind == top.kind  # la misma acción, de otro color

    def legal_plays(self, seat: int) -> list[PrismaCard]:
        """Las cartas que `seat` puede jugar ahora (vacío si no es su turno)."""
        if self.phase != Phase.PLAYING or seat != self.turn:
            return []
        options = [self.drawn] if self.drawn else self.players[seat].hand
        return [card for card in options if self.can_play(seat, card)]

    def can_declare(self, seat: int) -> bool:
        """¿Puede decir "¡Última!" ahora? Al jugar su penúltima carta o justo después."""
        if self.vulnerable == seat:
            return True
        return (
            self.phase == Phase.PLAYING
            and seat == self.turn
            and len(self.players[seat].hand) == 2
            and seat not in self.armed
        )

    def can_catch(self, seat: int) -> bool:
        """¿Hay alguien con una carta que no dijo "¡Última!" y al que `seat` puede pillar?"""
        return self.vulnerable is not None and self.vulnerable != seat

    # --- Una ronda ---

    def start_round(self, deck: Sequence[PrismaCard] | None = None) -> None:
        """Baraja, reparte y voltea la primera carta. `deck` (en orden) es solo para los tests."""
        if self.round_number > 0 and (self.phase != Phase.ROUND_OVER or self.game_over):
            raise IllegalMove("No se puede empezar otra ronda ahora")
        count = len(self.players)
        self.round_number += 1
        self.dealer = (self.dealer + 1) % count
        self.events = []
        self.direction = 1
        self.pending_draw, self.pending_kind = 0, None
        self.drawn = self.wild4 = self.winner = self.vulnerable = None
        self.armed = set()
        self.dry_turns = 0
        cards = list(deck) if deck is not None else full_deck()
        if deck is None:
            self.rng.shuffle(cards)
        self.draw_pile = list(reversed(cards))  # la primera de `cards` queda arriba
        self.discard = []
        for player in self.players:
            player.hand = []
            player.said_last = False
        # Se reparte de una en una, empezando por el de la izquierda de quien reparte.
        order = [(self.dealer + 1 + offset) % count for offset in range(count)]
        for _ in range(self.rules.hand_size):
            for seat in order:
                self.players[seat].hand.append(self.draw_pile.pop())
        for seat in order:
            hand = tuple(self.players[seat].hand)
            self.events.append(Event("deal", seat, cards=hand, count=len(hand)))

        # La primera carta del descarte. Un Camaleón +4 vuelve al mazo, en un sitio al azar.
        first = self.draw_pile.pop()
        while first.kind == Kind.CAMALEON4:
            self.draw_pile.insert(self.rng.randrange(len(self.draw_pile) + 1), first)
            self.events.append(Event("return", card=first))
            first = self.draw_pile.pop()
        self.discard = [first]
        self.color = first.color
        self.events.append(Event("start", card=first, color=first.color))
        self.turn = self.next_seat(self.dealer)
        self.phase = Phase.PLAYING

        # Si es una carta de acción, afecta al primer jugador.
        if first.kind == Kind.PAUSA:
            self.events.append(Event("skip", self.turn))
            self.turn = self.next_seat(self.turn)
        elif first.kind == Kind.REMOLINO:
            # Empieza quien reparte y el juego va al revés.
            self.direction = -1
            self.events.append(Event("reverse", result="left"))
            self.turn = self.dealer
        elif first.kind == Kind.CARGA:
            self._draw_cards(self.turn, 2, "carga")
            self.events.append(Event("skip", self.turn))
            self.turn = self.next_seat(self.turn)
        elif first.kind == Kind.CAMALEON:
            self.phase = Phase.CHOOSE_COLOR

    def choose_color(self, seat: int, color: Color | str) -> None:
        """El primer jugador elige el color cuando la carta inicial es un Camaleón."""
        self._require(seat, Phase.CHOOSE_COLOR)
        self.color = self._color(color)
        self.events.append(Event("choose", seat, color=self.color))
        self.phase = Phase.PLAYING

    def declare_last(self, seat: int) -> None:
        """Dice "¡Última!": al ir a jugar su penúltima carta, o justo después de jugarla."""
        player = self.players[seat]
        if self.vulnerable == seat:
            self.vulnerable = None
            player.said_last = True
        elif self.phase == Phase.PLAYING and seat == self.turn and len(player.hand) == 2:
            if seat in self.armed:
                raise IllegalMove("Ya lo has dicho")
            self.armed.add(seat)
        else:
            raise IllegalMove("«¡Última!» se dice al quedarte con una sola carta")
        self.events.append(Event("last", seat))

    def catch(self, accuser: int) -> None:
        """Pilla a quien se quedó con una carta sin decir "¡Última!": roba 2."""
        if not self.can_catch(accuser):
            raise IllegalMove("No hay nadie a quien pillar")
        target = self.vulnerable
        assert target is not None
        self.vulnerable = None
        self.events.append(Event("caught", target, target=accuser))
        self._draw_cards(target, self.rules.catch_penalty, "pillado")

    def play(self, seat: int, card_id: int, color: Color | str | None = None, declare: bool = False) -> None:
        """Juega una carta. Los comodines llevan el color elegido; `declare` dice "¡Última!" a la vez."""
        self._require(seat, Phase.PLAYING)
        player = self.players[seat]
        card = next((card for card in player.hand if card.id == card_id), None)
        if card is None:
            raise IllegalMove("No tienes esa carta")
        if self.drawn is not None and card.id != self.drawn.id:
            raise IllegalMove("Después de robar solo puedes jugar la carta robada, o pasar")
        if not self.can_play(seat, card):
            raise IllegalMove(self._why_not(seat, card))
        if card.is_wild:
            if color is None:
                raise IllegalMove("Elige un color para el comodín")
            chosen = self._color(color)
        elif color is not None:
            raise IllegalMove("Solo los comodines cambian el color")
        else:
            chosen = card.color
        if declare and len(player.hand) != 2:
            raise IllegalMove("«¡Última!» se dice al jugar la penúltima carta")

        self._close_window(seat)
        bluff = card.kind == Kind.CAMALEON4 and self._has_color(seat, self.color, excluding=card)
        player.hand.remove(card)
        self.discard.append(card)
        self.drawn = None
        self.color = chosen
        self.events.append(Event("play", seat, card=card, color=chosen))
        self.dry_turns = 0
        if declare:
            self.events.append(Event("last", seat))
        if len(player.hand) == 1:
            player.said_last = declare or seat in self.armed
            if not player.said_last:
                self.vulnerable = seat  # cualquiera puede pillarle hasta que juegue el siguiente
        self.armed.discard(seat)

        if not player.hand:
            self._finish_round(seat, card)
        else:
            self._apply(seat, card, bluff)

    def draw(self, seat: int) -> None:
        """Roba: una carta (que, si sirve, se puede jugar ya) o todas las acumuladas."""
        self._require(seat, Phase.PLAYING)
        if self.drawn is not None:
            raise IllegalMove("Ya has robado: juega la carta robada o pasa")
        self._close_window(seat)
        self.armed.discard(seat)
        if self.pending_draw:
            count, self.pending_draw, self.pending_kind = self.pending_draw, 0, None
            self._draw_cards(seat, count, "acumuladas")
            self.turn = self.next_seat(seat)
            return
        drawn = self._draw_cards(seat, 1, "turno")
        self.dry_turns = 0 if drawn else self.dry_turns + 1
        if self.dry_turns >= len(self.players):
            self._block_round()  # nadie ha podido jugar ni robar en una vuelta entera
        elif drawn and self.can_play(seat, drawn[0]):
            self.drawn = drawn[0]  # puede jugarla ahora o quedársela
        else:
            self.events.append(Event("pass", seat))
            self.turn = self.next_seat(seat)

    def pass_turn(self, seat: int) -> None:
        """Se queda la carta que acaba de robar y pasa el turno."""
        self._require(seat, Phase.PLAYING)
        if self.drawn is None:
            raise IllegalMove("Solo se puede pasar después de robar")
        self.drawn = None
        self.events.append(Event("pass", seat))
        self.turn = self.next_seat(seat)

    def accept(self, seat: int) -> None:
        """No desafía el Camaleón +4: roba 4 y pierde su turno."""
        self._require(seat, Phase.CHALLENGE)
        self._close_window(seat)
        self.wild4 = None
        self.phase = Phase.PLAYING
        self._draw_cards(seat, 4, "camaleon4")
        self.events.append(Event("skip", seat))
        self.turn = self.next_seat(seat)

    def challenge(self, seat: int) -> None:
        """Desafía el Camaleón +4. Si era un farol, quien lo jugó roba 4; si no, el desafiante roba 6."""
        self._require(seat, Phase.CHALLENGE)
        self._close_window(seat)
        play, self.wild4 = self.wild4, None
        assert play is not None
        self.phase = Phase.PLAYING
        if play.illegal:
            self.events.append(Event("challenge", seat, target=play.seat, result="guilty"))
            self._draw_cards(play.seat, 4, "desafio")
            self.turn = seat  # el desafiante juega su turno con normalidad
        else:
            self.events.append(Event("challenge", seat, target=play.seat, result="innocent"))
            self._draw_cards(seat, 6, "desafio")
            self.events.append(Event("skip", seat))
            self.turn = self.next_seat(seat)

    def next_round(self) -> None:
        """Otra ronda (solo si se juega a puntos y nadie ha llegado a la meta)."""
        if self.phase != Phase.ROUND_OVER or self.winner is None:
            raise IllegalMove("La ronda todavía no ha terminado")
        if self.game_over:
            raise IllegalMove("La partida ha terminado")
        self.start_round()

    # --- Interno ---

    def _require(self, seat: int, phase: Phase) -> None:
        if self.phase != phase:
            raise IllegalMove(
                {
                    Phase.CHOOSE_COLOR: "Primero hay que elegir el color de la carta inicial",
                    Phase.CHALLENGE: "Primero hay que decidir si se desafía el Camaleón +4",
                    Phase.ROUND_OVER: "La ronda ha terminado",
                    Phase.PLAYING: "Ahora no se puede hacer eso",
                }[self.phase]
            )
        if seat != self.turn:
            raise IllegalMove("No es tu turno")

    @staticmethod
    def _color(color: Color | str) -> Color:
        try:
            return Color(color)
        except ValueError:
            raise IllegalMove(f"Color desconocido: {color!r}") from None

    def _has_color(self, seat: int, color: Color | None, excluding: PrismaCard) -> bool:
        return any(card.color == color and card.id != excluding.id for card in self.players[seat].hand)

    def _why_not(self, seat: int, card: PrismaCard) -> str:
        if self.pending_draw:
            return "Tienes que acumular otra carta igual o robar las acumuladas"
        if card.kind == Kind.CAMALEON4:
            return "El Camaleón +4 solo se puede jugar sin cartas del color de la mesa"
        return "Esa carta no casa con la de la mesa"

    def _close_window(self, actor: int) -> None:
        """Al actuar el siguiente, ya no se puede pillar a quien no dijo "¡Última!"."""
        if self.vulnerable is not None and self.vulnerable != actor:
            self.vulnerable = None

    def _reshuffle(self) -> None:
        """Se acabó el mazo: se rebaraja el descarte, menos la carta de arriba."""
        top = self.discard.pop()
        rest, self.discard = self.discard, [top]
        self.rng.shuffle(rest)
        self.draw_pile = rest
        self.events.append(Event("reshuffle", count=len(rest)))

    def _draw_cards(self, seat: int, count: int, reason: str) -> list[PrismaCard]:
        drawn: list[PrismaCard] = []
        for _ in range(count):
            if not self.draw_pile and len(self.discard) > 1:
                self._reshuffle()
            if not self.draw_pile:
                break  # no quedan cartas en ningún sitio: se roban las que haya
            drawn.append(self.draw_pile.pop())
        player = self.players[seat]
        player.hand.extend(drawn)
        if len(player.hand) > 1:
            player.said_last = False
            if self.vulnerable == seat:
                self.vulnerable = None
        self.events.append(
            Event("draw", seat, cards=tuple(drawn), count=len(drawn), color=self.color, reason=reason)
        )
        return drawn

    def _apply(self, seat: int, card: PrismaCard, bluff: bool) -> None:
        """El efecto de la carta jugada y a quién le toca después."""
        victim = self.next_seat(seat)
        if card.kind in (Kind.NUMBER, Kind.CAMALEON):
            self.turn = victim
        elif card.kind == Kind.PAUSA:
            self.events.append(Event("skip", victim))
            self.turn = self.next_seat(seat, 2)
        elif card.kind == Kind.REMOLINO:
            self.direction *= -1
            self.events.append(Event("reverse", result="left" if self.direction < 0 else "right"))
            if len(self.players) == 2:
                # Con dos jugadores es como una Pausa: vuelve a jugar el mismo.
                self.events.append(Event("skip", victim))
                self.turn = seat
            else:
                self.turn = self.next_seat(seat)
        elif card.kind == Kind.CARGA:
            if self.rules.stack_draw2:
                self.pending_draw += 2
                self.pending_kind = Kind.CARGA
                self.turn = victim
            else:
                self._draw_cards(victim, 2, "carga")
                self.events.append(Event("skip", victim))
                self.turn = self.next_seat(seat, 2)
        else:  # Camaleón +4
            if self.rules.stack_draw4:
                self.pending_draw += 4
                self.pending_kind = Kind.CAMALEON4
                self.turn = victim
            elif self.rules.challenge_active:
                self.wild4 = Wild4Play(seat, bluff)
                self.phase = Phase.CHALLENGE
                self.turn = victim
            else:
                self._draw_cards(victim, 4, "camaleon4")
                self.events.append(Event("skip", victim))
                self.turn = self.next_seat(seat, 2)

    def _finish_round(self, winner: int, last: PrismaCard) -> None:
        """Alguien se quedó sin cartas. Si su última carta hace robar, el siguiente roba igual."""
        victim = self.next_seat(winner)
        penalty = {Kind.CARGA: 2, Kind.CAMALEON4: 4}.get(last.kind, 0)
        if penalty or self.pending_draw:
            self._draw_cards(victim, self.pending_draw + penalty, "final")
        self._close_round(winner)

    def _block_round(self) -> None:
        """Ronda trancada: no queda nada que robar y nadie ha jugado en una vuelta entera.

        Gana quien tiene menos cartas; si empatan, quien suma menos puntos, y si
        siguen empatados, el primero de la mesa.
        """
        winner = min(
            self.players, key=lambda p: (len(p.hand), sum(card.points for card in p.hand), p.seat)
        )
        self.events.append(Event("blocked", winner.seat))
        self._close_round(winner.seat)

    def _close_round(self, winner: int) -> None:
        self.pending_draw, self.pending_kind = 0, None
        self.drawn = None
        self.vulnerable = None
        self.winner = winner
        self.phase = Phase.ROUND_OVER
        points = sum(card.points for p in self.players if p.seat != winner for card in p.hand)
        if self.rules.scoring:
            self.players[winner].score += points
        self.events.append(Event("round_over", winner, count=points))
        assert self.total_cards() == DECK_SIZE
