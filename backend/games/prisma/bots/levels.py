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
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from core.bots import LEVEL_NAMES
from core.shuffle import SYSTEM_RNG
from games.prisma.engine import Color, Kind, PrismaCard, TableView


@dataclass(frozen=True)
class Move:
    """Lo que decide un bot. `kind`: play, draw, pass, choose_color, challenge o accept."""

    kind: str
    card: int | None = None  # id de la carta, al jugar
    color: Color | None = None  # al jugar un comodín o elegir color
    declare: bool = False  # dice "¡Última!" a la vez que juega


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
        if legal.challenge:
            return Move("challenge" if self.wants_challenge(view) else "accept")
        if not (legal.play or legal.draw or legal.pass_turn):
            raise ValueError("No es el turno de este bot")
        if legal.play:
            card = self.pick_card(view, [view.card(card_id) for card_id in legal.play])
            if card is not None:
                color = self.pick_color(view, card) if card.is_wild else None
                declare = len(view.hand) == 2 and self.rng.random() < self.declare_chance
                return Move("play", card.id, color, declare)
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


# --- Ayudas para leer la vista ---


def color_counts(view: TableView, without: PrismaCard | None = None) -> Counter:
    return Counter(
        card.color for card in view.hand if card.color is not None and (without is None or card.id != without.id)
    )


def most_common_color(view: TableView, wild: PrismaCard | None, rng: random.Random) -> Color:
    counts = color_counts(view, wild)
    if not counts:
        return rng.choice(list(Color))
    best = max(counts.values())
    return rng.choice([color for color, count in counts.items() if count == best])


def next_seat(view: TableView, steps: int = 1) -> int:
    return (view.viewer_seat + view.direction * steps) % len(view.players)


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
        return self.rng.choice(playable)

    def pick_color(self, view: TableView, wild: PrismaCard | None) -> Color:
        return self.rng.choice(list(Color))

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
        return max(playable, key=lambda card: (card.points, self.rng.random()))

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
        if card.kind in (Kind.PAUSA, Kind.CARGA):
            # Las cartas de ataque se guardan para cuando hay a quién frenar.
            value += (14 if card.kind == Kind.CARGA else 11) if threat else -5
        elif card.kind == Kind.REMOLINO:
            previous = view.players[next_seat(view, -1)]
            value += 8 if threat and previous.count > target.count else -3
        return value

    def pick_color(self, view: TableView, wild: PrismaCard | None) -> Color:
        counts = color_counts(view, wild)
        missing = missing_colors(view)[next_seat(view)]
        return max(
            Color,
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
