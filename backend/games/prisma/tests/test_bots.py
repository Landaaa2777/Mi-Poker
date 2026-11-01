"""Bots de Prisma: lo que ven, cómo juega cada nivel y el orden de los niveles."""

import random
import re
from pathlib import Path

import pytest

from games.prisma import bots
from games.prisma.bots import LEVELS, Move, create_bot, missing_colors
from games.prisma.bots.simulation import apply, play_game, run_tournament
from games.prisma.engine import Color, Kind, Phase, PrismaGame, table_view
from games.prisma.tests.helpers import rigged


def test_bot_code_never_touches_the_game_itself():
    """Los bots solo importan del motor tipos de datos y la vista, nunca la partida real."""
    forbidden = re.compile(r"\b(PrismaGame|Player|table_view|full_deck)\b")
    folder = Path(bots.__file__).parent
    for path in folder.glob("*.py"):
        if path.name == "simulation.py":  # el simulador sí monta la mesa; no es un bot
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("from games.prisma.engine"):
                assert not forbidden.search(line.split("import", 1)[1]), f"{path.name}: {line}"


def test_a_bot_only_sees_its_own_hand():
    game = rigged(["panal-1 panal-2", "halo-1 halo-2", "astro-1 astro-2"], "panal-7")
    view = table_view(game, 1)
    assert [card.code for card in view.hand] == ["halo-1", "halo-2"]
    assert [player.count for player in view.players] == [2, 2, 2]
    dealt = [event for event in view.events if event["kind"] == "deal"]
    assert all(event["cards"] == [] for event in dealt if event["seat"] != 1)
    assert "panal-1" not in str([event["cards"] for event in view.events])


def test_all_levels_share_the_same_interface():
    assert list(LEVELS) == ["easy", "medium", "hard", "expert"]
    game = rigged(["panal-1 halo-2 camaleon", "halo-1 halo-3 halo-4"], "panal-7")
    view = table_view(game, 0)
    for level in LEVELS:
        bot = create_bot(level, "Brisa", random.Random(1))
        assert bot.level == level and bot.level_name and bot.name == "Brisa"
        move = bot.decide(view)
        assert move.kind in ("play", "draw")
        if move.kind == "play":
            assert move.card in view.legal.play
    with pytest.raises(ValueError):
        create_bot("imposible", "X")
    with pytest.raises(ValueError):
        create_bot("hard", "X").decide(table_view(game, 1))  # no es su turno


def test_bots_choose_a_color_and_answer_a_challenge():
    start = rigged(["panal-1 panal-2", "halo-1 halo-2"], "camaleon")
    move = create_bot("medium", "X").decide(table_view(start, 0))
    assert move == Move("choose_color", color=Color.PANAL)  # el color que más tiene
    wild4 = rigged(["camaleon4 halo-1 halo-2", "astro-1 astro-2 astro-3"], "panal-7")
    wild4.play(0, next(card.id for card in wild4.players[0].hand if card.kind == Kind.CAMALEON4), Color.HALO)
    for level in LEVELS:
        assert create_bot(level, "X", random.Random(3)).decide(table_view(wild4, 1)).kind in ("challenge", "accept")


def test_medium_sheds_wilds_first_but_hard_keeps_them():
    game = rigged(["camaleon panal-3 halo-1 astro-5", "halo-2 halo-3 halo-4 halo-5"], "panal-7")
    view = table_view(game, 0)
    assert view.card(create_bot("medium", "X").decide(view).card).kind == Kind.CAMALEON
    assert view.card(create_bot("hard", "X").decide(view).card).code == "panal-3"
    assert view.card(create_bot("expert", "X").decide(view).card).code == "panal-3"


def test_hard_and_expert_never_bluff_a_draw_four():
    game = rigged(["camaleon4 panal-3 halo-1", "astro-2 astro-3 astro-4"], "panal-7")
    view = table_view(game, 0)
    for level in ("hard", "expert"):
        for seed in range(20):
            move = create_bot(level, "X", random.Random(seed)).decide(view)
            assert view.card(move.card).kind != Kind.CAMALEON4


def test_expert_stops_the_player_about_to_win():
    # El siguiente (jugador 1) tiene una sola carta: el Experto suelta la Carga +2.
    game = rigged(["panal-carga panal-3 panal-5", "halo-1 halo-2 halo-3"], "panal-7")
    rival = game.players[1]
    game.draw_pile += rival.hand[1:]  # sus otras cartas vuelven al mazo
    rival.hand = rival.hand[:1]
    assert game.total_cards() == 108
    view = table_view(game, 0)
    assert view.card(create_bot("expert", "X").decide(view).card).kind == Kind.CARGA


def test_hard_remembers_who_lacks_a_color():
    game = rigged(["panal-1 panal-2 panal-4", "halo-1 halo-2 halo-3", "astro-1 astro-2 astro-3"], "panal-7", rest="cumbre-9")
    game.play(0, next(card.id for card in game.players[0].hand if card.code == "panal-1"))
    game.draw(1)  # no tiene panal: roba (y no le sirve)
    view = table_view(game, 2)
    assert Color.PANAL in missing_colors(view)[1]
    assert missing_colors(view)[0] == set()


def test_easy_often_forgets_to_say_last_and_expert_never():
    game = rigged(["panal-1 panal-2", "halo-1 halo-2"], "panal-7")
    view = table_view(game, 0)

    def declares(level):
        bot = create_bot(level, "X", random.Random(5))
        return sum(bot.decide(view).declare for _ in range(400)) / 400

    assert declares("easy") < 0.6
    assert declares("medium") > 0.85
    assert declares("expert") == 1.0


def test_a_whole_game_between_bots_keeps_all_108_cards():
    for seed in range(30):
        game = PrismaGame(["a", "b", "c", "d"], rng=random.Random(seed))
        table = [create_bot(level, name, random.Random(seed + i)) for i, (level, name) in enumerate(zip(LEVELS, "abcd"))]
        game.start_round()
        for _ in range(3000):
            if game.phase == Phase.ROUND_OVER:
                break
            apply(game, game.turn, table[game.turn])
            assert game.total_cards() == 108
        assert game.phase == Phase.ROUND_OVER


def test_each_level_wins_more_than_the_one_below():
    """Miles de partidas a cuatro (un bot de cada nivel), rotando los asientos."""
    results = run_tournament(list(LEVELS), 2000, seed=2026)
    rates = [results[level].win_rate for level in LEVELS]
    assert sum(result.wins for result in results.values()) == 2000  # todas acaban
    for weaker, stronger in zip(LEVELS, list(LEVELS)[1:]):
        gap = results[stronger].win_rate - results[weaker].win_rate
        margin = results[stronger].margin + results[weaker].margin
        assert gap > margin / 2 > 0, (weaker, stronger, rates)


def test_a_duel_also_finishes():
    assert play_game(["expert", "easy"], seed=3) in (0, 1)


# --- Los modos nuevos ---

from games.prisma.engine import DARK_COLORS, Mode, PrismaRules  # noqa: E402
from games.prisma.tests.helpers import card_id, rigged_double  # noqa: E402


def relentless(hands, first, rest=""):
    return rigged(hands, first, rest, mode=Mode.SIN_TREGUA)


def test_bots_answer_the_roulette_with_a_colour_in_play():
    game = relentless(["ruleta panal-1", "halo-1 halo-2", "cumbre-1 cumbre-2"], "panal-5")
    game.play(0, card_id(game, 0, "ruleta"))
    view = table_view(game, 1)
    for level in LEVELS:
        move = create_bot(level, "X", random.Random(2)).decide(view)
        assert move.kind == "roulette" and move.color.value in view.colors


def test_the_roulette_is_played_without_a_colour_and_the_seven_with_a_target():
    game = relentless(["ruleta panal-7 halo-3", "halo-1 halo-2 halo-4", "cumbre-1 cumbre-2 cumbre-3"], "panal-5")
    rival = game.players[2]
    game.draw_pile += rival.hand[1:]  # el 2 se queda con una sola carta; las demás, al mazo
    rival.hand = rival.hand[:1]
    assert game.total_cards() == 168
    view = table_view(game, 0)
    for level in LEVELS:
        for seed in range(10):
            move = create_bot(level, "X", random.Random(seed)).decide(view)
            card = view.card(move.card)
            if card.kind == Kind.RULETA:
                assert move.color is None
            if card.number == 7:
                assert move.target in (1, 2)
    hard = create_bot("hard", "X", random.Random(1))
    assert hard.pick_target(view) == 2  # con quien menos cartas tiene


def test_hard_stacks_with_the_smallest_card_and_expert_finishes_off_the_leader():
    game = relentless(["panal-carga halo-1 halo-2", "camaleon10 panal-carga4 halo-3", "cumbre-1 cumbre-2 cumbre-3"], "panal-5")
    game.play(0, card_id(game, 0, "panal-carga"))
    view = table_view(game, 1)
    assert view.card(create_bot("hard", "X").decide(view).card).kind == Kind.CARGA4
    # El siguiente (el 2) está a punto de ganar: el Experto pone el +10 para que no pueda devolverlo.
    rival = game.players[2]
    game.draw_pile += rival.hand[1:]
    rival.hand = rival.hand[:1]
    assert game.total_cards() == 168
    view = table_view(game, 1)
    assert view.card(create_bot("expert", "X").decide(view).card).kind == Kind.CAMALEON10


def test_hard_likes_a_big_sweep():
    game = relentless(["panal-barrido panal-2 panal-3 panal-8 halo-5", "cumbre-1 cumbre-2 cumbre-3 cumbre-4 cumbre-6"], "panal-5")
    view = table_view(game, 0)
    assert view.card(create_bot("hard", "X").decide(view).card).kind == Kind.BARRIDO


def test_on_the_dark_side_bots_pick_dark_colours():
    game = rigged_double(["panal-eclipse panal-2 panal-3", "halo-3 halo-4 halo-5"], "panal-5/camaleon")
    game.play(0, card_id(game, 0, "panal-eclipse"))
    view = table_view(game, 0)  # el Eclipse dejó un comodín arriba: elige quien lo jugó
    for level in LEVELS:
        move = create_bot(level, "X", random.Random(4)).decide(view)
        assert move.kind == "choose_color" and move.color in DARK_COLORS


def test_hard_never_bluffs_a_hound():
    game = rigged_double(["panal-eclipse panal-2/sabueso panal-3/brasa-1", "halo-3 halo-4 halo-5"], "panal-5/brasa-9")
    game.play(0, card_id(game, 0, "panal-eclipse"))
    game.turn = 0
    view = table_view(game, 0)
    for seed in range(10):
        move = create_bot("hard", "X", random.Random(seed)).decide(view)
        assert view.card(move.card).kind != Kind.SABUESO


@pytest.mark.parametrize("mode", [Mode.DOBLE, Mode.SIN_TREGUA])
def test_whole_games_between_bots_keep_every_card(mode):
    rules = PrismaRules(mode=mode)
    for seed in range(15):
        game = PrismaGame(["a", "b", "c", "d"], rules, rng=random.Random(seed))
        table = [create_bot(level, name, random.Random(seed + i)) for i, (level, name) in enumerate(zip(LEVELS, "abcd"))]
        game.start_round()
        for _ in range(6000):
            if game.phase == Phase.ROUND_OVER:
                break
            apply(game, game.turn, table[game.turn])
            assert game.total_cards() == rules.deck_size
        assert game.phase == Phase.ROUND_OVER


@pytest.mark.parametrize("mode", [Mode.DOBLE, Mode.SIN_TREGUA])
def test_each_level_wins_more_than_the_one_below_in_every_mode(mode):
    results = run_tournament(list(LEVELS), 2000, seed=2026, rules=PrismaRules(mode=mode))
    rates = [results[level].win_rate for level in LEVELS]
    assert sum(result.wins for result in results.values()) == 2000
    for weaker, stronger in zip(LEVELS, list(LEVELS)[1:]):
        gap = results[stronger].win_rate - results[weaker].win_rate
        margin = results[stronger].margin + results[weaker].margin
        assert gap > margin / 2 > 0, (mode, weaker, stronger, rates)
