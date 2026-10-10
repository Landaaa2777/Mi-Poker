"""Herramientas de los bots: ranking preflop, equity Monte Carlo y lectura de la mano."""

import random

import pytest

from bots.equity import estimate_equity
from bots.postflop import read_hand
from bots.preflop import RANKED_COMBOS, combos_in_top, top_fraction
from poker_engine import HandCategory, parse_cards


def top(text):
    return top_fraction(parse_cards(text))


def test_every_starting_hand_is_ranked():
    assert len(RANKED_COMBOS) == 1326
    assert len({frozenset(combo) for combo in RANKED_COMBOS}) == 1326


def test_preflop_ranking_order():
    assert top("As Ah") == pytest.approx(6 / 1326)
    assert top("As Ah") < top("Ks Kh") < top("Qs Qh") < top("As Kh") < top("As Jh")
    assert top("As Ks") < top("As Kh")  # del mismo palo vale más
    assert top("Js Ts") < top("Js 6h")  # conectadas valen más
    assert top("7s 2h") == 1.0
    assert top("Ah As") == top("Ad Ac")


def test_combos_in_top_returns_the_best_hands():
    best = combos_in_top(0.05)
    assert best == RANKED_COMBOS[: round(0.05 * 1326)]
    assert {frozenset(parse_cards("As Ah")), frozenset(parse_cards("Kd Kc"))} <= set(map(frozenset, best))
    assert len(combos_in_top(0.0)) == 6  # nunca menos que AA
    assert len(combos_in_top(1.0)) == 1326


@pytest.mark.parametrize(
    ("hole", "expected"),
    [("As Ah", 0.85), ("Ks Qs", 0.63), ("7s 2h", 0.35)],
)
def test_preflop_equity_against_one_random_hand(hole, expected):
    equity = estimate_equity(parse_cards(hole), [], 1, 4000, random.Random(1))
    assert equity == pytest.approx(expected, abs=0.03)


def test_equity_drops_with_more_opponents():
    rng = random.Random(2)
    hole = parse_cards("As Ah")
    one = estimate_equity(hole, [], 1, 3000, rng)
    four = estimate_equity(hole, [], 4, 3000, rng)
    assert four < one - 0.2


def test_equity_of_the_nuts_and_of_a_dead_hand():
    rng = random.Random(3)
    board = parse_cards("Ts Js Qs 2d 3c")
    assert estimate_equity(parse_cards("As Ks"), board, 3, 300, rng) == 1.0
    # La mesa es escalera real: todos empatan.
    royal = parse_cards("Ts Js Qs Ks As")
    assert estimate_equity(parse_cards("2d 3c"), royal, 1, 300, rng) == 0.5
    # Con 7-2 en una mesa sin ayuda casi nunca se gana.
    assert estimate_equity(parse_cards("7d 2c"), parse_cards("As Kd 9h 5c 3s"), 1, 600, rng) < 0.15


def test_equity_is_lower_against_a_strong_range():
    rng = random.Random(4)
    hole = parse_cards("Ks Kh")
    against_any = estimate_equity(hole, [], 1, 3000, rng)
    against_premium = estimate_equity(hole, [], 1, 3000, rng, ranges=[0.01])
    assert against_any > 0.78
    assert against_premium < 0.5


def test_equity_with_ranges_never_reuses_known_cards():
    rng = random.Random(5)
    # El rango rival es AA-KK y el bot tiene dos ases: quedan pocas combinaciones.
    equity = estimate_equity(parse_cards("As Ah"), parse_cards("Ad 7c 2s"), 2, 500, rng, [0.01, 0.01])
    assert 0.0 <= equity <= 1.0


def test_equity_is_repeatable_with_the_same_seed():
    hole, board = parse_cards("9s 9h"), parse_cards("2c 7d Kh")
    first = estimate_equity(hole, board, 2, 500, random.Random(9))
    second = estimate_equity(hole, board, 2, 500, random.Random(9))
    assert first == second


@pytest.mark.parametrize(
    ("hole", "board", "category", "low", "high", "outs"),
    [
        ("As Kd", "Ah 7c 2s", HandCategory.PAIR, 0.7, 0.75, 0),  # pareja máxima, buen kicker
        ("Ad 4d", "Ah 7c 2s", HandCategory.PAIR, 0.6, 0.69, 0),  # pareja máxima, mal kicker
        ("Qs Qd", "Jh 7c 2s", HandCategory.PAIR, 0.75, 0.8, 0),  # overpair
        ("8s 7d", "Ah 7c 2s", HandCategory.PAIR, 0.5, 0.55, 0),  # segunda pareja
        ("3s 2d", "Ah 7c 2s", HandCategory.PAIR, 0.35, 0.45, 0),  # pareja baja
        ("7s 7d", "Ah 7c 2s", HandCategory.THREE_OF_A_KIND, 0.9, 1.0, 0),  # set
        ("As 7d", "Ah 7c 2s", HandCategory.TWO_PAIR, 0.85, 0.9, 0),
        ("Ks Qd", "9h 9c 2s", HandCategory.PAIR, 0.1, 0.25, 0),  # la pareja es de la mesa
        ("Ks Kd", "9h 9c 2s", HandCategory.TWO_PAIR, 0.7, 0.8, 0),  # overpair en mesa doblada
        ("Ks Qs", "9s 4s 2d", HandCategory.HIGH_CARD, 0.1, 0.25, 9),  # proyecto de color
        ("Jh Td", "9s 8c 2d", HandCategory.HIGH_CARD, 0.1, 0.25, 8),  # escalera abierta
        ("Jh Td", "9s 7c 2d", HandCategory.HIGH_CARD, 0.1, 0.25, 4),  # escalera interna
        ("Jh Tc", "9s 8s 7s Qd", HandCategory.STRAIGHT, 0.85, 0.95, 0),
        ("3h 3c", "As Ks Qs Js Ts", HandCategory.ROYAL_FLUSH, 0.1, 0.2, 0),  # juega la mesa
    ],
)
def test_read_hand(hole, board, category, low, high, outs):
    read = read_hand(parse_cards(hole), parse_cards(board))
    assert read.category is category
    assert low <= read.strength <= high
    assert read.outs == outs


def test_draw_equity_follows_the_rule_of_two_and_four():
    read = read_hand(parse_cards("Ks Qs"), parse_cards("9s 4s 2d"))
    assert read.draw_equity(1) == pytest.approx(0.18)
    assert read.draw_equity(2) == pytest.approx(0.36)
