"""Una partida de Prisma: rondas, turnos, efectos de las cartas y puntos. Python puro.

Hay tres modos (ver `cards.py` para sus mazos). El Clásico sigue las reglas del
juego de descarte clásico:

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

Doble cara cambia esto:

- Cada carta tiene dos caras, luz y sombra, y se juega con una de las dos. El
  Eclipse le da la vuelta a todo: al descarte (la carta de abajo queda
  arriba), al mazo y a las manos. Si la nueva carta de arriba es un comodín,
  quien jugó el Eclipse elige el color.
- Carga +1 y Carga +5 hacen robar 1 y 5; Pausa total salta a todos (vuelve a
  jugar quien la puso). Camaleón +2 hace robar 2 y Camaleón Sabueso, hasta
  sacar una carta del color elegido; los dos se juegan solo sin cartas del
  color de la mesa, y con el desafío activado se pueden desafiar.

Sin tregua cambia esto otro:

- Las cargas (+2, +4, +6, +10) se acumulan con otra de igual o más valor, de
  cualquier color; quien no puede o no quiere, lo roba todo y pierde el turno.
- Quien roba en su turno roba hasta sacar una carta que pueda jugar.
- Barrido: sueltas además todas tus cartas de su color. Pausa total: todos
  pierden el turno. Camaleón Remolino +4: cambia el sentido y el siguiente en
  el nuevo sentido roba 4 (con dos jugadores, quien lo jugó). Camaleón Ruleta:
  el siguiente elige un color y destapa cartas hasta que sale; se las queda.
- El 7 cambia tu mano por la de quien elijas; el 0 pasa todas las manos al
  siguiente, en el sentido del juego.
- Quien llega a 25 cartas queda eliminado de la ronda (sus cartas se apartan
  hasta el próximo rebarajado). Gana quien se queda sin cartas o el último que
  queda; a puntos, cada eliminado vale 250 más.

Las cartas nunca se crean ni se pierden: mazo + descarte + manos (+ las
apartadas) son siempre todas las del mazo del modo (108, 112 o 168).
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from core.shuffle import SYSTEM_RNG

from .cards import DARK_COLORS, DRAW_VALUE, LIGHT_COLORS, Color, Kind, Mode, PrismaCard, Side, full_deck
from .rules import KNOCKOUT_POINTS, MERCY_LIMIT, PrismaRules

# Comodines que solo se pueden jugar sin cartas del color de la mesa (y que,
# con el desafío activado, se pueden jugar de farol y desafiar).
RESTRICTED = frozenset({Kind.CAMALEON4, Kind.CAMALEON2, Kind.SABUESO})

MIN_PLAYERS = 2
MAX_PLAYERS = 6


class Phase(StrEnum):
    # Hay que elegir color: la carta inicial fue un Camaleón (elige el primero),
    # o un Eclipse dejó un comodín arriba (elige quien lo jugó).
    CHOOSE_COLOR = "choose_color"
    PLAYING = "playing"
    CHALLENGE = "challenge"  # el siguiente decide si desafía un comodín restringido
    ROULETTE = "roulette"  # Sin tregua: quien sufre la Ruleta elige el color que la para
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
    cards: tuple[PrismaCard, ...] = ()  # robadas o repartidas: solo las ve su dueño (las de la Ruleta, todos)
    count: int = 0
    color: Color | None = None  # el color de la mesa en ese momento
    target: int | None = None  # el otro jugador implicado (quien pilla, a quién se desafía)
    result: str = ""
    reason: str = ""
    # Tras un Eclipse, un 7 o un 0: cómo quedan las manos (cada uno verá la suya
    # y, en Doble cara, la otra cara de las de los demás; ver las vistas).
    hands: tuple[tuple[PrismaCard, ...], ...] = ()


@dataclass(frozen=True)
class WildPlay:
    """El último comodín restringido jugado (+4, +2 o Sabueso), por si lo desafían."""

    seat: int
    kind: Kind
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
        self.side = Side.LUZ  # la cara en juego (solo cambia en Doble cara)
        self.color: Color | None = None  # color que hay que seguir
        self.direction = 1  # 1 o -1
        self.turn = 0
        self.dealer = self.rng.randrange(len(names)) - 1  # la primera ronda reparte el siguiente
        self.phase = Phase.ROUND_OVER  # todavía no ha empezado ninguna ronda
        self.round_number = 0
        self.events: list[Event] = []
        # Cartas acumuladas: con las opciones de la casa del Clásico (solo se acumula
        # otra igual, `pending_kind`) o en Sin tregua (otra de valor `pending_min` o más).
        self.pending_draw = 0
        self.pending_kind: Kind | None = None
        self.pending_min = 0
        # Sin tregua: los eliminados de la ronda y sus cartas, apartadas hasta rebarajar.
        self.out: set[int] = set()
        self.set_aside: list[PrismaCard] = []
        self.drawn: PrismaCard | None = None  # robada este turno y que aún se puede jugar
        self.wild: WildPlay | None = None  # el comodín restringido que se puede desafiar
        self.after_color: int | None = None  # a quién le toca tras elegir color (None: al que elige)
        # Doble cara: un alias al azar por carta y ronda, para que los demás sigan
        # la otra cara de cada carta de una mano sin saber cuál es (ver las vistas).
        self.aliases: dict[int, int] = {}
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

    @property
    def mode(self) -> Mode:
        return self.rules.mode

    @property
    def colors(self) -> tuple[Color, ...]:
        """Los cuatro colores que hay ahora en juego (los de sombra, en la cara de sombra)."""
        return DARK_COLORS if self.side == Side.SOMBRA else LIGHT_COLORS

    def total_cards(self) -> int:
        """Mazo + descarte + manos + apartadas: tiene que ser siempre todo el mazo del modo."""
        hands = sum(len(p.hand) for p in self.players)
        return len(self.draw_pile) + len(self.discard) + hands + len(self.set_aside)

    @property
    def active(self) -> list[int]:
        """Los asientos que siguen en la ronda (en Sin tregua, los no eliminados)."""
        return [player.seat for player in self.players if player.seat not in self.out]

    def next_seat(self, seat: int, steps: int = 1) -> int:
        """El asiento `steps` puestos más allá en el sentido del juego, saltando a los eliminados."""
        count = len(self.players)
        for _ in range(steps):
            seat = (seat + self.direction) % count
            while seat in self.out:
                seat = (seat + self.direction) % count
        return seat

    def can_play(self, seat: int, card: PrismaCard) -> bool:
        """¿Casa `card` con la mesa, para `seat`, ahora mismo?"""
        if self.pending_draw:
            # Con cartas acumuladas solo vale acumular (o robarlas todas): en Sin tregua,
            # otra carga de igual o más valor; con las opciones de la casa, otra igual.
            if self.rules.relentless:
                return card.draw_value >= self.pending_min
            return card.kind == self.pending_kind
        if card.kind in RESTRICTED:
            if self.rules.challenge_active:
                return True  # se puede jugar de farol: el desafío lo castiga
            return not self._has_color(seat, self.color, excluding=card)
        if card.is_wild:
            return True
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
        self.side = Side.LUZ
        self.pending_draw, self.pending_kind, self.pending_min = 0, None, 0
        self.drawn = self.wild = self.winner = self.vulnerable = self.after_color = None
        self.out, self.set_aside = set(), []
        self.armed = set()
        self.dry_turns = 0
        cards = list(deck) if deck is not None else full_deck(self.mode, self.rng)
        if deck is None:
            self.rng.shuffle(cards)
        if self.mode == Mode.DOBLE:
            aliases = list(range(len(cards)))
            self.rng.shuffle(aliases)
            self.aliases = {card.id: alias for card, alias in zip(cards, aliases, strict=True)}
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

        # La primera carta del descarte. Las que no pueden empezar (el Camaleón +4;
        # en Doble cara, el +2 y el Eclipse) vuelven al mazo, en un sitio al azar.
        first = self.draw_pile.pop()
        while self._cannot_start(first):
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
        elif first.kind in (Kind.CARGA, Kind.CARGA1):
            self._draw_cards(self.turn, first.draw_value, first.kind.value)
            self.events.append(Event("skip", self.turn))
            self.turn = self.next_seat(self.turn)
        elif first.kind == Kind.CAMALEON:
            self.phase = Phase.CHOOSE_COLOR

    def choose_color(self, seat: int, color: Color | str) -> None:
        """Elige el color: el primer jugador, si la carta inicial es un Camaleón, o
        quien jugó un Eclipse que dejó un comodín arriba."""
        self._require(seat, Phase.CHOOSE_COLOR)
        self.color = self._color(color)
        self.events.append(Event("choose", seat, color=self.color))
        self.phase = Phase.PLAYING
        if self.after_color is not None:
            self.turn, self.after_color = self.after_color, None

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
        self._check_mercy(target)

    def play(
        self,
        seat: int,
        card_id: int,
        color: Color | str | None = None,
        declare: bool = False,
        target: int | None = None,
    ) -> None:
        """Juega una carta. Los comodines llevan el color elegido; `declare` dice
        "¡Última!" a la vez. En Sin tregua, el 7 lleva con quién se cambia la mano
        (`target`) y la Ruleta no lleva color: lo elige quien la sufre."""
        self._require(seat, Phase.PLAYING)
        player = self.players[seat]
        card = next((card for card in player.hand if card.id == card_id), None)
        if card is None:
            raise IllegalMove("No tienes esa carta")
        if self.drawn is not None and card.id != self.drawn.id:
            raise IllegalMove("Después de robar solo puedes jugar la carta robada, o pasar")
        if not self.can_play(seat, card):
            raise IllegalMove(self._why_not(seat, card))
        if card.kind == Kind.RULETA:
            if color is not None:
                raise IllegalMove("El color de la Ruleta lo elige quien la sufre")
            chosen = self.color
        elif card.is_wild:
            if color is None:
                raise IllegalMove("Elige un color para el comodín")
            chosen = self._color(color)
        elif color is not None:
            raise IllegalMove("Solo los comodines cambian el color")
        else:
            chosen = card.color
        swaps = self.rules.relentless and card.kind == Kind.NUMBER and card.number == 7
        if swaps and len(player.hand) > 1:
            if target is None or target == seat or target not in self.active:
                raise IllegalMove("Con el 7 eliges con quién cambias la mano")
        elif target is not None:
            raise IllegalMove("Solo el 7 de Sin tregua se juega con alguien")
        # El Barrido se lleva también las demás cartas de su color.
        swept = (
            [other for other in player.hand if other.color == card.color and other.id != card.id]
            if card.kind == Kind.BARRIDO
            else []
        )
        if declare and len(player.hand) - 1 - len(swept) != 1:
            raise IllegalMove("«¡Última!» se dice al jugar la penúltima carta")

        self._close_window(seat)
        bluff = card.kind in RESTRICTED and self._has_color(seat, self.color, excluding=card)
        player.hand.remove(card)
        for other in swept:
            player.hand.remove(other)
        self.discard += [*swept, card]  # las barridas, debajo
        self.drawn = None
        self.color = chosen
        self.events.append(Event("play", seat, card=card, color=chosen))
        if swept:
            self.events.append(Event("sweep", seat, cards=tuple(swept), count=len(swept), color=chosen))
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
            self._apply(seat, card, bluff, target)

    def draw(self, seat: int) -> None:
        """Roba: una carta (que, si sirve, se puede jugar ya) o todas las acumuladas."""
        self._require(seat, Phase.PLAYING)
        if self.drawn is not None:
            raise IllegalMove("Ya has robado: juega la carta robada o pasa")
        self._close_window(seat)
        self.armed.discard(seat)
        if self.pending_draw:
            count = self.pending_draw
            self.pending_draw, self.pending_kind, self.pending_min = 0, None, 0
            self._draw_cards(seat, count, "acumuladas")
            if self.rules.relentless:
                self.events.append(Event("skip", seat))
            self.turn = self.next_seat(seat)
            self._check_mercy(seat)
            return
        if self.rules.relentless:
            # Sin tregua: se roba hasta sacar una carta que se pueda jugar.
            drawn = self._draw_until_playable(seat)
            if self._check_mercy(seat):
                return
        else:
            drawn = self._draw_cards(seat, 1, "turno")
        self.dry_turns = 0 if drawn else self.dry_turns + 1
        if self.dry_turns >= len(self.active):
            self._block_round()  # nadie ha podido jugar ni robar en una vuelta entera
        elif drawn and self.can_play(seat, drawn[-1]):
            self.drawn = drawn[-1]  # puede jugarla ahora o quedársela
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
        """No desafía el comodín: roba lo que manda (4, 2 o hasta el color) y pierde su turno."""
        self._require(seat, Phase.CHALLENGE)
        self._close_window(seat)
        play, self.wild = self.wild, None
        assert play is not None
        self.phase = Phase.PLAYING
        self._penalty(seat, play.kind)
        self.events.append(Event("skip", seat))
        self.turn = self.next_seat(seat)

    def challenge(self, seat: int) -> None:
        """Desafía el comodín. Si era un farol, roba quien lo jugó; si no, el
        desafiante roba lo que mandaba más 2 y pierde su turno."""
        self._require(seat, Phase.CHALLENGE)
        self._close_window(seat)
        play, self.wild = self.wild, None
        assert play is not None
        self.phase = Phase.PLAYING
        if play.illegal:
            self.events.append(Event("challenge", seat, target=play.seat, result="guilty"))
            self._penalty(play.seat, play.kind, reason="desafio")
            self.turn = seat  # el desafiante juega su turno con normalidad
        else:
            self.events.append(Event("challenge", seat, target=play.seat, result="innocent"))
            self._penalty(seat, play.kind, extra=2, reason="desafio")
            self.events.append(Event("skip", seat))
            self.turn = self.next_seat(seat)

    def roulette(self, seat: int, color: Color | str) -> None:
        """Sin tregua: quien sufre la Ruleta elige un color y destapa cartas del mazo
        hasta que sale (los comodines no cuentan). Se las queda todas y pierde el turno."""
        self._require(seat, Phase.ROULETTE)
        self._close_window(seat)
        self.color = self._color(color)
        self.phase = Phase.PLAYING
        self._draw_until(seat, self.color, "ruleta", public=True)
        self.events.append(Event("skip", seat))
        self.turn = self.next_seat(seat)
        self._check_mercy(seat)

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
                    Phase.CHALLENGE: "Primero hay que decidir si se desafía el comodín",
                    Phase.ROULETTE: "Primero hay que elegir el color de la Ruleta",
                    Phase.ROUND_OVER: "La ronda ha terminado",
                    Phase.PLAYING: "Ahora no se puede hacer eso",
                }[self.phase]
            )
        if seat != self.turn:
            raise IllegalMove("No es tu turno")

    def _color(self, color: Color | str) -> Color:
        """Un color de los que están en juego (los de la cara de sombra, en la sombra)."""
        try:
            chosen = Color(color)
        except ValueError:
            raise IllegalMove(f"Color desconocido: {color!r}") from None
        if chosen not in self.colors:
            raise IllegalMove("Ese color no está en juego en esta cara")
        return chosen

    def _cannot_start(self, card: PrismaCard) -> bool:
        """¿Vuelve al mazo si sale como primera carta?"""
        if self.mode == Mode.SIN_TREGUA:
            return card.kind != Kind.NUMBER  # siempre empieza un número
        if self.mode == Mode.DOBLE:
            return card.kind in (Kind.CAMALEON2, Kind.ECLIPSE)
        return card.kind == Kind.CAMALEON4

    def _has_color(self, seat: int, color: Color | None, excluding: PrismaCard) -> bool:
        return any(card.color == color and card.id != excluding.id for card in self.players[seat].hand)

    def _why_not(self, seat: int, card: PrismaCard) -> str:
        if self.pending_draw:
            if self.rules.relentless:
                return f"Tienes que acumular una carga de +{self.pending_min} o más, o robar las acumuladas"
            return "Tienes que acumular otra carta igual o robar las acumuladas"
        if card.kind in RESTRICTED:
            return f"El {card.name()} solo se puede jugar sin cartas del color de la mesa"
        return "Esa carta no casa con la de la mesa"

    def _close_window(self, actor: int) -> None:
        """Al actuar el siguiente, ya no se puede pillar a quien no dijo "¡Última!"."""
        if self.vulnerable is not None and self.vulnerable != actor:
            self.vulnerable = None

    def _reshuffle(self) -> None:
        """Se acabó el mazo: se rebaraja el descarte, menos la carta de arriba (y,
        en Sin tregua, con las cartas apartadas de los eliminados)."""
        top = self.discard.pop()
        rest, self.discard = self.discard + self.set_aside, [top]
        self.set_aside = []
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

    def _draw_until(
        self, seat: int, color: Color | None, reason: str, extra: int = 0, public: bool = False
    ) -> list[PrismaCard]:
        """Roba hasta sacar una carta de `color` (un comodín no cuenta) y luego `extra`
        más. Con `public`, las cartas se destapan a la vista de todos (la Ruleta)."""
        drawn: list[PrismaCard] = []
        while True:
            if not self.draw_pile and len(self.discard) > 1:
                self._reshuffle()
            if not self.draw_pile:
                break  # no quedan cartas en ningún sitio
            card = self.draw_pile.pop()
            drawn.append(card)
            if card.color == color:
                break
        for _ in range(extra):
            if not self.draw_pile and len(self.discard) > 1:
                self._reshuffle()
            if not self.draw_pile:
                break
            drawn.append(self.draw_pile.pop())
        player = self.players[seat]
        player.hand.extend(drawn)
        if len(player.hand) > 1:
            player.said_last = False
            if self.vulnerable == seat:
                self.vulnerable = None
        kind = "reveal" if public else "draw"
        self.events.append(Event(kind, seat, cards=tuple(drawn), count=len(drawn), color=self.color, reason=reason))
        return drawn

    def _draw_until_playable(self, seat: int) -> list[PrismaCard]:
        """Sin tregua: roba de una en una hasta sacar una carta que pueda jugar (o hasta
        que no quede nada que robar). Un único suceso con todas las robadas."""
        drawn: list[PrismaCard] = []
        while True:
            if not self.draw_pile and len(self.discard) > 1:
                self._reshuffle()
            if not self.draw_pile:
                break
            card = self.draw_pile.pop()
            drawn.append(card)
            if self.can_play(seat, card):
                break
        player = self.players[seat]
        player.hand.extend(drawn)
        if len(player.hand) > 1:
            player.said_last = False
            if self.vulnerable == seat:
                self.vulnerable = None
        self.events.append(Event("draw", seat, cards=tuple(drawn), count=len(drawn), color=self.color, reason="turno"))
        return drawn

    def _check_mercy(self, seat: int) -> bool:
        """Sin tregua: con 25 cartas o más, eliminado de la ronda. Sus cartas se
        apartan hasta el próximo rebarajado. Si solo queda uno, gana la ronda.
        Devuelve si lo ha eliminado."""
        player = self.players[seat]
        if not self.rules.relentless or seat in self.out or len(player.hand) < MERCY_LIMIT:
            return False
        self.out.add(seat)
        self.set_aside += player.hand
        count, player.hand = len(player.hand), []
        player.said_last = False
        if self.vulnerable == seat:
            self.vulnerable = None
        self.armed.discard(seat)
        self.events.append(Event("eliminated", seat, count=count))
        if self.drawn is not None and self.turn == seat:
            self.drawn = None
        if self.turn == seat and self.phase == Phase.PLAYING:
            self.turn = self.next_seat(seat)  # pierde lo que le quedara de turno
        if len(self.active) == 1:
            self._close_round(self.active[0])
        return True

    def _swap(self, seat: int, target: int) -> None:
        """El 7 de Sin tregua: cambia su mano por la de `target`."""
        mine, theirs = self.players[seat], self.players[target]
        mine.hand, theirs.hand = theirs.hand, mine.hand
        self.events.append(Event("swap", seat, target=target, hands=self._hands()))
        self._after_hands_move()

    def _rotate(self, seat: int) -> None:
        """El 0 de Sin tregua: cada uno pasa su mano al siguiente, en el sentido del juego."""
        seats = self.active
        hands = {s: self.players[s].hand for s in seats}
        for s in seats:
            self.players[self.next_seat(s)].hand = hands[s]
        self.events.append(Event("rotate", seat, result="left" if self.direction < 0 else "right", hands=self._hands()))
        self._after_hands_move()

    def _hands(self) -> tuple[tuple[PrismaCard, ...], ...]:
        """Una foto de las manos de todos (para los sucesos que las cambian)."""
        return tuple(tuple(player.hand) for player in self.players)

    def _after_hands_move(self) -> None:
        """Tras cambiar manos: nadie puede ser pillado por una carta que no ha jugado él.
        Quien se queda con una sola carta así, queda a salvo."""
        self.vulnerable = None
        self.armed = set()
        for player in self.players:
            player.said_last = len(player.hand) == 1

    def _penalty(self, seat: int, kind: Kind, extra: int = 0, reason: str | None = None) -> None:
        """Lo que hace robar un comodín restringido: sus cartas, o hasta el color (Sabueso)."""
        if kind == Kind.SABUESO:
            self._draw_until(seat, self.color, reason or "sabueso", extra)
        else:
            self._draw_cards(seat, DRAW_VALUE[kind] + extra, reason or kind.value)

    def _eclipse(self, seat: int) -> None:
        """Doble cara: todo da la vuelta. El descarte entero (la de abajo queda arriba),
        el mazo y las manos. Lo que queda arriba no hace nada; si es un comodín, quien
        jugó el Eclipse elige el color."""
        self.discard = [card.flipped() for card in reversed(self.discard)]
        self.draw_pile = [card.flipped() for card in reversed(self.draw_pile)]
        for player in self.players:
            player.hand = [card.flipped() for card in player.hand]
        self.side = Side.SOMBRA if self.side == Side.LUZ else Side.LUZ
        top = self.top
        self.events.append(Event("eclipse", seat, card=top, result=self.side.value, hands=self._hands()))
        if top.is_wild:
            self.phase = Phase.CHOOSE_COLOR
            self.turn = seat
            self.after_color = self.next_seat(seat)
        else:
            self.color = top.color
            self.turn = self.next_seat(seat)

    def _apply(self, seat: int, card: PrismaCard, bluff: bool, target: int | None = None) -> None:
        """El efecto de la carta jugada y a quién le toca después."""
        victim = self.next_seat(seat)
        kind = card.kind
        if self.rules.relentless and kind == Kind.NUMBER and card.number in (0, 7):
            if card.number == 7:
                assert target is not None
                self._swap(seat, target)
            else:
                self._rotate(seat)
            self.turn = victim
        elif kind in (Kind.NUMBER, Kind.CAMALEON, Kind.BARRIDO):
            self.turn = victim
        elif kind == Kind.PAUSA:
            self.events.append(Event("skip", victim))
            self.turn = self.next_seat(seat, 2)
        elif kind == Kind.PAUSA_TOTAL:
            # Todos pierden el turno: vuelve a jugar quien la puso.
            self.events.append(Event("skip_all", seat))
            self.turn = seat
        elif kind == Kind.REMOLINO:
            self.direction *= -1
            self.events.append(Event("reverse", result="left" if self.direction < 0 else "right"))
            if len(self.active) == 2:
                # Con dos jugadores es como una Pausa: vuelve a jugar el mismo.
                self.events.append(Event("skip", victim))
                self.turn = seat
            else:
                self.turn = self.next_seat(seat)
        elif kind == Kind.ECLIPSE:
            self._eclipse(seat)
        elif self.rules.relentless and card.draw_value:
            # Sin tregua: las cargas se acumulan. El Camaleón Remolino +4 además cambia
            # el sentido (con dos jugadores, la carga le toca a quien lo jugó).
            if kind == Kind.CAMALEON_REMOLINO4:
                self.direction *= -1
                self.events.append(Event("reverse", result="left" if self.direction < 0 else "right"))
                self.turn = seat if len(self.active) == 2 else self.next_seat(seat)
            else:
                self.turn = victim
            self.pending_draw += card.draw_value
            self.pending_min = card.draw_value
            self.events.append(Event("stack", self.turn, count=self.pending_draw))
        elif kind == Kind.RULETA:
            self.phase = Phase.ROULETTE
            self.turn = victim
        elif kind == Kind.CARGA and self.rules.stack_draw2:
            self.pending_draw += 2
            self.pending_kind = Kind.CARGA
            self.turn = victim
        elif kind in (Kind.CARGA, Kind.CARGA1, Kind.CARGA5):
            self._draw_cards(victim, card.draw_value, kind.value)
            self.events.append(Event("skip", victim))
            self.turn = self.next_seat(seat, 2)
        elif kind == Kind.CAMALEON4 and self.rules.stack_draw4:
            self.pending_draw += 4
            self.pending_kind = Kind.CAMALEON4
            self.turn = victim
        elif kind in RESTRICTED:
            if self.rules.challenge_active:
                self.wild = WildPlay(seat, kind, bluff)
                self.phase = Phase.CHALLENGE
                self.turn = victim
            else:
                self._penalty(victim, kind)
                self.events.append(Event("skip", victim))
                self.turn = self.next_seat(seat, 2)
        else:
            raise AssertionError(f"Carta sin efecto definido: {card}")

    def _finish_round(self, winner: int, last: PrismaCard) -> None:
        """Alguien se quedó sin cartas. Si su última carta hace robar, el siguiente roba igual."""
        if last.kind == Kind.CAMALEON_REMOLINO4:
            self.direction *= -1  # cambia el sentido: roba quien jugó antes
        victim = self.next_seat(winner)
        if last.kind == Kind.SABUESO:
            self._draw_until(victim, self.color, "final")
        elif last.draw_value or self.pending_draw:
            self._draw_cards(victim, self.pending_draw + last.draw_value, "final")
        self._close_round(winner)

    def _block_round(self) -> None:
        """Ronda trancada: no queda nada que robar y nadie ha jugado en una vuelta entera.

        Gana quien tiene menos cartas; si empatan, quien suma menos puntos, y si
        siguen empatados, el primero de la mesa.
        """
        winner = min(
            (p for p in self.players if p.seat not in self.out),
            key=lambda p: (len(p.hand), sum(card.points_in(self.mode) for card in p.hand), p.seat),
        )
        self.events.append(Event("blocked", winner.seat))
        self._close_round(winner.seat)

    def _close_round(self, winner: int) -> None:
        self.pending_draw, self.pending_kind, self.pending_min = 0, None, 0
        self.drawn = None
        self.vulnerable = None
        self.winner = winner
        self.phase = Phase.ROUND_OVER
        points = sum(card.points_in(self.mode) for p in self.players if p.seat != winner for card in p.hand)
        points += KNOCKOUT_POINTS * len(self.out)  # Sin tregua: cada eliminado vale 250
        if self.rules.scoring:
            self.players[winner].score += points
        self.events.append(Event("round_over", winner, count=points))
        assert self.total_cards() == self.rules.deck_size
