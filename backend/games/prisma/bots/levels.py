"""Los bots de Prisma, del más flojo al más fuerte.

Solo ven lo que vería cualquier jugador: sus cartas, la de la mesa, el color,
cuántas cartas tiene cada uno y el historial de jugadas. Nunca las cartas de
los demás ni el mazo.

- Fácil: juega una carta legal al azar y a menudo olvida decir "¡Última!".
- Medio: suelta primero las cartas que más valen, elige como color el que más
  tiene y casi siempre dice "¡Última!".
- Difícil: recuerda qué colores no tienen los rivales (quien robó con un color
  en la mesa probablemente no lo tiene), guarda los comodines para el final y
  usa las cartas de ataque contra quien va ganando.
- Experto: como Difícil, con mejor final de mano, sin olvidar nunca
  "¡Última!" y con algo de azar para no ser previsible.

En los modos nuevos, además:

- Doble cara: Difícil y Experto miran la otra cara de las cartas de los demás
  (la que ven) para decidir si les conviene dar la vuelta a la mesa con un
  Eclipse, y guardan Carga +5, Pausa total y Sabueso para frenar a quien va
  ganando.
- Sin tregua: al acumular, Difícil pone la carga más pequeña que vale (guarda
  las grandes) y Experto, la más grande si el siguiente está cerca de ganar.
  Barren con el Barrido cuando se llevan muchas cartas, cambian la mano con
  el 7 con quien tiene menos y piden en la Ruleta el color del que quedan más
  cartas por salir. Fácil y Medio hacen todo eso sin pensar tanto.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from core.bots import LEVEL_NAMES
from core.shuffle import SYSTEM_RNG
from games.prisma.engine import Color, Kind, Mode, PrismaCard, TableView

# Las cartas que frenan al siguiente (o a todos).
ATTACKS = frozenset({Kind.PAUSA, Kind.CARGA, Kind.CARGA1, Kind.CARGA4, Kind.CARGA5, Kind.PAUSA_TOTAL})
# Cartas de cada palo en el mazo de Sin tregua (para saber cuántas quedan por salir).
RELENTLESS_PER_COLOR = 36


@dataclass(frozen=True)
class Move:
    """Lo que decide un bot. `kind`: play, draw, pass, choose_color, challenge,
    accept o roulette (el color de la Ruleta que le ha tocado)."""

    kind: str
    card: int | None = None  # id de la carta, al jugar
    color: Color | None = None  # al jugar un comodín, elegir color o pedir en la Ruleta
    declare: bool = False  # dice "¡Última!" a la vez que juega
    target: int | None = None  # con quién cambia la mano, al jugar un 7 en Sin tregua


class PrismaBot:
    """Lo común a todos los niveles."""

    level = "medium"
    declare_chance = 0.9  # probabilidad de acordarse de decir "¡Última!"
    catch_chance = 0.5  # probabilidad de pillar a quien no lo dijo

    def __init__(self, name: str, rng: random.Random | None = None) -> None:
        self.name = name
        self.rng = rng or SYSTEM_RNG

    @property
    def level_name(self) -> str:
        return LEVEL_NAMES[self.level]

    # --- Lo que el servidor le pregunta ---

    def decide(self, view: TableView) -> Move:
        """Su turno: elegir color inicial, desafiar o no, o jugar/robar/pasar."""
        legal = view.legal
        if legal is None:
            raise ValueError("Este bot no está en la mesa")
        if legal.choose_color:
            return Move("choose_color", color=self.pick_color(view, None))
        if legal.roulette:
            return Move("roulette", color=self.pick_roulette_color(view))
        if legal.challenge:
            return Move("challenge" if self.wants_challenge(view) else "accept")
        if not (legal.play or legal.draw or legal.pass_turn):
            raise ValueError("No es el turno de este bot")
        if legal.play:
            card = self.pick_card(view, [view.card(card_id) for card_id in legal.play])
            if card is not None:
                color = self.pick_color(view, card) if card.is_wild and card.kind != Kind.RULETA else None
                target = self.pick_target(view) if swaps(view, card) else None
                declare = len(view.hand) - 1 - swept(view, card) == 1 and self.rng.random() < self.declare_chance
                return Move("play", card.id, color, declare, target)
        return Move("pass") if legal.pass_turn else Move("draw")

    def catches(self, view: TableView) -> bool:
        """¿Pilla a quien se quedó con una carta sin decir "¡Última!"?"""
        return view.legal is not None and view.legal.catch and self.rng.random() < self.catch_chance

    def says_last(self, view: TableView) -> bool:
        """Se quedó con una carta sin decirlo: ¿se da cuenta a tiempo?"""
        return view.legal is not None and view.legal.declare and self.rng.random() < self.declare_chance / 2

    # --- Cada nivel decide a su manera ---

    def pick_card(self, view: TableView, playable: list[PrismaCard]) -> PrismaCard | None:
        """Qué carta jugar (None = robar en vez de jugar)."""
        raise NotImplementedError

    def pick_color(self, view: TableView, wild: PrismaCard | None) -> Color:
        """El color que elige al jugar un comodín (o al empezar con un Camaleón)."""
        return most_common_color(view, wild, self.rng)

    def wants_challenge(self, view: TableView) -> bool:
        return False

    def pick_target(self, view: TableView) -> int:
        """Sin tregua: con quién cambia la mano al jugar un 7 (con quien tiene menos)."""
        return min(opponents(view), key=lambda player: (player.count, self.rng.random())).seat

    def pick_roulette_color(self, view: TableView) -> Color:
        """Sin tregua: el color que pide en la Ruleta que le ha tocado (el que antes saldrá)."""
        return likeliest_color(view, self.rng)


# --- Ayudas para leer la vista ---


def relentless(view: TableView) -> bool:
    return view.mode == "sin_tregua"


def double(view: TableView) -> bool:
    return view.mode == "doble_cara"


def swaps(view: TableView, card: PrismaCard) -> bool:
    """¿Este 7 obliga a cambiar la mano? (Sin tregua, y si no es la última carta)."""
    return relentless(view) and card.kind == Kind.NUMBER and card.number == 7 and len(view.hand) > 1


def swept(view: TableView, card: PrismaCard) -> int:
    """Cuántas cartas más se lleva un Barrido (las de su color)."""
    if card.kind != Kind.BARRIDO:
        return 0
    return sum(other.color == card.color and other.id != card.id for other in view.hand)


def opponents(view: TableView):
    """Los rivales que siguen en la ronda."""
    return [player for player in view.players if player.seat != view.viewer_seat and not player.out]


def points(view: TableView, card: PrismaCard) -> int:
    """Lo que vale una carta en el modo de la partida."""
    return card.points_in(Mode(view.mode))


def likeliest_color(view: TableView, rng: random.Random) -> Color:
    """El color del que quedan más cartas por salir: las de mi mano y las ya jugadas
    (o destapadas) ya no pueden salir del mazo."""
    seen: Counter = Counter(card.color for card in view.hand if card.color is not None)
    for event in view.events:
        if event["kind"] == "play" and event["card"]["color"]:
            seen[Color(event["card"]["color"])] += 1
        elif event["kind"] in ("sweep", "reveal"):
            seen.update(Color(card["color"]) for card in event["cards"] if card["color"])
    return max(in_play(view), key=lambda color: (RELENTLESS_PER_COLOR - seen[color], rng.random()))


def in_play(view: TableView) -> list[Color]:
    """Los colores que se pueden elegir ahora (en Doble cara, los de la cara en juego)."""
    return [Color(color) for color in view.colors]


def color_counts(view: TableView, without: PrismaCard | None = None) -> Counter:
    return Counter(
        card.color for card in view.hand if card.color is not None and (without is None or card.id != without.id)
    )


def most_common_color(view: TableView, wild: PrismaCard | None, rng: random.Random) -> Color:
    counts = color_counts(view, wild)
    if not counts:
        return rng.choice(in_play(view))
    best = max(counts.values())
    return rng.choice([color for color, count in counts.items() if count == best])


def next_seat(view: TableView, steps: int = 1) -> int:
    """El asiento `steps` puestos más allá, saltando a los eliminados (Sin tregua)."""
    seat, count = view.viewer_seat, len(view.players)
    step = 1 if steps >= 0 else -1
    for _ in range(abs(steps)):
        seat = (seat + view.direction * step) % count
        while view.players[seat].out:
            seat = (seat + view.direction * step) % count
    return seat


def missing_colors(view: TableView) -> dict[int, set[Color]]:
    """Qué colores parece no tener cada rival, según lo que ha pasado en la ronda.

    Quien roba en su turno con un color en la mesa probablemente no lo tenía.
    En cuanto juega una carta de ese color, se le quita de la lista.
    """
    missing: dict[int, set[Color]] = {player.seat: set() for player in view.players}
    for event in view.events:
        seat = event["seat"]
        if seat is None:
            continue
        if event["kind"] == "draw" and event["reason"] == "turno" and event["color"]:
            missing[seat].add(Color(event["color"]))
        elif event["kind"] == "play" and event["card"]["color"]:
            missing[seat].discard(Color(event["card"]["color"]))
    return missing


class EasyBot(PrismaBot):
    """Juega cualquier carta legal y a menudo se olvida de decir "¡Última!"."""

    level = "easy"
    declare_chance = 0.45
    catch_chance = 0.25

    def pick_card(self, view: TableView, playable: list[PrismaCard]) -> PrismaCard | None:
        if view.drawn is not None:
            return playable[0] if self.rng.random() < 0.5 else None
        if view.pending_draw and self.rng.random() < 0.3:
            return None  # a veces se come la carga aunque podría pasarla
        return self.rng.choice(playable)

    def pick_color(self, view: TableView, wild: PrismaCard | None) -> Color:
        return self.rng.choice(in_play(view))

    def pick_target(self, view: TableView) -> int:
        return self.rng.choice(opponents(view)).seat

    def pick_roulette_color(self, view: TableView) -> Color:
        return self.rng.choice(in_play(view))

    def wants_challenge(self, view: TableView) -> bool:
        return self.rng.random() < 0.15


class MediumBot(PrismaBot):
    """Suelta primero lo que más vale (los comodines valen 50) y elige el color que más tiene."""

    level = "medium"
    declare_chance = 0.92
    catch_chance = 0.6

    def pick_card(self, view: TableView, playable: list[PrismaCard]) -> PrismaCard | None:
        # Quitarse de encima las cartas que más puntos valdrían al acabar la ronda:
        # primero los comodines, luego las acciones y los números altos.
        return max(playable, key=lambda card: (points(view, card), self.rng.random()))

    def wants_challenge(self, view: TableView) -> bool:
        return self.rng.random() < 0.1


class HardBot(PrismaBot):
    """Recuerda qué colores les faltan a los rivales y guarda comodines y ataques para cuando sirven."""

    level = "hard"
    declare_chance = 0.99
    catch_chance = 0.9
    attack_below = 3  # ataca a quien tenga estas cartas o menos

    def pick_card(self, view: TableView, playable: list[PrismaCard]) -> PrismaCard | None:
        ranked = sorted(playable, key=lambda card: self.score(view, card), reverse=True)
        return ranked[0] if ranked else None

    def threat(self, view: TableView) -> bool:
        """¿El siguiente está cerca de ganar (o es quien va mejor)?"""
        target = view.players[next_seat(view)]
        leader = min(player.count for player in view.players if player.seat != view.viewer_seat)
        return target.count <= self.attack_below or (target.count == leader and leader <= 4)

    def score(self, view: TableView, card: PrismaCard) -> float:
        """Lo buena que es una jugada: cuanto más alta, mejor."""
        if view.pending_draw:
            return self.stack_score(view, card)
        if relentless(view) or double(view):
            special = self.mode_score(view, card)
            if special is not None:
                return special
        hand = len(view.hand)
        counts = color_counts(view)
        target = view.players[next_seat(view)]
        missing = missing_colors(view)[target.seat]
        threat = self.threat(view)
        if card.is_wild:
            # Los comodines se guardan: sirven para cerrar la mano o para frenar al que va a ganar.
            if card.kind == Kind.CAMALEON4:
                legal = not any(other.color == Color(view.color) for other in view.hand if other.id != card.id)
                if not legal:
                    return -100  # nada de faroles
                return 20 if threat else (-2 if hand <= 2 else -20)
            return -1 if hand <= 2 else -18
        # Seguir con un color del que me quedan muchas cartas: así no tendré que robar.
        value = 2.0 * (counts[card.color] - 1)
        if card.color in missing:
            value += 3  # al siguiente le falta ese color: probablemente tendrá que robar
        if card.kind in ATTACKS:
            # Las cartas de ataque se guardan para cuando hay a quién frenar.
            strength = 11 + card.draw_value * 1.5 + (6 if card.kind == Kind.PAUSA_TOTAL else 0)
            value += strength if threat else (2 if card.kind == Kind.PAUSA_TOTAL else -5)
        elif card.kind == Kind.REMOLINO:
            previous = view.players[next_seat(view, -1)]
            value += 8 if threat and previous.count > target.count else -3
        return value

    def stack_score(self, view: TableView, card: PrismaCard) -> float:
        """Sin tregua, con una carga encima: pasarla con la más pequeña que vale."""
        return -card.draw_value

    def mode_score(self, view: TableView, card: PrismaCard) -> float | None:
        """Las cartas propias de Doble cara y Sin tregua (None: se valora como siempre)."""
        hand = len(view.hand)
        threat = self.threat(view)
        counts = color_counts(view)
        if card.kind == Kind.ECLIPSE:
            return self.eclipse_score(view) + 2.0 * (counts[card.color] - 1)
        if card.kind == Kind.SABUESO or card.kind == Kind.CAMALEON2:
            legal = not any(other.color == Color(view.color) for other in view.hand if other.id != card.id)
            if not legal:
                return -100  # nada de faroles
            return (30 if card.kind == Kind.SABUESO else 18) if threat else (-2 if hand <= 2 else -20)
        if not relentless(view):
            return None
        if card.kind == Kind.BARRIDO:
            gone = swept(view, card)
            return 6.0 * gone + (100 if gone + 1 == hand else 0)
        if card.kind == Kind.NUMBER and card.number == 7 and hand > 1:
            fewest = min(player.count for player in opponents(view))
            return 3.0 * (hand - 1 - fewest) + 2.0 * (counts[card.color] - 1)
        if card.kind == Kind.NUMBER and card.number == 0:
            previous = view.players[next_seat(view, -1)]
            return 2.5 * (hand - 1 - previous.count) + 2.0 * (counts[card.color] - 1)
        if card.is_wild:
            # Cargas grandes y Ruleta: se guardan para defenderse o para frenar al que va a ganar.
            if threat:
                return 16 + card.draw_value * 1.5 + (10 if card.kind == Kind.RULETA else 0)
            return -1 if hand <= 2 else -16 - card.draw_value
        return None

    def eclipse_score(self, view: TableView) -> float:
        """¿Conviene dar la vuelta a la mesa? Tras el Eclipse, los rivales jugarán con
        la cara que ahora les veo: si la del que va mejor es floja, adelante."""
        rivals = opponents(view)
        leader = min(rivals, key=lambda player: player.count)
        backs = leader.backs or ()
        strong = sum(face["color"] is None for face in backs) * 4 + sum(
            face["kind"] not in ("number",) for face in backs
        )
        weak = sum(face["kind"] == "number" and (face["number"] or 0) >= 6 for face in backs)
        value = (weak - strong) * 2.0
        if leader.count <= 3:
            value += 4  # cambiarle la mano al que está a punto de ganar
        return value

    def pick_color(self, view: TableView, wild: PrismaCard | None) -> Color:
        counts = color_counts(view, wild)
        missing = missing_colors(view)[next_seat(view)]
        return max(
            in_play(view),
            key=lambda color: (counts[color] * 2 + (1.5 if color in missing else 0), self.rng.random()),
        )

    def wants_challenge(self, view: TableView) -> bool:
        """Solo desafía con pruebas: quien jugó el +4 había soltado hace poco el color de antes."""
        return challenge_evidence(view)


def challenge_evidence(view: TableView) -> bool:
    """¿Hay motivos para pensar que el +4 era un farol?

    Lo era si quien lo jugó tenía cartas del color que había en la mesa. Si en
    su jugada anterior soltó ese mismo color y desde entonces no ha robado con
    él en la mesa, seguramente le quedaba alguna.
    """
    events = view.events
    index = max(i for i, event in enumerate(events) if event["kind"] == "play")
    wild4 = events[index]
    player = wild4["seat"]
    before = next((event["color"] for event in reversed(events[:index]) if event["kind"] in ("play", "choose", "start")), None)
    if before is None:
        return False
    for event in reversed(events[:index]):
        if event["seat"] != player:
            continue
        if event["kind"] == "draw" and event["reason"] == "turno":
            return False  # robó: quizá no tenía
        if event["kind"] == "play":
            return event["card"]["color"] == before and view.players[player].count >= 3
    return False


class ExpertBot(HardBot):
    """Como Difícil, cuidando el final de la mano y con algo de azar."""

    level = "expert"
    declare_chance = 1.0
    catch_chance = 0.95
    attack_below = 4

    def score(self, view: TableView, card: PrismaCard) -> float:
        value = super().score(view, card)
        target = view.players[next_seat(view)]
        hand = len(view.hand)
        missing = missing_colors(view)[target.seat]
        if target.count == 1:
            if card.kind in (Kind.CARGA, Kind.PAUSA):
                value += 30  # al que está a punto de ganar, se le para
            elif not card.is_wild and card.color not in missing:
                value -= 6  # mejor no dejarle un color que quizá tenga
        if hand == 2 and not card.is_wild and any(other.is_wild for other in view.hand):
            value += 15  # la última, el comodín: con él siempre se puede cerrar
        if hand == 2 and card.kind in (Kind.PAUSA, Kind.REMOLINO) and len(view.players) == 2:
            value += 10  # con dos jugadores, vuelvo a jugar y cierro
        return value

    knockout_from = 15  # Sin tregua: a quien tiene estas cartas o más, se le remata

    def threat(self, view: TableView) -> bool:
        """Además de frenar a quien va a ganar, en Sin tregua remata a quien está
        cerca de las 25 cartas: cada rival eliminado es uno menos que puede ganar."""
        if relentless(view) and view.players[next_seat(view)].count >= self.knockout_from:
            return True
        return super().threat(view)

    def stack_score(self, view: TableView, card: PrismaCard) -> float:
        """Con una carga encima: la más grande si el siguiente está cerca de ganar o
        de quedar eliminado (que no pueda devolverla); si no, la más pequeña que vale."""
        target = view.players[next_seat(view)]
        if target.count <= 3 or target.count >= self.knockout_from:
            return card.draw_value
        return -card.draw_value

    def pick_card(self, view: TableView, playable: list[PrismaCard]) -> PrismaCard | None:
        ranked = sorted(playable, key=lambda card: self.score(view, card), reverse=True)
        if not ranked:
            return None
        # Un poco de azar para no ser previsible, solo entre jugadas casi igual de buenas.
        if len(ranked) > 1 and self.rng.random() < 0.08:
            if abs(self.score(view, ranked[0]) - self.score(view, ranked[1])) < 2:
                return ranked[1]
        return ranked[0]

    def pick_color(self, view: TableView, wild: PrismaCard | None) -> Color:
        target = view.players[next_seat(view)]
        if target.count <= 2:
            missing = missing_colors(view)[target.seat]
            counts = color_counts(view, wild)
            mine = [color for color in missing if counts[color] > 0]
            if mine:
                return max(mine, key=lambda color: counts[color])
        return super().pick_color(view, wild)
