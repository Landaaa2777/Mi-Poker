from games.poker.tests.helpers import ALL_IN, CALL, FOLD, make_game, raise_to, stacked_deck
from games.poker.engine import Pot, award_pots, build_pots, evaluate, parse_cards

BOARD = "2c 7d 9h Jc 3s"


def value(hole):
    return evaluate(parse_cards(f"{hole} {BOARD}"))


def test_single_pot_without_all_ins():
    assert build_pots({0: 200, 1: 200, 2: 200}, folded=set()) == [Pot(600, (0, 1, 2))]


def test_side_pots_with_three_different_all_ins():
    contributions = {0: 100, 1: 250, 2: 600, 3: 600}
    pots = build_pots(contributions, folded=set())
    assert pots == [
        Pot(400, (0, 1, 2, 3)),  # 100 de cada uno
        Pot(450, (1, 2, 3)),  # 150 más de tres jugadores
        Pot(700, (2, 3)),  # 350 más de dos jugadores
    ]
    assert sum(p.amount for p in pots) == sum(contributions.values())


def test_folded_chips_stay_in_the_pot_but_cannot_win_it():
    # El asiento 3 puso 250 y se retiró; sus fichas se reparten entre los botes.
    pots = build_pots({0: 100, 1: 400, 2: 400, 3: 250}, folded={3})
    assert pots == [Pot(400, (0, 1, 2)), Pot(750, (1, 2))]


def test_each_pot_goes_to_its_best_eligible_hand():
    pots = build_pots({0: 100, 1: 250, 2: 600, 3: 600}, folded=set())
    values = {0: value("As Ah"), 1: value("Ks Kh"), 2: value("Qs Qh"), 3: value("8s 8h")}
    awards = award_pots(pots, values, odd_chip_order=[1, 2, 3, 0])
    assert [a.payouts for a in awards] == [{0: 400}, {1: 450}, {2: 700}]


def test_best_hand_overall_takes_every_pot_it_is_eligible_for():
    pots = build_pots({0: 100, 1: 250, 2: 600, 3: 600}, folded=set())
    values = {0: value("8s 8h"), 1: value("Qs Qh"), 2: value("Ks Kh"), 3: value("As Ah")}
    awards = award_pots(pots, values, odd_chip_order=[1, 2, 3, 0])
    assert [a.payouts for a in awards] == [{3: 400}, {3: 450}, {3: 700}]


def test_split_pot_gives_odd_chip_to_first_winner_left_of_the_button():
    values = {0: value("As Kd"), 1: value("Ah Kc"), 2: value("4s 5h")}
    # Botón en el asiento 0: el primero a su izquierda es el 1.
    awards = award_pots([Pot(25, (0, 1, 2))], values, odd_chip_order=[1, 2, 0])
    assert awards[0].winners == (1, 0)
    assert awards[0].payouts == {1: 13, 0: 12}
    # Botón en el asiento 1: ahora el más cercano entre los ganadores es el 0.
    awards = award_pots([Pot(25, (0, 1, 2))], values, odd_chip_order=[2, 0, 1])
    assert awards[0].payouts == {0: 13, 1: 12}


def test_three_way_split_with_two_odd_chips():
    values = {0: value("As Kd"), 1: value("Ah Kc"), 2: value("Ad Kh")}
    awards = award_pots([Pot(101, (0, 1, 2))], values, odd_chip_order=[1, 2, 0])
    assert awards[0].payouts == {1: 34, 2: 34, 0: 33}


def test_full_hand_with_three_all_ins_of_different_sizes():
    # Botón 0, ciegas 1 y 2: hablan 3, 0, 1, 2. La mejor mano es la del stack más corto.
    game = make_game([250, 600, 1000, 100], button=0, sb=5, bb=10)
    deck = stacked_deck({3: "As Ah", 0: "Ks Kh", 1: "Qs Qh", 2: "8s 8h"}, BOARD, button=0)
    hand = game.start_hand(deck)
    hand.act(3, ALL_IN)
    hand.act(0, ALL_IN)
    hand.act(1, ALL_IN)
    hand.act(2, CALL)

    assert hand.is_complete
    assert [(a.amount, a.eligible, a.winners) for a in hand.result.awards] == [
        (400, (0, 1, 2, 3), (3,)),
        (450, (0, 1, 2), (0,)),
        (700, (1, 2), (1,)),
    ]
    assert [p.stack for p in game.players] == [450, 700, 400, 400]
    assert game.total_chips == 1950


def test_uncalled_part_of_an_all_in_is_returned():
    game = make_game([500, 200], button=0)
    deck = stacked_deck({0: "8s 8h", 1: "As Ah"}, BOARD, button=0)
    hand = game.start_hand(deck)
    hand.act(0, ALL_IN)
    hand.act(1, CALL)

    refunds = [(e.seat, e.amount) for e in hand.events if e.kind == "refund"]
    assert refunds == [(0, 300)]
    assert [(a.amount, a.winners) for a in hand.result.awards] == [(400, (1,))]
    assert [p.stack for p in game.players] == [300, 400]


def test_short_blind_creates_a_side_pot():
    game = make_game([1000, 1000, 60], button=0)
    deck = stacked_deck({0: "Ks Kh", 1: "Qs Qh", 2: "As Ah"}, BOARD, button=0)
    hand = game.start_hand(deck)
    hand.act(0, CALL)
    hand.act(1, CALL)
    for _ in range(3):  # flop, turn y river sin apuestas
        hand.act(1, CALL)
        hand.act(0, CALL)

    assert [(a.amount, a.winners) for a in hand.result.awards] == [(180, (2,)), (80, (0,))]
    assert [p.stack for p in game.players] == [980, 900, 180]


def test_dead_money_from_a_folded_player_goes_to_the_winner():
    game = make_game([1000, 1000, 1000], button=0)
    deck = stacked_deck({0: "As Ah", 1: "7c 2d", 2: "Ks Kh"}, "3c 8d 9h Jc 4s", button=0)
    hand = game.start_hand(deck)
    hand.act(0, raise_to(300))
    hand.act(1, CALL)
    hand.act(2, CALL)
    hand.act(1, raise_to(200))  # flop: apuesta y luego se retira ante la subida
    hand.act(2, CALL)
    hand.act(0, raise_to(700))
    hand.act(1, FOLD)
    hand.act(2, CALL)

    assert hand.is_complete
    assert [(a.amount, a.eligible) for a in hand.result.awards] == [(2500, (0, 2))]
    assert [p.stack for p in game.players] == [2500, 500, 0]
