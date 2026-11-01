"""Modo Sin tregua: cargas que se acumulan, robar hasta poder, el 7 y el 0, la Ruleta y el desborde."""

import random
from collections import Counter

import pytest

from games.prisma.engine import (
    LIGHT_COLORS,
    Color,
    IllegalMove,
    Kind,
    Mode,
    Phase,
    PrismaGame,
    PrismaRules,
    full_deck,
    table_view,
)
from games.prisma.engine.views import event_view
from games.prisma.tests.helpers import card_id, codes, random_move, rigged

RELENTLESS = Mode.SIN_TREGUA


def relentless(hands: list[str], first: str, rest: str = "", **rules):
    return rigged(hands, first, rest, mode=RELENTLESS, **rules)


# --- El mazo ---


def test_the_deck_has_168_cards():
    deck = full_deck(RELENTLESS)
    assert len(deck) == 168
    assert sorted(card.id for card in deck) == list(range(168))
    for color in LIGHT_COLORS:
        mine = [card for card in deck if card.color == color]
        numbers = Counter(card.number for card in mine if card.kind == Kind.NUMBER)
        assert numbers == {number: 2 for number in range(10)}
        counts = Counter(card.kind for card in mine if card.kind != Kind.NUMBER)
        assert counts == {
            Kind.PAUSA: 3,
            Kind.REMOLINO: 3,
            Kind.CARGA: 3,
            Kind.CARGA4: 2,
            Kind.BARRIDO: 3,
            Kind.PAUSA_TOTAL: 2,
        }
    wilds = Counter(card.kind for card in deck if card.is_wild)
    assert wilds == {Kind.CAMALEON_REMOLINO4: 8, Kind.CAMALEON6: 4, Kind.CAMALEON10: 4, Kind.RULETA: 8}
    assert all(card.back is None for card in deck)


def test_points():
    deck = {card.code: card for card in full_deck(RELENTLESS)}
    assert deck["halo-barrido"].points_in(RELENTLESS) == deck["astro-carga4"].points_in(RELENTLESS) == 20
    assert deck["camaleon10"].points_in(RELENTLESS) == deck["ruleta"].points_in(RELENTLESS) == 50
    assert deck["cumbre-0"].points_in(RELENTLESS) == 0


def test_the_first_card_is_always_a_number():
    game = relentless(["panal-1", "halo-1"], "panal-pausa ruleta camaleon10", "cumbre-5")
    assert str(game.top) == "cumbre-5"
    assert sum(event.kind == "return" for event in game.events) == 3
    assert game.turn == 0 and game.total_cards() == 168


# --- Acumular ---


def test_draw_cards_stack_with_equal_or_higher_ones_of_any_colour():
    game = relentless(
        ["panal-carga panal-1", "halo-carga4 halo-1", "cumbre-carga cumbre-1"],
        "panal-5",
    )
    game.play(0, card_id(game, 0, "panal-carga"))
    assert game.pending_draw == 2 and game.turn == 1
    game.play(1, card_id(game, 1, "halo-carga4"))  # +4 sobre +2, de otro color
    assert game.pending_draw == 6 and game.pending_min == 4 and game.turn == 2
    # Un +2 ya no vale: hay que poner +4 o más, o robar.
    assert game.legal_plays(2) == []
    with pytest.raises(IllegalMove, match=r"\+4 o más"):
        game.play(2, card_id(game, 2, "cumbre-carga"))
    game.draw(2)
    assert len(game.players[2].hand) == 8 and game.pending_draw == 0
    assert game.turn == 0  # pierde el turno


def test_a_wild_ten_stacks_on_a_six():
    game = relentless(["camaleon6 panal-1", "camaleon10 halo-1"], "panal-5")
    game.play(0, card_id(game, 0, "camaleon6"), Color.HALO)
    game.play(1, card_id(game, 1, "camaleon10"), Color.ASTRO)
    assert game.pending_draw == 16 and game.turn == 0
    game.draw(0)
    assert len(game.players[0].hand) == 17


def test_the_wild_reverse_four_goes_back_the_other_way():
    game = relentless(["camaleon_remolino4 panal-1", "halo-1 halo-2", "cumbre-1 cumbre-2"], "panal-5")
    game.play(0, card_id(game, 0, "camaleon_remolino4"), Color.HALO)
    assert game.direction == -1 and game.turn == 2  # el siguiente en el nuevo sentido
    assert game.pending_draw == 4


def test_with_two_players_the_wild_reverse_four_hits_whoever_played_it():
    game = relentless(["camaleon_remolino4 panal-carga4 panal-1", "halo-1 halo-2 halo-3"], "panal-5")
    game.play(0, card_id(game, 0, "camaleon_remolino4"), Color.PANAL)
    assert game.turn == 0 and game.pending_draw == 4
    game.play(0, card_id(game, 0, "panal-carga4"))  # lo devuelve acumulando
    assert game.turn == 1 and game.pending_draw == 8


# --- Robar ---


def test_drawing_goes_on_until_a_playable_card():
    game = relentless(["halo-1 halo-2", "cumbre-1 cumbre-2"], "panal-5", "astro-8 cumbre-9 panal-6 halo-3")
    game.draw(0)
    drawn = game.events[-1]
    assert drawn.kind == "draw" and [card.code for card in drawn.cards] == ["astro-8", "cumbre-9", "panal-6"]
    assert game.drawn is not None and game.drawn.code == "panal-6" and game.turn == 0
    game.play(0, game.drawn.id)
    assert game.turn == 1


# --- Cartas de acción ---


def test_sweep_discards_every_card_of_its_colour():
    game = relentless(["panal-barrido panal-2 panal-9 halo-4", "cumbre-1 cumbre-2 cumbre-3 cumbre-4"], "panal-5")
    game.play(0, card_id(game, 0, "panal-barrido"))
    assert codes(game, 0) == ["halo-4"]
    assert str(game.top) == "panal-barrido"
    assert [card.code for card in game.discard[-3:-1]] == ["panal-2", "panal-9"]  # debajo
    assert game.vulnerable == 0  # se quedó con una y no dijo «¡Última!»
    assert game.turn == 1 and game.total_cards() == 168


def test_sweeping_your_whole_hand_wins_the_round():
    game = relentless(["panal-barrido panal-2 panal-9", "cumbre-1 cumbre-2 cumbre-3"], "panal-5")
    game.play(0, card_id(game, 0, "panal-barrido"))
    assert game.winner == 0 and game.phase == Phase.ROUND_OVER


def test_skip_everyone_plays_again():
    game = relentless(["panal-pausa_total panal-1", "halo-1 halo-2", "cumbre-1 cumbre-2"], "panal-5")
    game.play(0, card_id(game, 0, "panal-pausa_total"))
    assert game.turn == 0


def test_seven_swaps_hands_with_whoever_you_choose():
    game = relentless(["panal-7 panal-1 panal-2", "halo-1 halo-2 halo-3", "cumbre-1 cumbre-2 cumbre-3"], "panal-5")
    with pytest.raises(IllegalMove, match="con quién"):
        game.play(0, card_id(game, 0, "panal-7"))
    game.play(0, card_id(game, 0, "panal-7"), target=2)
    assert codes(game, 0) == ["cumbre-1", "cumbre-2", "cumbre-3"]
    assert codes(game, 2) == ["panal-1", "panal-2"]
    assert game.turn == 1
    assert game.events[-1].kind == "swap" and game.events[-1].target == 2


def test_zero_passes_every_hand_along():
    game = relentless(["panal-0 panal-1", "halo-1 halo-2", "cumbre-1 cumbre-2"], "panal-5")
    game.play(0, card_id(game, 0, "panal-0"))
    assert codes(game, 1) == ["panal-1"]  # mi mano pasa al siguiente
    assert codes(game, 2) == ["halo-1", "halo-2"]
    assert codes(game, 0) == ["cumbre-1", "cumbre-2"]
    assert game.vulnerable is None and game.players[1].said_last  # a salvo: no la jugó él


def test_after_a_swap_or_a_rotation_each_one_sees_only_their_own_new_hand():
    game = relentless(["panal-7 panal-0 panal-1", "halo-1 halo-2 halo-3", "cumbre-1 cumbre-2 cumbre-3"], "panal-5")
    game.play(0, card_id(game, 0, "panal-7"), target=2)
    swap = game.events[-1]
    # El evento guarda la foto de las manos justo después del cambio: cada uno
    # recibe la suya (para animar a qué cartas pasa), nunca la de los demás.
    for seat in range(3):
        view = event_view(swap, seat)
        assert [card["id"] for card in view["cards"]] == [card.id for card in game.players[seat].hand]
        assert view["backs"] == {}  # en Sin tregua no hay otra cara
    assert event_view(swap, None)["cards"] == []  # un mirón no ve ninguna mano
    # El 0 lo pasa todo al siguiente; la foto también es por persona.
    game.turn = 2
    game.players[2].hand.append(game.draw_pile.pop())
    game.players[2].hand[-1] = type(game.players[2].hand[-1])(game.players[2].hand[-1].id, Kind.NUMBER, Color.PANAL, 0)
    game.play(2, game.players[2].hand[-1].id)
    rotate = game.events[-1]
    assert rotate.kind == "rotate"
    for seat in range(3):
        assert [card["id"] for card in event_view(rotate, seat)["cards"]] == [card.id for card in game.players[seat].hand]


def test_only_the_seven_takes_a_target():
    game = relentless(["panal-6 panal-1", "halo-1 halo-2"], "panal-5")
    with pytest.raises(IllegalMove):
        game.play(0, card_id(game, 0, "panal-6"), target=1)


def test_the_roulette_reveals_cards_until_the_chosen_colour():
    game = relentless(
        ["ruleta panal-1", "halo-1 halo-2", "cumbre-1 cumbre-2"],
        "panal-5",
        "astro-3 camaleon10 panal-8 cumbre-7",
    )
    with pytest.raises(IllegalMove):
        game.play(0, card_id(game, 0, "ruleta"), Color.HALO)  # el color lo elige quien la sufre
    game.play(0, card_id(game, 0, "ruleta"))
    assert game.phase == Phase.ROULETTE and game.turn == 1
    assert table_view(game, 1).legal.roulette and not table_view(game, 2).legal.roulette
    game.roulette(1, Color.CUMBRE)
    reveal = next(event for event in game.events if event.kind == "reveal")
    assert [card.code for card in reveal.cards] == ["astro-3", "camaleon10", "panal-8", "cumbre-7"]
    # Las ve todo el mundo, no solo quien las roba.
    assert len(event_view(reveal, 0)["cards"]) == 4
    assert game.color == Color.CUMBRE and game.turn == 2
    assert len(game.players[1].hand) == 6


# --- Desborde ---


def test_reaching_25_cards_knocks_you_out():
    game = relentless(["camaleon10 camaleon10 panal-1", "halo-1 halo-2 halo-3", "cumbre-1 cumbre-2 cumbre-3"], "panal-5")
    game.players[1].hand += [game.draw_pile.pop() for _ in range(12)]  # 15 cartas
    game.play(0, card_id(game, 0, "camaleon10"), Color.PANAL)
    game.draw(1)  # roba 10: llega a 25
    assert 1 in game.out and game.players[1].hand == []
    assert len(game.set_aside) == 25
    assert game.events[-1].kind == "eliminated" and game.events[-1].count == 25
    assert game.turn == 2  # el eliminado ya no juega
    assert game.next_seat(0) == 2 and game.next_seat(2) == 0
    assert table_view(game, 0).players[1].out
    assert game.total_cards() == 168


def test_the_last_one_standing_wins_and_knockouts_score_250():
    game = relentless(["camaleon10 panal-1", "halo-1 halo-2"], "panal-5", scoring=True, target=1000)
    game.players[1].hand += [game.draw_pile.pop() for _ in range(13)]  # 15 cartas
    game.play(0, card_id(game, 0, "camaleon10"), Color.PANAL)
    game.draw(1)
    assert game.winner == 0 and game.phase == Phase.ROUND_OVER
    assert game.players[0].score == 250 + 0  # el eliminado no tiene cartas: solo el premio
    assert game.total_cards() == 168


def test_set_aside_cards_come_back_when_the_deck_is_reshuffled():
    game = relentless(["camaleon10 panal-1 panal-2", "halo-1 halo-2 halo-3", "cumbre-1 cumbre-2 cumbre-3"], "panal-5")
    game.players[1].hand += [game.draw_pile.pop() for _ in range(12)]
    game.play(0, card_id(game, 0, "camaleon10"), Color.PANAL)
    game.draw(1)
    aside = len(game.set_aside)
    # Vaciar el mazo en el descarte y forzar un rebarajado.
    game.discard[:-1] = game.discard[:-1] + game.draw_pile
    game.draw_pile = []
    game._reshuffle()
    assert game.set_aside == [] and len(game.draw_pile) >= aside
    assert game.total_cards() == 168


# --- Partidas enteras al azar ---


@pytest.mark.parametrize("seed", range(40))
def test_random_games_keep_all_168_cards(seed):
    rng = random.Random(seed)
    players = rng.randint(2, 6)
    rules = PrismaRules(mode=RELENTLESS, scoring=True, target=600)
    game = PrismaGame([f"J{i}" for i in range(players)], rules, rng=random.Random(seed))
    game.start_round()
    for _ in range(6000):
        if game.phase == Phase.ROUND_OVER:
            if game.game_over:
                break
            game.next_round()
        random_move(game, rng)
        assert game.total_cards() == 168
        for seat in game.out:
            assert game.players[seat].hand == []
        assert len(game.active) >= 1
        if game.phase != Phase.ROUND_OVER:
            assert game.turn not in game.out
            assert all(len(game.players[seat].hand) < 25 for seat in game.active)
    assert game.game_over
