"""Manos completas. Blinds 50/100 y botón en el asiento 0 salvo que se indique."""

import pytest

from conftest import ALL_IN, CALL, CHECK, FOLD, make_game, raise_to, stacked_deck
from poker_engine import Game, GameConfig, GameStateError, HandCategory, Phase, parse_cards

BOARD = "2c 7d 9h Jc 3s"


def test_everyone_folds_to_the_big_blind():
    game = make_game([1000, 1000, 1000])
    hand = game.start_hand()
    hand.act(0, FOLD)
    hand.act(1, FOLD)

    assert hand.is_complete
    assert not hand.result.showdown
    assert hand.result.shown_hands == {}
    assert hand.result.payouts == {2: 100}
    assert hand.board == []
    assert [p.stack for p in game.players] == [1000, 950, 1050]


def test_uncalled_raise_wins_only_what_was_matched():
    game = make_game([1000, 1000, 1000])
    hand = game.start_hand()
    hand.act(0, raise_to(300))
    hand.act(1, FOLD)
    hand.act(2, FOLD)

    assert [(e.seat, e.amount) for e in hand.events if e.kind == "refund"] == [(0, 200)]
    assert hand.result.shown_hands == {}
    assert [p.stack for p in game.players] == [1150, 950, 900]


def test_showdown_after_betting_on_every_street():
    game = make_game([1000, 1000, 1000])
    deck = stacked_deck({0: "As Ah", 1: "Ks Kh", 2: "Qc Td"}, BOARD, button=0)
    hand = game.start_hand(deck)

    hand.act(0, raise_to(300))
    hand.act(1, CALL)
    hand.act(2, FOLD)
    assert hand.phase is Phase.FLOP
    assert hand.board == parse_cards("2c 7d 9h")
    assert hand.to_act.seat == 1  # primero a la izquierda del botón que sigue en la mano

    hand.act(1, CHECK)
    hand.act(0, raise_to(300))
    hand.act(1, CALL)
    assert hand.phase is Phase.TURN
    assert hand.pot == 1300
    hand.act(1, CHECK)
    hand.act(0, CHECK)
    assert hand.phase is Phase.RIVER
    hand.act(1, CHECK)
    hand.act(0, CHECK)

    result = hand.result
    assert hand.is_complete and result.showdown
    assert result.board == tuple(parse_cards(BOARD))
    assert result.payouts == {0: 1300}
    assert result.hand_values[0][0] is HandCategory.PAIR
    # Se muestran las manos que llegan al showdown; la del retirado, nunca.
    assert set(result.shown_hands) == {0, 1}
    assert result.shown_hands[0] == tuple(parse_cards("As Ah"))
    assert [p.stack for p in game.players] == [1700, 400, 900]


def test_split_pot_with_an_indivisible_chip():
    game = make_game([1000, 1000, 1000], sb=5, bb=10)
    deck = stacked_deck({0: "2c 3d", 1: "7c 8d", 2: "2h 3h"}, "As Ks Qd Jh Tc", button=0)
    hand = game.start_hand(deck)
    hand.act(0, CALL)
    hand.act(1, FOLD)
    hand.act(2, CHECK)
    for _ in range(3):
        hand.act(2, CHECK)
        hand.act(0, CHECK)

    # Bote de 25 entre dos escaleras iguales: la ficha suelta va al asiento 2,
    # el ganador más cercano a la izquierda del botón.
    assert hand.result.payouts == {2: 13, 0: 12}
    assert [p.stack for p in game.players] == [1002, 995, 1003]


def test_all_in_before_the_flop_deals_the_whole_board():
    game = make_game([1000, 1000], button=0)
    deck = stacked_deck({0: "As Ah", 1: "Ks Kh"}, BOARD, button=0)
    hand = game.start_hand(deck)
    hand.act(0, ALL_IN)
    hand.act(1, CALL)

    assert hand.is_complete and hand.result.showdown
    assert len(hand.board) == 5
    assert [e.action for e in hand.events if e.kind == "board"] == ["flop", "turn", "river"]
    assert [p.stack for p in game.players] == [2000, 0]


def test_button_and_blinds_rotate_every_hand():
    game = make_game([1000, 1000, 1000], button=0)
    positions = []
    for _ in range(4):
        hand = game.start_hand()
        positions.append((game.button_seat, hand.small_blind_seat, hand.big_blind_seat))
        while not hand.is_complete:
            hand.act(hand.to_act.seat, FOLD)
    assert positions == [(0, 1, 2), (1, 2, 0), (2, 0, 1), (0, 1, 2)]


def test_button_skips_eliminated_players():
    game = make_game([1000, 1000, 1000, 1000], button=0)
    hand = game.start_hand()
    while not hand.is_complete:
        hand.act(hand.to_act.seat, FOLD)

    game.players[1].stack = 0  # como si hubiera quedado eliminado
    hand = game.start_hand()
    assert game.button_seat == 2
    assert (hand.small_blind_seat, hand.big_blind_seat) == (3, 0)
    assert [p.seat for p in hand.order] == [3, 0, 2]
    assert not game.players[1].in_hand
    assert game.players[1].hole_cards == []


def test_eliminated_player_ends_the_game_and_reset_restarts_it():
    game = make_game([1000, 1000], button=0)
    deck = stacked_deck({0: "As Ah", 1: "Ks Kh"}, BOARD, button=0)
    hand = game.start_hand(deck)
    hand.act(0, ALL_IN)
    hand.act(1, CALL)

    assert game.is_over
    assert game.winner.seat == 0
    with pytest.raises(GameStateError):
        game.start_hand()

    game.reset()
    assert not game.is_over
    assert game.hand_number == 0
    assert [p.stack for p in game.players] == [1000, 1000]
    game.start_hand()
    assert game.hand_number == 1


def test_cannot_start_a_hand_while_another_is_in_progress():
    game = make_game([1000, 1000, 1000])
    game.start_hand()
    with pytest.raises(GameStateError):
        game.start_hand()


@pytest.mark.parametrize(
    "names, stack, sb, bb",
    [
        (("solo",), 1000, 5, 10),
        (tuple("abcdefg"), 1000, 5, 10),
        (("a", "b"), 0, 5, 10),
        (("a", "b"), 1000, 0, 10),
        (("a", "b"), 1000, 20, 10),
        (("a", "b"), 5, 5, 10),
        (("a", "b"), 1000.5, 5, 10),
    ],
)
def test_invalid_configuration_is_rejected(names, stack, sb, bb):
    with pytest.raises(ValueError):
        GameConfig(names, stack, sb, bb)


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6])
def test_table_sizes_from_two_to_six(count):
    game = Game(GameConfig(tuple(f"P{i}" for i in range(count)), 1000, 5, 10))
    hand = game.start_hand()
    assert len(hand.order) == count
    assert all(len(p.hole_cards) == 2 for p in game.players)
    assert game.total_chips == 1000 * count
