import random
from itertools import combinations

import pytest

from poker_engine import HandCategory as C
from poker_engine import evaluate, full_deck, parse_cards


def ev(text):
    return evaluate(parse_cards(text))


# Una mano de 5 cartas por categoría, de la más débil a la más fuerte.
FIVE_CARD_HANDS = [
    ("As Kd 9h 5c 2d", C.HIGH_CARD, (14, 13, 9, 5, 2)),
    ("As Ad 9h 5c 2d", C.PAIR, (14, 9, 5, 2)),
    ("As Ad 9h 9c 2d", C.TWO_PAIR, (14, 9, 2)),
    ("As Ad Ah 9c 2d", C.THREE_OF_A_KIND, (14, 9, 2)),
    ("9s 8d 7h 6c 5d", C.STRAIGHT, (9,)),
    ("As Js 9s 5s 2s", C.FLUSH, (14, 11, 9, 5, 2)),
    ("As Ad Ah 9c 9d", C.FULL_HOUSE, (14, 9)),
    ("As Ad Ah Ac 9d", C.FOUR_OF_A_KIND, (14, 9)),
    ("9s 8s 7s 6s 5s", C.STRAIGHT_FLUSH, (9,)),
    ("As Ks Qs Js Ts", C.ROYAL_FLUSH, (14,)),
]


@pytest.mark.parametrize("text, category, tiebreak", FIVE_CARD_HANDS)
def test_ten_categories_with_five_cards(text, category, tiebreak):
    assert ev(text) == (category, tiebreak)


def test_there_are_ten_categories_in_strict_order():
    values = [ev(text) for text, _, _ in FIVE_CARD_HANDS]
    assert len({value[0] for value in values}) == 10 == len(C)
    assert all(weaker < stronger for weaker, stronger in zip(values, values[1:]))


@pytest.mark.parametrize(
    "text, category, tiebreak",
    [
        ("As Kd 9h 5c 2d 7s 8h", C.HIGH_CARD, (14, 13, 9, 8, 7)),
        ("As Ad 9h 5c 2d 7s 8h", C.PAIR, (14, 9, 8, 7)),
        # Tres parejas: cuentan las dos mejores y el kicker más alto restante.
        ("As Ad Kh Kc 9d 9s 2h", C.TWO_PAIR, (14, 13, 9)),
        ("As Ad Ah 9c 2d 7s 8h", C.THREE_OF_A_KIND, (14, 9, 8)),
        # Escalera de 6 cartas: se queda con la más alta.
        ("4s 5d 6h 7c 8d 9s Kh", C.STRAIGHT, (9,)),
        # Seis cartas del mismo palo: las cinco más altas.
        ("As Js 9s 5s 2s Ks 3d", C.FLUSH, (14, 13, 11, 9, 5)),
        # Hay escalera y color a la vez, pero no escalera de color.
        ("9s 8s 7s 6d 5d 2s Ks", C.FLUSH, (13, 9, 8, 7, 2)),
        # Dos tríos: el mayor hace de trío y el menor de pareja.
        ("As Ad Ah Kc Kd Ks 2h", C.FULL_HOUSE, (14, 13)),
        # Trío y dos parejas: se usa la pareja más alta.
        ("9s 9d 9h Kc Kd 2s 2h", C.FULL_HOUSE, (9, 13)),
        ("As Ad Ah Ac 9d 9s Kh", C.FOUR_OF_A_KIND, (14, 13)),
        # La escalera de color manda aunque exista una escalera normal más alta.
        ("5s 6s 7s 8s 9s Td Jd", C.STRAIGHT_FLUSH, (9,)),
        ("As Ks Qs Js Ts 9s 8s", C.ROYAL_FLUSH, (14,)),
    ],
)
def test_best_five_out_of_seven(text, category, tiebreak):
    assert ev(text) == (category, tiebreak)


def test_six_cards():
    assert ev("As Ad 9h 9c 2d 2s") == (C.TWO_PAIR, (14, 9, 2))


def test_wheel_is_the_lowest_straight():
    assert ev("As 2d 3h 4c 5d") == (C.STRAIGHT, (5,))
    assert ev("As 2d 3h 4c 5d") < ev("2s 3d 4h 5c 6d")


def test_steel_wheel_is_a_straight_flush_not_royal():
    assert ev("As 2s 3s 4s 5s") == (C.STRAIGHT_FLUSH, (5,))


def test_ace_does_not_wrap_around():
    assert ev("Qs Kd Ah 2c 3d")[0] is C.HIGH_CARD


@pytest.mark.parametrize("text", ["As Kd 9h 5c", "As Kd 9h 5c 2d 7s 8h 3c"])
def test_rejects_wrong_number_of_cards(text):
    with pytest.raises(ValueError):
        ev(text)


def test_rejects_repeated_cards():
    with pytest.raises(ValueError):
        ev("As As 9h 5c 2d")


@pytest.mark.parametrize("size", [6, 7])
def test_matches_brute_force_over_five_card_subsets(size):
    """La evaluación directa coincide con probar todas las combinaciones de 5."""
    rng = random.Random(20261009)
    deck = full_deck()
    for _ in range(3000):
        cards = rng.sample(deck, size)
        expected = max(evaluate(list(combo)) for combo in combinations(cards, 5))
        assert evaluate(cards) == expected, cards
