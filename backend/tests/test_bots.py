"""Los bots juegan solo con su vista, siempre de forma legal, y cada nivel a su estilo."""

import random
import re
from pathlib import Path

import pytest

import bots
from bots import LEVELS, PERSONALITIES, Spot, create_bot, pick_personalities
from bots.simulation import play_hand, run_match
from conftest import CALL, FOLD, make_game, raise_to, stacked_deck
from poker_engine import ActionType, Game, GameConfig, TableView, player_view
from test_views import cards_in, hidden_from

BOT_ACTIONS = {ActionType.FOLD, ActionType.CALL, ActionType.RAISE}


class Spy:
    """Envuelve a un bot y comprueba todo lo que recibe y devuelve."""

    def __init__(self, bot, game, seat):
        self.bot, self.game, self.seat = bot, game, seat
        self.decisions = 0

    def decide(self, view):
        assert isinstance(view, TableView)
        assert view.viewer_seat == self.seat
        # En la vista no hay ni una carta que el bot no deba conocer.
        assert not cards_in(view.to_dict()) & hidden_from(self.game, self.seat)
        action = self.bot.decide(view)
        assert action.type in BOT_ACTIONS
        self.decisions += 1
        return action

    def observe(self, view):
        self.bot.observe(view)


def mixed_table(seed, simulations=40):
    """Mesa de seis con todos los niveles y personalidades distintas."""
    rng = random.Random(seed)
    levels = [*LEVELS, "easy", "expert"]
    return [
        create_bot(level, personality, random.Random(rng.random()), simulations)
        for level, personality in zip(levels, pick_personalities(6, rng))
    ]


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_full_games_are_legal_leak_free_and_conserve_chips(seed):
    """Partidas largas con eliminaciones: el motor no rechaza ninguna jugada."""
    players = mixed_table(seed)
    game = Game(GameConfig(tuple(bot.name for bot in players), 600, 10, 20))
    spies = {seat: Spy(bot, game, seat) for seat, bot in enumerate(players)}
    total = game.total_chips

    for _ in range(400):
        if game.is_over:
            break
        play_hand(game, spies)
        assert game.total_chips == total
    assert sum(p.stack == 0 for p in game.players) >= 2  # hubo eliminados
    assert sum(spy.decisions for spy in spies.values()) > 100


@pytest.mark.parametrize("level", list(LEVELS))
@pytest.mark.parametrize("stacks", [[30, 2000], [2000, 15], [45, 45, 5000], [1, 1, 1, 9000]])
def test_bots_handle_short_and_deep_stacks(level, stacks):
    """Stacks mínimos y enormes: ciegas incompletas, all-ins y subidas limitadas."""
    rng = random.Random(len(stacks))
    for button in range(len(stacks)):
        game = make_game(stacks, button=button, sb=10, bb=20)
        table = {
            seat: create_bot(level, rng=random.Random(rng.random()), simulations=30)
            for seat in range(len(stacks))
        }
        play_hand(game, table)
        assert game.total_chips == sum(stacks)


def test_decide_rejects_a_view_without_the_turn():
    game = make_game([1000, 1000, 1000])
    game.start_hand()
    not_my_turn = next(p.seat for p in game.players if p.seat != game.hand.to_act.seat)
    with pytest.raises(ValueError):
        create_bot("easy").decide(player_view(game, not_my_turn))


def test_bot_code_never_touches_the_deck_or_the_engine_internals():
    """Los bots solo importan del motor tipos de datos y la vista, nunca el estado real."""
    forbidden = re.compile(r"\b(Deck|Game|GameConfig|Hand|Player|player_view|public_view)\b")
    folder = Path(bots.__file__).parent
    for path in folder.glob("*.py"):
        if path.name == "simulation.py":  # el simulador sí monta la mesa; no es un bot
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in (text for text in lines if text.startswith("from poker_engine")):
            assert not forbidden.search(line.split("import", 1)[1]), f"{path.name}: {line}"


def test_all_levels_share_the_same_interface():
    assert list(LEVELS) == ["easy", "medium", "hard", "expert"]
    for level, bot_class in LEVELS.items():
        bot = create_bot(level, PERSONALITIES[0])
        assert isinstance(bot, bot_class)
        assert bot.level == level and bot.level_name
        assert bot.name == PERSONALITIES[0].name
    assert create_bot("hard").simulations >= 2000
    assert create_bot("expert").simulations >= 2000
    with pytest.raises(ValueError):
        create_bot("imposible")


def test_personalities_have_unique_original_names():
    names = [p.name for p in PERSONALITIES]
    assert len(set(names)) == len(names) >= 5
    assert len({p.name for p in pick_personalities(5, random.Random(1))}) == 5
    for personality in PERSONALITIES:
        assert 0.8 <= personality.tightness <= 1.2
        assert 0.8 <= personality.aggression <= 1.2


# --- Estilo de cada nivel en situaciones concretas ---


def view_after(holes, board, button, actions):
    """Juega `actions` con un mazo preparado y devuelve la vista del jugador en turno."""
    game = make_game([1000] * len(holes), button=button, sb=5, bb=10)
    game.start_hand(stacked_deck(holes, board, button))
    for seat, action in actions:
        game.hand.act(seat, action)
    return player_view(game, game.hand.to_act.seat)


def decisions(level, view, tries=60):
    """Lo que decide el nivel en esa situación, con distintas semillas."""
    return [
        create_bot(level, rng=random.Random(seed), simulations=150).decide(view)
        for seed in range(tries)
    ]


def frequency(level, view, action_type):
    actions = decisions(level, view)
    return sum(action.type is action_type for action in actions) / len(actions)


def test_easy_plays_trash_that_better_bots_fold():
    # Cuatro jugadores; el asiento 2 habla primero con K-4 de distinto palo.
    holes = {0: "Ac Ad", 1: "Qc Qd", 2: "Kc 4d", 3: "8h 3s"}
    view = view_after(holes, "2s 7h Jc Td 5s", 3, [])
    assert view.viewer_seat == 2 and view.phase == "preflop"
    assert frequency("easy", view, ActionType.CALL) == 1.0
    for level in ("medium", "hard", "expert"):
        assert frequency(level, view, ActionType.FOLD) == 1.0


def test_everyone_raises_aces_but_easy_only_the_minimum():
    holes = {0: "9c 4d", 1: "Kc Kd", 2: "Ac Ad", 3: "8h 3s"}
    view = view_after(holes, "2s 7h Jc Qd 5s", 3, [])
    for level in ("medium", "hard", "expert"):
        assert frequency(level, view, ActionType.RAISE) == 1.0
    raises = [a for a in decisions("easy", view) if a.type is ActionType.RAISE]
    assert raises and all(a.amount == view.legal_actions.min_raise_to for a in raises)


def test_medium_respects_big_bets_and_easy_does_not():
    # Flop A-7-2: el asiento 0 tiene segunda pareja y le apuestan el bote entero.
    holes = {0: "8s 7d", 1: "Kc Kd"}
    actions = [(0, raise_to(30)), (1, CALL), (1, raise_to(60))]
    view = view_after(holes, "Ah 7c 2s Qd 5s", 0, actions)
    assert view.phase == "flop" and view.viewer_seat == 0
    assert frequency("easy", view, ActionType.CALL) == 1.0
    assert frequency("medium", view, ActionType.FOLD) == 1.0


def test_medium_calls_a_draw_only_with_the_right_pot_odds():
    # Proyecto de color en el flop: 9 outs, cerca de un 18% con una carta.
    holes = {0: "Ks Qs", 1: "Ac Ad"}
    board = "9s 4s 2d 3c 8h"
    cheap = view_after(holes, board, 0, [(0, raise_to(30)), (1, CALL), (1, raise_to(15))])
    expensive = view_after(holes, board, 0, [(0, raise_to(30)), (1, CALL), (1, raise_to(120))])
    assert frequency("medium", cheap, ActionType.CALL) == 1.0
    assert frequency("medium", expensive, ActionType.FOLD) == 1.0


@pytest.mark.parametrize("level", ["hard", "expert"])
def test_hard_and_expert_vary_their_bet_sizes(level):
    # Trío de sietes en el flop y el rival pasa: apuesta por valor, de tamaño variable.
    holes = {0: "7s 7d", 1: "Kc Qd"}
    view = view_after(holes, "Ah 7c 2s 3d 5s", 0, [(0, raise_to(30)), (1, CALL), (1, CALL)])
    assert view.viewer_seat == 0 and view.legal_actions.can_check
    actions = decisions(level, view)
    assert all(action.type is ActionType.RAISE for action in actions)
    assert len({action.amount for action in actions}) >= 5


@pytest.mark.parametrize("level", ["hard", "expert"])
def test_hard_and_expert_bluff_sometimes_but_not_always(level):
    # Subió preflop con 6-5 y el flop A-K-9 no le da nada.
    holes = {0: "6c 5d", 1: "7s 7d"}
    view = view_after(holes, "Ah Kc 9s 3d 2s", 0, [(0, raise_to(30)), (1, CALL), (1, CALL)])
    assert 0.1 < frequency(level, view, ActionType.RAISE) < 0.9


@pytest.mark.parametrize("level", ["hard", "expert"])
def test_position_changes_the_opening_range(level):
    """La misma mano se tira en primera posición y se sube desde el botón."""
    others = ["2c 2d", "3c 3d", "4c 4d", "5c 5d", "6c 6d"]
    board = "9s 7h Jc Kd Ts"

    early = dict(zip([0, 1, 2, 4, 5], others)) | {3: "As 2h"}
    early_view = view_after(early, board, 0, [])
    assert early_view.viewer_seat == 3 and Spot(early_view).seats_behind == 5
    assert frequency(level, early_view, ActionType.FOLD) == 1.0

    late = dict(zip([1, 2, 3, 4, 5], others)) | {0: "As 2h"}
    late_view = view_after(late, board, 0, [(3, FOLD), (4, FOLD), (5, FOLD)])
    assert late_view.viewer_seat == 0 and Spot(late_view).seats_behind == 2
    assert frequency(level, late_view, ActionType.RAISE) == 1.0


def test_expert_adapts_to_what_each_rival_does_in_public():
    expert = create_bot("expert", rng=random.Random(1), simulations=100)
    table = {0: expert, 1: create_bot("easy", rng=random.Random(2))}
    for number in range(200):
        game = make_game([1000, 1000], button=number % 2, sb=5, bb=10)
        play_hand(game, table)
    # El Fácil paga más y sube preflop mucho menos que el rival típico supuesto.
    assert expert._call_frequency("P1") > expert.TYPICAL_CALL + 0.05
    assert expert._open_frequency("P1") < expert.TYPICAL_OPEN / 2
    # De un rival que no ha visto nunca supone lo típico; de sí mismo no apunta nada.
    assert expert._call_frequency("Desconocido") == pytest.approx(expert.TYPICAL_CALL)
    assert "P0" not in expert._stats


def test_simulation_is_repeatable_and_zero_sum():
    first = run_match(list(LEVELS), 200, seed=11, simulations=40)
    second = run_match(list(LEVELS), 200, seed=11, simulations=40)
    assert [r.won for r in first] == [r.won for r in second]
    assert sum(r.won for r in first) == pytest.approx(0, abs=1e-6)
    assert all(r.hands == 200 and r.deals == 50 for r in first)
