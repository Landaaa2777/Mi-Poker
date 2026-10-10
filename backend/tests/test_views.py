"""Las vistas nunca revelan cartas ajenas ni el mazo antes del showdown."""

import json
import random
from dataclasses import fields

from conftest import ALL_IN, CALL, FOLD, make_game, random_action, raise_to, stacked_deck
from poker_engine import Game, GameConfig, TableView, full_deck, player_view, public_view

CARD_TEXTS = {str(card) for card in full_deck()}


def cards_in(value):
    """Todas las cartas que aparecen en cualquier parte de una vista ya convertida."""
    if isinstance(value, str):
        return {value} & CARD_TEXTS
    if isinstance(value, dict):
        return set().union(*(cards_in(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(cards_in(item) for item in value))
    return set()


def hidden_from(game, viewer_seat):
    """Cartas que el asiento no debe poder ver: manos ajenas no mostradas y mazo."""
    hand = game.hand
    shown = hand.result.shown_hands if hand.result is not None else {}
    hidden = {
        str(card)
        for player in game.players
        if player.seat != viewer_seat and player.seat not in shown
        for card in player.hole_cards
    }
    deck = hand._deck
    return hidden | {str(card) for card in deck._cards[deck._next :]}


def assert_no_leaks(game):
    for viewer in [None, *(p.seat for p in game.players)]:
        view = player_view(game, viewer).to_dict()
        json.dumps(view)  # debe ser serializable tal cual
        leaked = cards_in(view) & hidden_from(game, viewer)
        assert not leaked, f"El asiento {viewer} ve cartas ocultas: {leaked}"


def test_view_has_no_field_for_the_deck():
    assert not any("deck" in f.name for f in fields(TableView))


def test_no_hidden_cards_leak_during_random_games():
    rng = random.Random(7)
    game = Game(GameConfig(("Ana", "Beto", "Caro", "Dani", "Eva"), 500, 5, 10))
    for _ in range(150):
        if game.is_over:
            game.reset()
        hand = game.start_hand()
        assert_no_leaks(game)
        while not hand.is_complete:
            hand.act(hand.to_act.seat, random_action(hand.legal_actions(), rng))
            assert_no_leaks(game)


def test_player_sees_own_cards_and_public_view_sees_none():
    game = make_game([1000, 1000, 1000])
    game.start_hand()

    view = player_view(game, 1)
    assert view.hole_cards == tuple(game.players[1].hole_cards)
    assert [seat.hole_cards is not None for seat in view.seats] == [False, True, False]

    public = public_view(game)
    assert public.hole_cards == ()
    assert all(seat.hole_cards is None for seat in public.seats)
    assert cards_in(public.to_dict()) == set()


def test_legal_actions_only_for_the_player_to_act():
    game = make_game([1000, 1000, 1000])
    hand = game.start_hand()
    assert player_view(game, 0).legal_actions == hand.legal_actions()
    assert player_view(game, 1).legal_actions is None
    assert public_view(game).legal_actions is None
    assert player_view(game, 1).to_act_seat == 0


def test_public_state_of_the_table():
    game = make_game([1000, 1000, 1000])
    hand = game.start_hand()
    hand.act(0, raise_to(300))
    view = public_view(game)
    assert (view.phase, view.pot, view.current_bet, view.button_seat) == ("preflop", 450, 300, 0)
    assert [(s.stack, s.bet, s.status) for s in view.seats] == [
        (700, 300, "active"),
        (950, 50, "active"),
        (900, 100, "active"),
    ]
    assert [e.kind for e in view.events] == ["small_blind", "big_blind", "action"]


def test_showdown_reveals_only_the_hands_that_reached_it():
    game = make_game([1000, 1000, 1000])
    deck = stacked_deck({0: "As Ah", 1: "Ks Kh", 2: "Qc Td"}, "2c 7d 9h Jc 3s", button=0)
    hand = game.start_hand(deck)
    hand.act(0, ALL_IN)
    hand.act(1, CALL)
    hand.act(2, FOLD)

    view = player_view(game, 1).to_dict()
    assert view["seats"][0]["hole_cards"] == ["As", "Ah"]
    assert view["seats"][1]["hole_cards"] == ["Ks", "Kh"]
    assert view["seats"][2]["hole_cards"] is None  # se retiró: no se muestra
    assert [s["status"] for s in view["seats"]] == ["active", "out", "folded"]
    assert view["result"]["payouts"] == {"0": 2100}


def test_cards_stay_hidden_when_everyone_folds():
    game = make_game([1000, 1000, 1000])
    hand = game.start_hand()
    hand.act(0, FOLD)
    hand.act(1, FOLD)
    assert cards_in(public_view(game).to_dict()) == set()
    assert cards_in(player_view(game, 0).to_dict()) == {str(c) for c in game.players[0].hole_cards}


def test_view_before_the_first_hand():
    view = public_view(make_game([1000, 1000]))
    assert (view.phase, view.pot, view.board, view.to_act_seat) == (None, 0, (), None)
    assert [s.status for s in view.seats] == ["active", "active"]
