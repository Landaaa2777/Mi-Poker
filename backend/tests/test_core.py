"""Piezas compartidas: barajado seguro, nombres de los bots y ficha de un juego."""

import random

import pytest

from core import shuffle
from core.bots import BOT_DELAY, BOT_NAMES, LEVEL_NAMES, pick_names
from core.registry import GameInfo


def test_shuffling_uses_the_system_generator(monkeypatch):
    assert isinstance(shuffle.SYSTEM_RNG, random.SystemRandom)
    calls = []

    class Spy(random.SystemRandom):
        def shuffle(self, items):
            calls.append(len(items))
            super().shuffle(items)

    monkeypatch.setattr(shuffle, "SYSTEM_RNG", Spy())
    cards = list(range(52))
    mixed = shuffle.shuffled(cards)
    assert calls == [52]
    assert sorted(mixed) == cards and cards == list(range(52))  # el original no se toca


def test_a_seeded_generator_repeats_the_same_order():
    """Solo para tests y simulaciones: con la misma semilla sale el mismo orden."""
    first = shuffle.shuffled(range(20), random.Random(7))
    assert first == shuffle.shuffled(range(20), random.Random(7))
    assert first != list(range(20))


def test_bots_think_between_0_8_and_2_5_seconds_in_every_game():
    assert BOT_DELAY == (0.8, 2.5)
    assert list(LEVEL_NAMES) == ["easy", "medium", "hard", "expert"]


def test_bot_names_never_repeat_nor_take_the_player_name():
    names = pick_names(5, taken=["brisa"], rng=random.Random(1))
    assert len(set(names)) == 5 and "Brisa" not in names
    assert set(names) <= set(BOT_NAMES)
    with pytest.raises(ValueError):
        pick_names(len(BOT_NAMES) + 1)


def test_a_game_without_create_is_coming_soon():
    soon = GameInfo("x", "X", "Pronto", min_bots=1, max_bots=3)
    assert not soon.available
    assert soon.players == (2, 4)
    assert GameInfo("y", "Y", "Ya", create=lambda context: None).available
