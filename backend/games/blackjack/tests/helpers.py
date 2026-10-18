"""Ayudantes de los tests del blackjack: mesas con el zapato preparado."""

from __future__ import annotations

import random

from core.cards import parse_cards
from games.blackjack.engine import Action, BlackjackGame, Phase, Rules, Shoe


def rigged(cards: str, players: int = 1, stack: int = 1000, **rules) -> BlackjackGame:
    """Mesa con un zapato en orden fijo.

    El reparto va así: primera carta de cada jugador, carta vista del crupier,
    segunda de cada jugador y carta tapada del crupier. Después, las que se
    pidan. Ejemplo con un jugador: "Ah Kd 9s 7c" = el jugador recibe As y 9,
    el crupier enseña K y tapa un 7.
    """
    names = [f"J{index}" for index in range(players)]
    shoe = Shoe(cards=parse_cards(cards))
    return BlackjackGame(names, stack, Rules(**rules), shoe=shoe)


def chips(game: BlackjackGame) -> int:
    return game.total_chips()


def random_round(game: BlackjackGame, rng: random.Random) -> None:
    """Juega una ronda entera con decisiones legales al azar."""
    bets = {}
    for seat in game.seats:
        if game.can_bet(seat.seat) and rng.random() < 0.9:
            top = min(seat.stack, game.rules.max_bet) // game.rules.bet_step
            low = game.rules.min_bet // game.rules.bet_step
            bets[seat.seat] = rng.randint(low, top) * game.rules.bet_step
    if not bets:
        return
    game.start_round(bets)
    while game.phase == Phase.INSURANCE:
        pending = next(seat for seat in game.seats if seat.insurance_pending)
        game.insure(pending.seat, rng.random() < 0.4)
    while game.phase == Phase.PLAYING:
        seat, _ = game.to_act
        legal = game.legal_actions(seat)
        weights = {
            Action.HIT: 4,
            Action.STAND: 4,
            Action.DOUBLE: 2,
            Action.SPLIT: 3,
            Action.SURRENDER: 1,
        }
        game.act(seat, rng.choices(legal, [weights[action] for action in legal])[0])
