"""Valor de las manos (ases blandos y duros) y el zapato con su carta de corte."""

import random
from collections import Counter

import pytest

from core import shuffle
from core.cards import full_deck, parse_cards
from games.blackjack.engine import Shoe, card_value, hand_total, is_blackjack, is_bust


@pytest.mark.parametrize(
    ("cards", "total", "soft"),
    [
        ("Ah 6d", 17, True),  # As como 11: blanda
        ("Ah 6d 9c", 16, False),  # el As pasa a valer 1
        ("Ah Ad", 12, True),  # solo un As puede valer 11
        ("Ah Ad 9c", 21, True),
        ("Ah Ad Ac Ah", 14, True),
        ("Kh Qd", 20, False),
        ("Jh 5d 6c", 21, False),
        ("Th 9d 5c", 24, False),
        ("2h 3d 4c 5s 6h", 20, False),
        ("Ah 5d Kc", 16, False),
    ],
)
def test_hand_totals_with_soft_and_hard_aces(cards, total, soft):
    assert hand_total(parse_cards(cards)) == (total, soft)


def test_card_values():
    assert [card_value(card) for card in parse_cards("2c 9d Th Js Qc Kd Ah")] == [2, 9, 10, 10, 10, 10, 11]


def test_blackjack_is_two_cards_making_21_but_not_after_splitting():
    assert is_blackjack(parse_cards("Ah Kd"))
    assert is_blackjack(parse_cards("Ts Ac"))
    assert not is_blackjack(parse_cards("Ah 5d 5c"))  # 21 con tres cartas
    assert not is_blackjack(parse_cards("Ah Kd"), from_split=True)  # tras dividir es un 21 normal
    assert is_bust(parse_cards("Kh Qd 2c")) and not is_bust(parse_cards("Ah Kd Qc"))


def test_a_six_deck_shoe_has_every_card_six_times():
    shoe = Shoe(6, rng=random.Random(1))
    dealt = [shoe.deal() for _ in range(312)]
    assert shoe.total == 312 and len(shoe) == 0
    assert Counter(dealt) == Counter(full_deck() * 6)


def test_the_shoe_is_shuffled_with_the_system_generator(monkeypatch):
    calls = []

    class Spy(random.SystemRandom):
        def shuffle(self, cards):
            calls.append(len(cards))
            super().shuffle(cards)

    monkeypatch.setattr("games.blackjack.engine.shoe.SYSTEM_RNG", Spy())
    Shoe(6)
    assert calls == [312]
    assert isinstance(shuffle.SYSTEM_RNG, random.SystemRandom)


def test_the_cut_card_goes_around_three_quarters():
    for seed in range(30):
        shoe = Shoe(6, rng=random.Random(seed))
        dealt = 0
        while not shoe.cut_reached:
            shoe.deal()
            dealt += 1
        assert 234 - 12 <= dealt <= 234 + 12  # 75 % de 312, con margen de dos cartas por mazo


def test_reshuffling_brings_every_card_back():
    shoe = Shoe(2, rng=random.Random(3))
    for _ in range(90):
        shoe.deal()
    assert shoe.cut_reached
    shoe.reshuffle()
    assert len(shoe) == 104 and not shoe.cut_reached and shoe.shuffles == 2


def test_an_empty_shoe_mid_round_never_deals_a_card_that_is_on_the_table():
    shoe = Shoe(1, rng=random.Random(5))
    on_table = [shoe.deal() for _ in range(52)]
    keep = on_table[-6:]  # estas siguen en la mesa
    fresh = [shoe.deal(keep) for _ in range(46)]
    assert Counter(fresh + keep) == Counter(full_deck())


def test_a_fixed_shoe_keeps_its_order():
    cards = parse_cards("Ah Kd 9s 7c")
    shoe = Shoe(cards=cards)
    assert [shoe.deal() for _ in range(4)] == cards
    with pytest.raises(ValueError):
        shoe.deal()
