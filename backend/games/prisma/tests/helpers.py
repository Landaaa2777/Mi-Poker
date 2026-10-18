"""Ayudantes de los tests de Prisma: mesas con las manos preparadas."""

from __future__ import annotations

import random
from dataclasses import replace

from games.prisma.engine import Color, Phase, PrismaCard, PrismaGame, PrismaRules, full_deck


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
    cartas que se robarán, en orden; detrás va el resto del mazo.
    """
    pool = full_deck()
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
        game.choose_color(seat, rng.choice(list(Color)))
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
            color = rng.choice(list(Color)) if card.is_wild else None
            game.play(seat, card.id, color, declare=len(game.players[seat].hand) == 2 and rng.random() < 0.5)
        elif game.drawn is not None:
            game.pass_turn(seat)
        else:
            game.draw(seat)
