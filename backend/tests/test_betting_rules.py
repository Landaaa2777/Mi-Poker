"""Reglas de apuestas. Blinds 50/100 y botón en el asiento 0 salvo que se indique."""

import pytest

from conftest import ALL_IN, CALL, CHECK, FOLD, make_game, raise_to
from poker_engine import Action, ActionType, IllegalActionError, Phase


def start(stacks, button=0):
    game = make_game(stacks, button=button)
    return game, game.start_hand()


def test_blinds_and_first_to_act_three_handed():
    game, hand = start([1000, 1000, 1000])
    assert (hand.small_blind_seat, hand.big_blind_seat) == (1, 2)
    assert [p.bet for p in game.players] == [0, 50, 100]
    assert hand.to_act.seat == 0
    legal = hand.legal_actions()
    assert (legal.can_check, legal.call_amount) == (False, 100)
    assert (legal.can_raise, legal.min_raise_to, legal.max_raise_to) == (True, 200, 1000)


def test_minimum_raise_follows_last_full_raise():
    game, hand = start([5000, 5000, 5000])
    with pytest.raises(IllegalActionError):
        hand.act(0, raise_to(150))  # menos que el doble de la ciega grande
    hand.act(0, raise_to(200))

    legal = hand.legal_actions()
    assert (hand.to_act.seat, legal.call_amount, legal.min_raise_to) == (1, 150, 300)
    hand.act(1, raise_to(500))  # incremento de 300

    legal = hand.legal_actions()
    assert (hand.to_act.seat, legal.call_amount, legal.min_raise_to) == (2, 400, 800)
    with pytest.raises(IllegalActionError):
        hand.act(2, raise_to(799))
    hand.act(2, raise_to(800))


def test_minimum_bet_after_the_flop_is_the_big_blind():
    game, hand = start([1000, 1000, 1000])
    hand.act(0, CALL)
    hand.act(1, CALL)
    hand.act(2, CHECK)
    assert hand.phase is Phase.FLOP
    assert hand.to_act.seat == 1
    legal = hand.legal_actions()
    assert (legal.can_check, legal.call_amount, legal.min_raise_to) == (True, 0, 100)
    with pytest.raises(IllegalActionError):
        hand.act(1, raise_to(99))
    hand.act(1, raise_to(100))


def test_illegal_actions_are_rejected_without_changing_state():
    game, hand = start([1000, 1000, 1000])
    illegal = [
        (0, CHECK),  # hay una apuesta por igualar
        (1, CALL),  # no es su turno
        (0, raise_to(1001)),  # más fichas de las que tiene
        (0, raise_to(-50)),
        (0, raise_to(0)),
        (0, Action(ActionType.RAISE, 250.5)),
        (0, Action(ActionType.RAISE, True)),
        (0, Action("bet", 300)),
    ]
    for seat, action in illegal:
        with pytest.raises(IllegalActionError):
            hand.act(seat, action)
    assert [p.stack for p in game.players] == [1000, 950, 900]
    assert hand.to_act.seat == 0
    assert hand.events[-1].kind == "big_blind"
    assert game.total_chips == 3000


def test_no_action_after_the_hand_is_over():
    game, hand = start([1000, 1000, 1000])
    hand.act(0, FOLD)
    hand.act(1, FOLD)
    assert hand.is_complete
    with pytest.raises(IllegalActionError):
        hand.act(2, CHECK)
    with pytest.raises(IllegalActionError):
        hand.legal_actions()


def test_big_blind_has_the_option_to_raise():
    game, hand = start([1000, 1000, 1000])
    hand.act(0, CALL)
    hand.act(1, CALL)
    legal = hand.legal_actions()
    assert hand.to_act.seat == 2
    assert (legal.can_check, legal.can_raise, legal.min_raise_to) == (True, True, 200)

    hand.act(2, raise_to(300))
    assert hand.phase is Phase.PREFLOP
    assert hand.to_act.seat == 0
    assert hand.legal_actions().call_amount == 200


def test_heads_up_button_posts_small_blind_and_acts_first():
    game, hand = start([1000, 1000], button=0)
    assert (hand.small_blind_seat, hand.big_blind_seat) == (0, 1)
    assert hand.to_act.seat == 0
    hand.act(0, CALL)
    assert hand.to_act.seat == 1  # opción de la ciega grande
    hand.act(1, CHECK)
    assert hand.phase is Phase.FLOP
    assert hand.to_act.seat == 1  # después del flop habla primero la ciega grande


def test_call_and_all_in_are_normalized():
    game, hand = start([1000, 1000, 1000])
    hand.act(0, CALL)
    hand.act(1, CALL)
    assert hand.act(2, CALL) == CHECK  # igualar sin nada que igualar es pasar
    assert hand.act(1, ALL_IN) == raise_to(900)
    assert game.players[1].all_in


def test_call_for_less_puts_the_player_all_in():
    game, hand = start([1000, 1000, 300])
    hand.act(0, raise_to(800))
    hand.act(1, FOLD)
    legal = hand.legal_actions()
    assert (legal.call_amount, legal.can_raise) == (200, False)
    assert hand.act(2, ALL_IN) == Action(ActionType.CALL, 200)
    assert hand.is_complete  # nadie más puede apostar: se reparte hasta el final
    assert game.total_chips == 2300


def test_short_all_in_does_not_reopen_betting():
    game, hand = start([1000, 1000, 250])
    hand.act(0, CALL)
    hand.act(1, CALL)
    hand.act(2, CHECK)

    hand.act(1, raise_to(100))
    legal = hand.legal_actions()  # asiento 2: le quedan 150
    assert (legal.min_raise_to, legal.max_raise_to) == (150, 150)
    hand.act(2, ALL_IN)  # sube solo 50: raise incompleto

    # El asiento 0 aún no había actuado: puede subir, y el mínimo sigue siendo +100.
    legal = hand.legal_actions()
    assert (hand.to_act.seat, legal.call_amount) == (0, 150)
    assert (legal.can_raise, legal.min_raise_to) == (True, 250)
    hand.act(0, CALL)

    # El asiento 1 ya había actuado y solo afronta 50 más: igualar o retirarse.
    legal = hand.legal_actions()
    assert (hand.to_act.seat, legal.call_amount, legal.can_raise) == (1, 50, False)
    with pytest.raises(IllegalActionError):
        hand.act(1, raise_to(400))
    with pytest.raises(IllegalActionError):
        hand.act(1, ALL_IN)
    hand.act(1, CALL)
    assert hand.phase is Phase.TURN


def test_several_short_all_ins_adding_up_to_a_full_raise_reopen_betting():
    game, hand = start([310, 1000, 250, 1000])
    for seat, action in [(3, CALL), (0, CALL), (1, CALL), (2, CHECK)]:
        hand.act(seat, action)

    hand.act(1, raise_to(100))
    hand.act(2, ALL_IN)  # a 150 (+50)
    hand.act(3, CALL)
    assert hand.act(0, ALL_IN) == raise_to(210)  # +60: entre los dos suman 110

    # Asiento 1: actuó con la apuesta en 100 y ahora está en 210 -> se reabre.
    legal = hand.legal_actions()
    assert (hand.to_act.seat, legal.call_amount) == (1, 110)
    assert (legal.can_raise, legal.min_raise_to) == (True, 310)
    hand.act(1, CALL)

    # Asiento 3: actuó con la apuesta en 150 y solo subió 60 -> no se reabre.
    legal = hand.legal_actions()
    assert (hand.to_act.seat, legal.call_amount, legal.can_raise) == (3, 60, False)


def test_short_big_blind_does_not_lower_the_amount_to_call():
    game, hand = start([1000, 1000, 60])
    assert game.players[2].all_in
    assert hand.legal_actions().call_amount == 100
    hand.act(0, CALL)
    assert hand.legal_actions().call_amount == 50
    hand.act(1, CALL)
    assert hand.phase is Phase.FLOP
    assert hand.pot == 260


def test_heads_up_against_short_big_blind_only_needs_to_cover_it():
    game, hand = start([1000, 60], button=0)
    legal = hand.legal_actions()
    assert (hand.to_act.seat, legal.call_amount, legal.can_raise) == (0, 10, False)
    hand.act(0, CALL)
    assert hand.is_complete
    assert game.total_chips == 1060


def test_blind_smaller_than_the_other_blind_ends_the_betting_at_once():
    game, hand = start([1000, 30], button=0)
    # La ciega grande solo tiene 30: las 20 que sobran de la pequeña se devuelven.
    assert hand.is_complete
    assert hand.result.showdown
    assert sum(hand.result.payouts.values()) == 60
    assert game.total_chips == 1030
