"""Una ronda de blackjack de principio a fin: jugadas, crupier, seguro y pagos."""

import random

import pytest

from games.blackjack.engine import (
    Action,
    BlackjackGame,
    HandStatus,
    IllegalActionError,
    Phase,
    Result,
    Rules,
    table_view,
)
from games.blackjack.tests.helpers import chips, random_round, rigged

HIT, STAND, DOUBLE, SPLIT, SURRENDER = (
    Action.HIT,
    Action.STAND,
    Action.DOUBLE,
    Action.SPLIT,
    Action.SURRENDER,
)


def me(game):
    return game.seats[0]


# --- Pagos de cada resultado ---


def test_a_natural_blackjack_pays_three_to_two():
    game = rigged("Ah 9d Kc 7s")  # yo: A K; crupier: 9 y 7 tapado
    game.start_round({0: 100})
    assert game.phase == Phase.COMPLETE  # con blackjack no queda nada que decidir
    hand = me(game).hands[0]
    assert hand.status == HandStatus.BLACKJACK and hand.result == Result.BLACKJACK
    assert hand.payout == 250 and me(game).stack == 1150


def test_winning_pays_even_money_and_a_tie_returns_the_bet():
    win = rigged("Th 9d Kc 8s")  # 20 contra 17
    win.start_round({0: 100})
    win.act(0, STAND)
    assert me(win).hands[0].result == Result.WIN and me(win).stack == 1100

    tie = rigged("Th 9d Kc Ts")  # 20 contra 19... el crupier tapa un 10: 19
    tie.start_round({0: 100})
    tie.act(0, STAND)
    assert me(tie).hands[0].result == Result.WIN

    push = rigged("Th 9d Kc As")  # 20 contra 20 (9 + As = 20)
    push.start_round({0: 100})
    push.act(0, STAND)
    assert me(push).hands[0].result == Result.PUSH and me(push).stack == 1000


def test_losing_and_busting_lose_the_bet():
    lose = rigged("Th 9d 7c Ts")  # 17 contra 19
    lose.start_round({0: 100})
    lose.act(0, STAND)
    assert me(lose).hands[0].result == Result.LOSE and me(lose).stack == 900

    bust = rigged("Th 6d 6c Ts Kh")  # 16, pido y me paso
    bust.start_round({0: 100})
    bust.act(0, HIT)
    assert me(bust).hands[0].status == HandStatus.BUST
    assert bust.phase == Phase.COMPLETE and me(bust).stack == 900
    assert bust.dealer == bust.dealer[:2]  # nadie a quien ganar: el crupier no pide


def test_the_dealer_busting_pays_every_standing_hand():
    game = rigged("Th 6d 8c Ts 9h", players=1)  # 18; crupier 6 + 10 = 16, pide 9
    game.start_round({0: 100})
    game.act(0, STAND)
    assert [str(card) for card in game.dealer] == ["6d", "Ts", "9h"]
    assert me(game).hands[0].result == Result.WIN


# --- El crupier ---


def test_the_dealer_stands_on_soft_17_by_default():
    game = rigged("Th 6d 9c As")  # crupier: 6 + As = 17 blando
    game.start_round({0: 100})
    game.act(0, STAND)
    assert len(game.dealer) == 2
    assert me(game).hands[0].result == Result.WIN  # 19 contra 17


def test_the_dealer_can_be_told_to_hit_soft_17():
    game = rigged("Th 6d 9c As 4h", dealer_hits_soft_17=True)  # 17 blando: pide y saca un 4
    game.start_round({0: 100})
    game.act(0, STAND)
    assert [str(card) for card in game.dealer] == ["6d", "As", "4h"]  # 21 blando: se planta
    assert me(game).hands[0].result == Result.LOSE  # mis 19 contra 21


def test_the_dealer_checks_for_blackjack_with_a_ten_showing():
    game = rigged("9h Kd 9c As", players=1)  # crupier K + As tapado: blackjack
    game.start_round({0: 100})
    assert game.phase == Phase.COMPLETE and game.to_act is None  # no se llega a jugar
    assert me(game).hands[0].result == Result.LOSE and me(game).stack == 900
    assert game.hole_revealed


def test_a_player_blackjack_ties_a_dealer_blackjack():
    game = rigged("Ah Kd Tc As")
    game.start_round({0: 100})
    assert me(game).hands[0].result == Result.PUSH and me(game).stack == 1000


def test_no_peek_without_an_ace_or_ten_showing():
    game = rigged("9h 7d 9c Ts")
    game.start_round({0: 100})
    assert game.phase == Phase.PLAYING
    assert not any(event.kind == "peek" for event in game.events)


# --- Seguro ---


def test_insurance_is_offered_when_the_dealer_shows_an_ace():
    game = rigged("9h Ad 9c 7s")
    game.start_round({0: 100})
    assert game.phase == Phase.INSURANCE and me(game).insurance_pending
    with pytest.raises(IllegalActionError):
        game.act(0, STAND)  # primero hay que decidir el seguro


def test_insurance_pays_two_to_one_when_the_dealer_has_blackjack():
    game = rigged("9h Ad 9c Ks")
    game.start_round({0: 100})
    game.insure(0, True)  # cuesta la mitad: 50
    assert game.phase == Phase.COMPLETE
    # Pierdo los 100 de la mano pero el seguro paga 50 × 3 = 150: quedo igual.
    assert me(game).stack == 1000


def test_insurance_is_lost_when_the_dealer_has_no_blackjack():
    game = rigged("Th Ad 9c 7s")
    game.start_round({0: 100})
    game.insure(0, True)
    assert game.phase == Phase.PLAYING and me(game).stack == 850
    game.act(0, STAND)  # 19 contra 18 (As + 7)
    assert me(game).hands[0].result == Result.WIN and me(game).stack == 1050


def test_declining_insurance_costs_nothing():
    game = rigged("Th Ad 9c 7s")
    game.start_round({0: 100})
    game.insure(0, False)
    assert me(game).stack == 900 and game.phase == Phase.PLAYING
    with pytest.raises(IllegalActionError):
        game.insure(0, True)  # ya decidido


# --- Doblar ---


def test_doubling_doubles_the_bet_and_takes_exactly_one_card():
    game = rigged("6h 9d 5c 7s Kh 2d")  # 11; doblo y recibo K: 21
    game.start_round({0: 100})
    game.act(0, DOUBLE)
    hand = me(game).hands[0]
    assert hand.doubled and hand.bet == 200 and len(hand.cards) == 3
    assert hand.status == HandStatus.STOOD and game.phase == Phase.COMPLETE
    assert hand.result == Result.WIN and me(game).stack == 1200


def test_doubling_needs_the_first_two_cards_and_enough_chips():
    game = rigged("2h 9d 3c 7s 2c 9h", stack=150)
    game.start_round({0: 100})  # me quedan 50: no llega para doblar 100
    assert DOUBLE not in game.legal_actions(0)
    with pytest.raises(IllegalActionError, match="fichas suficientes"):
        game.act(0, DOUBLE)
    game2 = rigged("2h 9d 3c 7s 2c 9h")
    game2.start_round({0: 100})
    game2.act(0, HIT)  # tres cartas
    with pytest.raises(IllegalActionError, match="dos primeras"):
        game2.act(0, DOUBLE)


# --- Dividir ---


def test_splitting_a_pair_makes_two_hands_with_their_own_bets():
    # Yo: 8 8; crupier 6, tapa 10. Al dividir: 8+3 (doblo y saco K: 21) y 8+9 (17).
    game = rigged("8h 6d 8c Ts 3h Kd 9c 2c")
    game.start_round({0: 100})
    game.act(0, SPLIT)
    first, second = me(game).hands
    assert first.bet == second.bet == 100 and me(game).stack == 800
    assert [str(card) for card in first.cards] == ["8h", "3h"]
    assert len(second.cards) == 1  # la segunda espera su carta hasta que le toque
    game.act(0, DOUBLE)  # se puede doblar tras dividir
    assert [str(card) for card in second.cards] == ["8c", "9c"]
    game.act(0, STAND)
    # El crupier tiene 16, pide un 2: 18. La mano doblada (21) gana y la otra (17) pierde.
    assert first.result == Result.WIN and first.payout == 400
    assert second.result == Result.LOSE
    assert me(game).stack == 1000 - 300 + 400


def test_split_aces_get_one_card_each_and_cannot_be_split_again():
    game = rigged("Ah 9d Ac 7s Kh Ad Qc")
    game.start_round({0: 100})
    game.act(0, SPLIT)
    hands = me(game).hands
    assert len(hands) == 2
    assert all(hand.status == HandStatus.STOOD for hand in hands)
    assert [len(hand.cards) for hand in hands] == [2, 2]
    # As + K después de dividir es 21, pero no blackjack: paga 1 a 1.
    assert hands[0].result == Result.WIN and hands[0].payout == 200
    assert game.phase == Phase.COMPLETE


def test_split_aces_receiving_another_ace_stay_as_they_are():
    game = rigged("Ah 9d Ac 7s Ad 5c Kc")
    game.start_round({0: 100})
    game.act(0, SPLIT)
    first = me(game).hands[0]
    assert [str(card) for card in first.cards] == ["Ah", "Ad"] and first.status == HandStatus.STOOD


def test_up_to_four_hands():
    game = rigged("8h 6d 8c Ts 8d 8s 8h 2c 3c 4c 5c Kd", stack=1000)
    game.start_round({0: 100})
    game.act(0, SPLIT)  # 2 manos: 8+8 y 8
    game.act(0, SPLIT)  # 3 manos
    game.act(0, SPLIT)  # 4 manos
    assert len(me(game).hands) == 4
    assert SPLIT not in game.legal_actions(0)
    with pytest.raises(IllegalActionError, match="4 manos"):
        game.act(0, SPLIT)


def test_only_pairs_can_be_split():
    game = rigged("8h 6d 9c Ts")
    game.start_round({0: 100})
    with pytest.raises(IllegalActionError, match="pareja"):
        game.act(0, SPLIT)
    tens = rigged("Kh 6d Qc Ts")  # K y Q valen lo mismo: se pueden dividir
    tens.start_round({0: 100})
    assert SPLIT in tens.legal_actions(0)


# --- Rendirse ---


def test_surrender_is_off_by_default():
    game = rigged("Th 9d 6c Ts")
    game.start_round({0: 100})
    assert SURRENDER not in game.legal_actions(0)
    with pytest.raises(IllegalActionError, match="rendirse"):
        game.act(0, SURRENDER)


def test_late_surrender_gives_back_half_the_bet():
    game = rigged("Th Td 6c 9s", surrender=True)  # 16 contra un 10
    game.start_round({0: 100})
    game.act(0, SURRENDER)
    hand = me(game).hands[0]
    assert hand.result == Result.SURRENDER and hand.payout == 50 and me(game).stack == 950


def test_surrender_only_with_the_first_two_cards():
    game = rigged("5h Td 6c 9s 2c", surrender=True)
    game.start_round({0: 100})
    game.act(0, HIT)
    assert SURRENDER not in game.legal_actions(0)


# --- Reglas de las apuestas y del turno ---


@pytest.mark.parametrize(
    ("bet", "problem"),
    [(5, "entre"), (510, "entre"), (25, "de 10 en 10"), (1100, "entre")],
)
def test_bets_must_follow_the_table_rules(bet, problem):
    game = rigged("Th 9d 6c Ts", stack=1000)
    with pytest.raises(IllegalActionError, match=problem):
        game.start_round({0: bet})
    assert me(game).stack == 1000 and game.round_number == 0


def test_cannot_bet_more_than_the_stack():
    game = rigged("Th 9d 6c Ts", stack=50)
    with pytest.raises(IllegalActionError, match="fichas suficientes"):
        game.start_round({0: 60})


def test_only_the_player_in_turn_can_act():
    game = rigged("Th 5h 9d 6c 7h Ts", players=2)
    game.start_round({0: 100, 1: 100})
    assert game.to_act == (0, 0)
    with pytest.raises(IllegalActionError, match="No es tu turno"):
        game.act(1, STAND)
    with pytest.raises(IllegalActionError, match="desconocida"):
        game.act(0, "trampa")


def test_reaching_21_stands_automatically():
    game = rigged("Th 5h 6c 9d 5c Ts")
    game.start_round({0: 100})
    game.act(0, HIT)  # 10 + 6 + 5 = 21
    assert me(game).hands[0].status == HandStatus.STOOD


def test_a_seat_without_a_bet_sits_the_round_out():
    game = rigged("Th 9d 6c Ts", players=2)
    game.start_round({0: 100})
    assert game.seats[1].hands == []


# --- Lo que se ve ---


def test_the_hole_card_is_never_shown_before_it_is_turned():
    game = rigged("Th 9d 6c 7s Kh")  # el crupier tapa el 7♠
    game.start_round({0: 100})
    view = table_view(game, 0).to_dict()
    assert view["dealer"]["cards"] == ["9d", None] and view["dealer"]["hole_hidden"]
    assert view["dealer"]["total"] == 9
    assert "7s" not in str(view)
    game.act(0, STAND)
    view = table_view(game, 0).to_dict()
    assert view["dealer"]["cards"][:2] == ["9d", "7s"] and not view["dealer"]["hole_hidden"]
    assert any(event["kind"] == "reveal" and event["card"] == "7s" for event in view["events"])


def test_legal_actions_are_only_sent_to_the_player_in_turn():
    game = rigged("Th 5h 9d 6c 7h Ts", players=2)
    game.start_round({0: 100, 1: 100})
    assert table_view(game, 0).legal_actions == ("hit", "stand", "double")
    assert table_view(game, 1).legal_actions is None


# --- El zapato entre rondas y las fichas ---


def test_after_the_cut_card_the_next_round_starts_with_a_new_shuffle():
    rules = Rules(decks=1, penetration=0.5)
    game = BlackjackGame(["Tú"], 10_000, rules)
    rng = random.Random(4)
    shuffles = game.shoe.shuffles
    while game.shoe.shuffles == shuffles:
        random_round(game, rng)
    assert game.events[0].kind == "shuffle"
    assert len(game.shoe) <= 52


@pytest.mark.parametrize("players", [1, 3, 5])
def test_chips_are_never_created_or_lost(players):
    rng = random.Random(players)
    game = BlackjackGame([f"J{i}" for i in range(players)], 2_000, Rules(surrender=True))
    total = chips(game)
    for _ in range(600):
        random_round(game, rng)
        assert chips(game) == total
        assert sum(seat.at_stake for seat in game.seats) == 0  # nada queda en la mesa
    assert game.house != 0


def test_a_small_shoe_never_runs_dry_nor_repeats_a_card_on_the_table():
    rules = Rules(decks=1, penetration=0.9)
    game = BlackjackGame([f"J{i}" for i in range(5)], 1_000_000, rules)
    rng = random.Random(9)
    for _ in range(400):
        random_round(game, rng)
        on_table = game._in_play()
        assert len(on_table) == len(set(on_table))  # una sola baraja: nada repetido
    assert game.round_number >= 390
