"""Simulación de manos completas: las fichas ni se crean ni se destruyen."""

import random

import pytest

from games.poker.tests.helpers import random_action
from games.poker.engine import Game, GameConfig

HANDS_PER_TABLE_SIZE = 1000


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6])
def test_total_chips_never_change(count):
    rng = random.Random(1000 + count)
    # Blinds y stack impares para forzar repartos con fichas indivisibles.
    config = GameConfig(tuple(f"P{i}" for i in range(count)), 997, 5, 15)
    game = Game(config)
    total = config.starting_stack * count
    showdowns = split_pots = side_pots = finished_games = 0

    for _ in range(HANDS_PER_TABLE_SIZE):
        if game.is_over:
            assert game.winner.stack == total
            finished_games += 1
            game.reset()

        hand = game.start_hand()
        assert game.total_chips == total
        while not hand.is_complete:
            hand.act(hand.to_act.seat, random_action(hand.legal_actions(), rng))
            assert game.total_chips == total
            assert all(p.stack >= 0 and p.bet >= 0 for p in game.players)

        result = hand.result
        assert sum(p.stack for p in game.players) == total
        assert sum(a.amount for a in result.awards) == sum(result.payouts.values()) == hand.pot
        for award in result.awards:
            assert sum(award.payouts.values()) == award.amount
            assert set(award.winners) <= set(award.eligible)

        showdowns += result.showdown
        side_pots += len(result.awards) > 1
        split_pots += any(len(a.winners) > 1 for a in result.awards)

    # La simulación debe haber pasado de verdad por los casos difíciles.
    assert showdowns > 100
    assert finished_games > 0
    if count > 2:
        assert side_pots > 0
    assert split_pots > 0
