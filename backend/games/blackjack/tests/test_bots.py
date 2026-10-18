"""Bots del blackjack: la estrategia básica, lo que ven y el orden de los niveles."""

import random
import re
from pathlib import Path

import pytest

from core.cards import Card, parse_cards
from games.blackjack import bots
from games.blackjack.bots import LEVELS, basic_strategy, create_bot, strategy_code
from games.blackjack.bots.simulation import compare
from games.blackjack.engine import Action, BlackjackGame, Phase, Rules, table_view
from games.blackjack.tests.helpers import rigged

S17 = Rules()
H17 = Rules(dealer_hits_soft_17=True)
ALL = list(Action)


def code(cards, up, rules=S17, can_split=True):
    return strategy_code(parse_cards(cards), Card.parse(up), rules, can_split)


@pytest.mark.parametrize(
    ("cards", "up", "expected"),
    [
        ("Th 6d", "Tc", "Rh"),  # 16 contra 10: rendirse o pedir
        ("Th 6d", "6c", "S"),
        ("9h 3d", "4c", "S"),  # 12 contra 4: plantarse
        ("9h 3d", "2c", "H"),
        ("6h 5d", "Ac", "H"),  # 11 contra As: pedir (el crupier se planta con 17 blando)
        ("6h 5d", "Tc", "D"),
        ("5h 4d", "3c", "D"),  # 9 contra 3: doblar
        ("Ah 7d", "3c", "Ds"),  # 18 blando contra 3: doblar o plantarse
        ("Ah 7d", "9c", "H"),  # 18 blando contra 9: pedir
        ("Ah 7d", "2c", "S"),
        ("Ah 2d", "5c", "D"),
        ("8h 8d", "Tc", "P"),  # los ochos siempre se dividen
        ("Ah Ad", "Ac", "P"),
        ("Th Td", "6c", "S"),  # los dieces nunca
        ("5h 5d", "6c", "D"),  # 5-5 es un 10 duro
        ("9h 9d", "7c", "S"),
        ("9h 9d", "8c", "P"),
        ("4h 4d", "5c", "P"),
        ("Th 7d", "Ac", "S"),
        ("Th 8d", "Ac", "S"),
    ],
)
def test_basic_strategy_with_the_dealer_standing_on_soft_17(cards, up, expected):
    assert code(cards, up) == expected


@pytest.mark.parametrize(
    ("cards", "up", "expected"),
    [
        ("6h 5d", "Ac", "D"),  # con 17 blando del crupier, el 11 dobla también contra el As
        ("Th 5d", "Ac", "Rh"),
        ("Th 7d", "Ac", "Rs"),
        ("Ah 7d", "2c", "Ds"),
        ("Ah 8d", "6c", "Ds"),
        ("8h 8d", "Ac", "Rp"),
    ],
)
def test_basic_strategy_when_the_dealer_hits_soft_17(cards, up, expected):
    assert code(cards, up, H17) == expected


def test_codes_become_legal_actions():
    hard16 = parse_cards("Th 6d")
    ten = Card.parse("Tc")
    with_surrender = [Action.HIT, Action.STAND, Action.SURRENDER]
    assert basic_strategy(hard16, ten, S17, with_surrender) == Action.SURRENDER
    assert basic_strategy(hard16, ten, S17, [Action.HIT, Action.STAND]) == Action.HIT
    soft18 = parse_cards("Ah 7d")
    three = Card.parse("3c")
    assert basic_strategy(soft18, three, S17, ALL) == Action.DOUBLE
    assert basic_strategy(soft18, three, S17, [Action.HIT, Action.STAND]) == Action.STAND
    # Ochos que ya no se pueden dividir: un 16 duro.
    assert code("8h 8d", "Tc", can_split=False) == "Rh"


def test_bot_code_never_touches_the_shoe_or_the_game():
    """Los bots solo importan del motor tipos de datos y la vista, nunca el estado real."""
    forbidden = re.compile(r"\b(BlackjackGame|Shoe|Seat|PlayerHand|table_view)\b")
    folder = Path(bots.__file__).parent
    for path in folder.glob("*.py"):
        if path.name == "simulation.py":  # el simulador sí monta la mesa; no es un bot
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("from games.blackjack.engine"):
                assert not forbidden.search(line.split("import", 1)[1]), f"{path.name}: {line}"


def test_all_levels_share_the_same_interface():
    assert list(LEVELS) == ["easy", "medium", "hard", "expert"]
    game = rigged("Th 9d 6c 7s Kh")
    game.start_round({0: 100})
    view = table_view(game, 0)
    for level in LEVELS:
        bot = create_bot(level, "Brisa", random.Random(1))
        assert bot.level == level and bot.level_name and bot.name == "Brisa"
        assert Action(bot.decide(view)) in game.legal_actions(0)
    with pytest.raises(ValueError):
        create_bot("imposible", "X")


def test_a_bot_needs_its_turn():
    game = rigged("Th 5h 9d 6c 7h Ts", players=2)
    game.start_round({0: 100, 1: 100})
    with pytest.raises(ValueError):
        create_bot("hard", "X").decide(table_view(game, 1))


def test_bots_bet_a_fixed_amount_and_stop_without_chips():
    game = BlackjackGame(["Tú", "Brisa"], 1_000, Rules(min_bet=20, max_bet=200))
    bot = create_bot("hard", "Brisa", random.Random(3), units=3)
    view = table_view(game, 1)
    assert bot.bet(view) == 60 == bot.bet(view)  # siempre lo mismo
    game.seats[1].stack = 55
    assert bot.bet(table_view(game, 1)) == 50  # lo que le queda, de 10 en 10
    game.seats[1].stack = 15
    assert bot.bet(table_view(game, 1)) is None  # ya no llega a la mínima


def test_only_the_easy_bot_takes_insurance():
    game = rigged("9h Ad 9c 7s")
    game.start_round({0: 100})
    view = table_view(game, 0)
    assert view.insurance_offered
    for level in ("medium", "hard", "expert"):
        assert not create_bot(level, "X").insure(view)
    easy = create_bot("easy", "X", random.Random(2))
    assert any(easy.insure(view) for _ in range(20))


def test_bots_play_whole_rounds_at_a_shared_table():
    names = ["Tú", "Brisa", "Cobalto", "Lince", "Olivo"]
    game = BlackjackGame(names, 5_000, Rules(surrender=True))
    table = {
        seat: create_bot(level, names[seat], random.Random(seat))
        for seat, level in enumerate(LEVELS, start=1)
    }
    table[0] = create_bot("hard", "Tú", random.Random(0))
    total = game.total_chips()
    for _ in range(300):
        bets = {seat: bot.bet(table_view(game, seat)) for seat, bot in table.items()}
        bets = {seat: bet for seat, bet in bets.items() if bet}
        if not bets:
            break
        game.start_round(bets)
        while game.phase == Phase.INSURANCE:
            seat = next(s.seat for s in game.seats if s.insurance_pending)
            game.insure(seat, table[seat].insure(table_view(game, seat)))
        while game.phase == Phase.PLAYING:
            seat = game.to_act[0]
            game.act(seat, table[seat].decide(table_view(game, seat)))
        assert game.total_chips() == total


# --- Cada nivel juega mejor que el anterior (con las mismas rondas para los dos) ---


def test_medium_plays_much_better_than_easy():
    difference, margin = compare("medium", "easy", 3_000)
    assert difference > 2 * margin > 0


def test_hard_plays_better_than_medium():
    difference, margin = compare("hard", "medium", 30_000)
    assert difference > margin > 0


def test_expert_plays_at_least_as_well_as_hard():
    difference, margin = compare("expert", "hard", 10_000)
    assert difference > -margin
