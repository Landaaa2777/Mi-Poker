"""Ayudantes de los tests de Prisma: mesas con las manos preparadas."""

from __future__ import annotations

import random
from dataclasses import replace

from games.prisma.engine import Kind, Mode, Phase, PrismaCard, PrismaGame, PrismaRules, full_deck


def take(codes: str, pool: list[PrismaCard]) -> list[PrismaCard]:
    """Saca del montón las cartas pedidas por su nombre corto ("panal-7", "camaleon4"...)."""
    taken = []
    for code in codes.split():
        card = next(card for card in pool if card.code == code)
        pool.remove(card)
        taken.append(card)
    return taken


def rigged(hands: list[str], first: str, rest: str = "", **rules) -> PrismaGame:
    """Mesa con las manos, la primera carta del descarte y el mazo preparados.

    `hands[i]` son las cartas del jugador i (todas las manos del mismo tamaño).
    Empieza jugando el jugador 0 y el turno va 0, 1, 2… `rest` son las primeras
    cartas que se robarán, en orden; detrás va el resto del mazo. Con
    `mode=Mode.SIN_TREGUA` las cartas salen de su mazo de 168.
    """
    pool = full_deck(rules.get("mode", Mode.CLASICO))
    cards = [take(hand, pool) for hand in hands]
    size = len(cards[0])
    deck = [cards[seat][index] for index in range(size) for seat in range(len(hands))]
    deck += take(first, pool) + take(rest, pool) + pool
    game = PrismaGame(
        [f"J{seat}" for seat in range(len(hands))],
        replace(PrismaRules(**rules), hand_size=size),
        rng=random.Random(0),
    )
    game.dealer = len(hands) - 2  # al empezar la ronda reparte el último, y juega el 0
    game.start_round(deck)
    return game


def take_double(spec: str, pool: list[PrismaCard]) -> PrismaCard:
    """Doble cara: saca del montón una carta con la cara de luz pedida y, si se
    pide ("panal-7/brasa-3"), con esa cara de sombra. Para conseguirla se
    intercambian las caras de sombra de dos cartas del montón: las caras del
    mazo siguen siendo las mismas, solo cambia cómo van emparejadas."""
    light, _, dark = spec.partition("/")
    card = next(card for card in pool if card.code == light)
    index = pool.index(card)
    if dark:
        assert card.back is not None
        if card.back.code != dark:
            other_index = next(i for i, other in enumerate(pool) if other.back is not None and other.back.code == dark)
            other = pool[other_index]
            assert other.back is not None
            pool[other_index] = replace(other, back=replace(card.back, id=other.id))
            card = replace(card, back=replace(other.back, id=card.id))
    pool.pop(index)
    return card


def rigged_double(hands: list[str], first: str, rest: str = "", **rules) -> PrismaGame:
    """Como `rigged`, en Doble cara. Cada carta es "luz" o "luz/sombra"."""
    pool = full_deck(Mode.DOBLE)
    cards = [[take_double(spec, pool) for spec in hand.split()] for hand in hands]
    size = len(cards[0])
    deck = [cards[seat][index] for index in range(size) for seat in range(len(hands))]
    deck += [take_double(spec, pool) for spec in first.split()]
    deck += [take_double(spec, pool) for spec in rest.split()] + pool
    game = PrismaGame(
        [f"J{seat}" for seat in range(len(hands))],
        replace(PrismaRules(mode=Mode.DOBLE, **rules), hand_size=size),
        rng=random.Random(0),
    )
    game.dealer = len(hands) - 2
    game.start_round(deck)
    return game


def card_id(game: PrismaGame, seat: int, code: str) -> int:
    """El id de una carta de la mano de `seat`, por su nombre corto."""
    return next(card.id for card in game.players[seat].hand if card.code == code)


def codes(game: PrismaGame, seat: int) -> list[str]:
    return [card.code for card in game.players[seat].hand]


def random_move(game: PrismaGame, rng: random.Random) -> None:
    """Una jugada legal cualquiera del jugador al que le toca (y a veces, pillar)."""
    seat = game.turn
    if game.vulnerable is not None and rng.random() < 0.3:
        accuser = rng.choice([p.seat for p in game.players if p.seat != game.vulnerable])
        game.catch(accuser)
        return
    if game.phase == Phase.CHOOSE_COLOR:
        game.choose_color(seat, rng.choice(game.colors))
    elif game.phase == Phase.ROULETTE:
        game.roulette(seat, rng.choice(game.colors))
    elif game.phase == Phase.CHALLENGE:
        (game.challenge if rng.random() < 0.4 else game.accept)(seat)
    else:
        if game.vulnerable == seat or (game.can_declare(seat) and rng.random() < 0.3):
            if rng.random() < 0.6:
                game.declare_last(seat)
                return
        plays = game.legal_plays(seat)
        if plays and rng.random() < 0.85:
            card = rng.choice(plays)
            hand = game.players[seat].hand
            color = rng.choice(game.colors) if card.is_wild and card.kind != Kind.RULETA else None
            target = None
            if game.rules.relentless and card.kind == Kind.NUMBER and card.number == 7 and len(hand) > 1:
                target = rng.choice([other for other in game.active if other != seat])
            swept = sum(other.color == card.color and other.id != card.id for other in hand) if card.kind == Kind.BARRIDO else 0
            declare = len(hand) - 1 - swept == 1 and rng.random() < 0.5
            game.play(seat, card.id, color, declare=declare, target=target)
        elif game.drawn is not None:
            game.pass_turn(seat)
        else:
            game.draw(seat)
