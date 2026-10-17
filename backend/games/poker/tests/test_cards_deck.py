import random

import pytest

from games.poker.engine import Card, Deck, Rank, Suit, full_deck, parse_cards
from games.poker.engine import deck as deck_module


def test_parse_and_str_roundtrip():
    for card in full_deck():
        assert Card.parse(str(card)) == card
    assert Card.parse("As") == Card(Rank.ACE, Suit.SPADES)
    assert Card.parse("td") == Card(10, "d")
    assert [str(c) for c in parse_cards("As Kd 7h 2c")] == ["As", "Kd", "7h", "2c"]


@pytest.mark.parametrize("text", ["", "A", "Asx", "1s", "Ax", "ZZ"])
def test_parse_rejects_invalid_text(text):
    with pytest.raises(ValueError):
        Card.parse(text)


def test_card_rejects_invalid_values():
    with pytest.raises(ValueError):
        Card(1, "s")
    with pytest.raises(ValueError):
        Card(15, "s")
    with pytest.raises(ValueError):
        Card(10, "x")


def test_full_deck_has_52_unique_cards():
    cards = full_deck()
    assert len(cards) == 52
    assert len(set(cards)) == 52


def test_shuffled_deck_deals_52_unique_cards():
    deck = Deck()
    assert len(deck) == 52
    dealt = deck.deal(5) + deck.deal(47)
    assert len(deck) == 0
    assert set(dealt) == set(full_deck())


def test_deal_more_than_remaining_fails():
    deck = Deck()
    deck.deal(50)
    with pytest.raises(ValueError):
        deck.deal(3)


def test_shuffles_are_different():
    assert Deck().deal(52) != Deck().deal(52)


def test_shuffle_uses_system_random(monkeypatch):
    assert isinstance(deck_module._SYSTEM_RNG, random.SystemRandom)

    calls = []

    class SpyRng(random.SystemRandom):
        def shuffle(self, cards):
            calls.append(len(cards))
            super().shuffle(cards)

    monkeypatch.setattr(deck_module, "_SYSTEM_RNG", SpyRng())
    Deck()
    assert calls == [52]


def test_fixed_deck_keeps_order_and_rejects_duplicates():
    cards = parse_cards("As Kd 7h 2c")
    assert Deck(cards).deal(4) == cards
    with pytest.raises(ValueError):
        Deck(parse_cards("As Kd As"))
