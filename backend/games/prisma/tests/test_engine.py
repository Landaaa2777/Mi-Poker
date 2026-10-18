"""Motor de Prisma: el mazo, las jugadas legales e ilegales y el efecto de cada carta."""

import random
from collections import Counter

import pytest

from games.prisma.engine import (
    DECK_SIZE,
    Color,
    IllegalMove,
    Kind,
    Phase,
    PrismaGame,
    PrismaRules,
    full_deck,
    table_view,
)
from games.prisma.tests.helpers import card_id, codes, random_move, rigged

PANAL, HALO, CUMBRE, ASTRO = Color.PANAL, Color.HALO, Color.CUMBRE, Color.ASTRO


# --- El mazo ---


def test_the_deck_has_exactly_108_cards():
    deck = full_deck()
    assert len(deck) == DECK_SIZE == 108
    assert sorted(card.id for card in deck) == list(range(108))  # ids únicos
    for color in Color:
        mine = [card for card in deck if card.color == color]
        assert len(mine) == 25
        numbers = Counter(card.number for card in mine if card.kind == Kind.NUMBER)
        assert numbers == {0: 1, **{number: 2 for number in range(1, 10)}}
        for action in (Kind.PAUSA, Kind.REMOLINO, Kind.CARGA):
            assert sum(card.kind == action for card in mine) == 2
    assert sum(card.kind == Kind.CAMALEON for card in deck) == 4
    assert sum(card.kind == Kind.CAMALEON4 for card in deck) == 4
    assert all(card.color is None for card in deck if card.is_wild)
    # Sin duplicados inesperados: cada carta aparece las veces que debe.
    assert Counter(card.code for card in deck).most_common(1)[0][1] == 4  # los comodines


def test_card_points_and_names():
    deck = {card.code: card for card in full_deck()}
    assert deck["panal-7"].points == 7 and deck["halo-0"].points == 0
    assert deck["cumbre-pausa"].points == deck["astro-carga"].points == 20
    assert deck["camaleon"].points == deck["camaleon4"].points == 50
    assert deck["astro-remolino"].name() == "Astro Remolino"
    assert deck["camaleon4"].name() == "Camaleón +4"


# --- Reparto y carta inicial ---


def test_dealing_seven_cards_each():
    game = PrismaGame(["Tú", "Brisa", "Lince"], rng=random.Random(1))
    game.start_round()
    assert [len(player.hand) for player in game.players] == [7, 7, 7]
    assert len(game.discard) == 1 and game.top.kind != Kind.CAMALEON4
    assert game.total_cards() == 108
    assert game.turn == game.next_seat(game.dealer)


def test_a_wild_draw_four_cannot_start_the_round():
    game = rigged(["panal-1", "halo-1"], "camaleon4", "cumbre-5")
    assert str(game.top) == "cumbre-5"
    assert any(event.kind == "return" for event in game.events)
    assert sum(card.kind == Kind.CAMALEON4 for card in game.draw_pile) == 4  # volvió al mazo
    assert game.total_cards() == 108


def test_a_starting_pausa_skips_the_first_player():
    game = rigged(["panal-1", "halo-1", "cumbre-1"], "panal-pausa")
    assert game.turn == 1


def test_a_starting_remolino_lets_the_dealer_start_backwards():
    game = rigged(["panal-1", "halo-1", "cumbre-1"], "panal-remolino")
    assert game.direction == -1 and game.turn == 2  # el que reparte (el último)
    assert game.next_seat(2) == 1


def test_a_starting_carga_makes_the_first_player_draw_two():
    game = rigged(["panal-1", "halo-1", "cumbre-1"], "panal-carga")
    assert len(game.players[0].hand) == 3 and game.turn == 1


def test_a_starting_camaleon_lets_the_first_player_choose():
    game = rigged(["panal-1", "halo-1"], "camaleon")
    assert game.phase == Phase.CHOOSE_COLOR and game.turn == 0
    with pytest.raises(IllegalMove, match="color de la carta inicial"):
        game.play(0, card_id(game, 0, "panal-1"))
    with pytest.raises(IllegalMove, match="No es tu turno"):
        game.choose_color(1, HALO)
    game.choose_color(0, HALO)
    assert game.phase == Phase.PLAYING and game.color == HALO and game.turn == 0


# --- Jugadas legales e ilegales ---


def test_matching_color_number_or_symbol():
    game = rigged(["panal-3 halo-7 cumbre-pausa astro-2 camaleon", "halo-1 halo-2 halo-3 halo-4 halo-5"], "panal-7")
    playable = {card.code for card in game.legal_plays(0)}
    assert playable == {"panal-3", "halo-7", "camaleon"}  # color, número y comodín
    with pytest.raises(IllegalMove, match="no casa"):
        game.play(0, card_id(game, 0, "astro-2"))
    with pytest.raises(IllegalMove, match="no casa"):
        game.play(0, card_id(game, 0, "cumbre-pausa"))
    assert len(game.players[0].hand) == 5 and game.turn == 0  # nada cambió


def test_the_same_action_matches_across_colors():
    game = rigged(["astro-pausa halo-1", "cumbre-1 cumbre-2", "halo-pausa cumbre-3"], "astro-3")
    game.play(0, card_id(game, 0, "astro-pausa"))  # salta al 1: le toca al 2
    assert game.turn == 2
    # Una Pausa de otro color casa con la Pausa de la mesa; un 3 de otro color, no.
    assert {card.code for card in game.legal_plays(2)} == {"halo-pausa"}
    game.play(2, card_id(game, 2, "halo-pausa"))
    assert game.color == HALO and game.turn == 1  # salta al 0


def test_wilds_need_a_color_and_only_wilds_change_it():
    game = rigged(["camaleon panal-3", "halo-1 halo-2"], "panal-7")
    with pytest.raises(IllegalMove, match="Elige un color"):
        game.play(0, card_id(game, 0, "camaleon"))
    with pytest.raises(IllegalMove, match="Solo los comodines"):
        game.play(0, card_id(game, 0, "panal-3"), HALO)
    with pytest.raises(IllegalMove, match="Color desconocido"):
        game.play(0, card_id(game, 0, "camaleon"), "rojo")
    game.play(0, card_id(game, 0, "camaleon"), ASTRO)
    assert game.color == ASTRO and game.turn == 1


def test_only_the_player_in_turn_can_play():
    game = rigged(["panal-3 halo-1", "panal-4 halo-2"], "panal-7")
    with pytest.raises(IllegalMove, match="No es tu turno"):
        game.play(1, card_id(game, 1, "panal-4"))
    with pytest.raises(IllegalMove, match="No tienes esa carta"):
        game.play(0, card_id(game, 1, "panal-4"))


def test_without_challenge_the_draw_four_needs_no_card_of_the_color():
    game = rigged(["camaleon4 panal-3 halo-1", "halo-2 halo-3 halo-4"], "panal-7", challenge=False)
    assert "camaleon4" not in {card.code for card in game.legal_plays(0)}
    with pytest.raises(IllegalMove, match="Camaleón \\+4 solo se puede jugar"):
        game.play(0, card_id(game, 0, "camaleon4"), HALO)
    # Sin cartas del color de la mesa sí se puede (aunque tenga otras que casen por número).
    legit = rigged(["camaleon4 halo-7 astro-1", "halo-2 halo-3 halo-4"], "panal-7", challenge=False)
    legit.play(0, card_id(legit, 0, "camaleon4"), HALO)
    assert len(legit.players[1].hand) == 7 and legit.turn == 0  # el 1 roba 4 y pierde el turno


# --- Desafío del Camaleón +4 ---


def test_accepting_a_draw_four():
    game = rigged(["camaleon4 halo-1 halo-2", "astro-1 astro-2 astro-3", "cumbre-1 cumbre-2 cumbre-3"], "panal-7")
    game.play(0, card_id(game, 0, "camaleon4"), HALO)
    assert game.phase == Phase.CHALLENGE and game.turn == 1
    with pytest.raises(IllegalMove, match="desafía"):
        game.draw(1)
    game.accept(1)
    assert len(game.players[1].hand) == 7 and game.turn == 2 and game.phase == Phase.PLAYING


def test_a_bluff_caught_by_a_challenge():
    game = rigged(["camaleon4 panal-1 halo-2", "astro-1 astro-2 astro-3", "cumbre-1 cumbre-2 cumbre-3"], "panal-7")
    game.play(0, card_id(game, 0, "camaleon4"), HALO)  # tenía panal-1: farol
    game.challenge(1)
    assert len(game.players[0].hand) == 6  # el que faroleó roba 4
    assert len(game.players[1].hand) == 3 and game.turn == 1  # y el desafiante juega
    assert game.events[-2].kind == "challenge" and game.events[-2].result == "guilty"


def test_a_failed_challenge_costs_six_cards():
    game = rigged(["camaleon4 halo-1 halo-2", "astro-1 astro-2 astro-3", "cumbre-1 cumbre-2 cumbre-3"], "panal-7")
    game.play(0, card_id(game, 0, "camaleon4"), HALO)  # no tenía panal: era legal
    game.challenge(1)
    assert len(game.players[1].hand) == 9 and game.turn == 2


# --- Efectos de las acciones ---


def test_pausa_skips_the_next_player():
    game = rigged(["panal-pausa panal-1", "halo-1 halo-2", "cumbre-1 cumbre-2"], "panal-7")
    game.play(0, card_id(game, 0, "panal-pausa"))
    assert game.turn == 2


def test_remolino_reverses_the_order():
    game = rigged(["panal-remolino panal-1", "halo-1 halo-2", "cumbre-1 cumbre-2"], "panal-7")
    game.play(0, card_id(game, 0, "panal-remolino"))
    assert game.direction == -1 and game.turn == 2
    assert game.next_seat(2) == 1


def test_with_two_players_remolino_acts_as_pausa():
    game = rigged(["panal-remolino panal-1 panal-2", "halo-1 halo-2 halo-3"], "panal-7")
    game.play(0, card_id(game, 0, "panal-remolino"))
    assert game.turn == 0  # vuelvo a jugar yo
    assert any(event.kind == "skip" and event.seat == 1 for event in game.events)


def test_carga_makes_the_next_draw_two_and_lose_the_turn():
    game = rigged(["panal-carga panal-1", "halo-1 halo-2", "cumbre-1 cumbre-2"], "panal-7")
    game.play(0, card_id(game, 0, "panal-carga"))
    assert len(game.players[1].hand) == 4 and game.turn == 2


# --- Robar ---


def test_drawing_a_playable_card_lets_you_play_it_or_pass():
    game = rigged(["halo-1 halo-2", "astro-1 astro-2"], "panal-7", rest="panal-5")
    game.draw(0)
    assert game.drawn is not None and str(game.drawn) == "panal-5" and game.turn == 0
    assert [card.code for card in game.legal_plays(0)] == ["panal-5"]
    with pytest.raises(IllegalMove, match="Ya has robado"):
        game.draw(0)
    game.pass_turn(0)
    assert game.turn == 1 and "panal-5" in codes(game, 0)


def test_after_drawing_only_the_drawn_card_can_be_played():
    game = rigged(["panal-1 halo-2", "astro-1 astro-2"], "panal-7", rest="panal-5")
    game.draw(0)  # se puede robar aunque se tenga jugada, como en el clásico
    with pytest.raises(IllegalMove, match="carta robada"):
        game.play(0, card_id(game, 0, "panal-1"))
    game.play(0, card_id(game, 0, "panal-5"))
    assert game.turn == 1


def test_an_unplayable_drawn_card_passes_the_turn():
    game = rigged(["halo-1 halo-2", "astro-1 astro-2"], "panal-7", rest="cumbre-3")
    game.draw(0)
    assert game.drawn is None and game.turn == 1
    with pytest.raises(IllegalMove, match="después de robar"):
        game.pass_turn(1)


def test_an_empty_draw_pile_is_rebuilt_from_the_discard_but_its_top():
    game = rigged(["panal-1 panal-2 panal-3", "panal-4 panal-5 panal-6"], "panal-7")
    while game.draw_pile:
        game.draw_pile.pop(0)  # se vacía el mazo a mano…
        game.discard.insert(0, game.draw_pile.pop()) if game.draw_pile else None
    top = game.top
    before = len(game.discard)
    game.draw(0)
    assert game.top == top and len(game.discard) == 1
    assert any(event.kind == "reshuffle" and event.count == before - 1 for event in game.events)


# --- "¡Última!" ---


def test_forgetting_to_say_last_lets_anyone_catch_you():
    game = rigged(["panal-1 panal-2", "halo-1 halo-2", "astro-1 astro-2"], "panal-7")
    game.play(0, card_id(game, 0, "panal-1"))  # me quedo con una y no digo nada
    assert game.vulnerable == 0
    view = table_view(game, 2)
    assert view.legal.catch and view.players[0].vulnerable
    with pytest.raises(IllegalMove, match="nadie a quien pillar"):
        game.catch(0)  # a uno mismo no
    game.catch(2)
    assert len(game.players[0].hand) == 3 and game.vulnerable is None


def test_saying_last_with_the_play_keeps_you_safe():
    game = rigged(["panal-1 panal-2", "halo-1 halo-2"], "panal-7")
    game.play(0, card_id(game, 0, "panal-1"), declare=True)
    assert game.vulnerable is None and game.players[0].said_last
    with pytest.raises(IllegalMove):
        game.catch(1)


def test_saying_last_before_playing_or_right_after_also_works():
    before = rigged(["panal-1 panal-2", "halo-1 halo-2"], "panal-7")
    before.declare_last(0)
    before.play(0, card_id(before, 0, "panal-1"))
    assert before.vulnerable is None
    after = rigged(["panal-1 panal-2", "halo-1 halo-2"], "panal-7")
    after.play(0, card_id(after, 0, "panal-1"))
    after.declare_last(0)  # todavía no ha jugado el siguiente
    assert after.vulnerable is None and after.players[0].said_last


def test_once_the_next_player_acts_it_is_too_late_to_catch():
    game = rigged(["panal-1 panal-2", "halo-1 panal-3", "astro-1 astro-2"], "panal-7")
    game.play(0, card_id(game, 0, "panal-1"))
    game.play(1, card_id(game, 1, "panal-3"))  # el siguiente juega: se cierra mi ventana
    # Ahora el pillable es el 1 (también se quedó con una sin decir nada), no yo.
    assert game.vulnerable == 1
    game.catch(2)
    assert len(game.players[1].hand) == 3 and len(game.players[0].hand) == 1
    with pytest.raises(IllegalMove):
        game.catch(2)  # a mí ya no me puede pillar nadie
    with pytest.raises(IllegalMove, match="una sola carta"):
        game.declare_last(0)


def test_last_cannot_be_said_with_many_cards():
    game = rigged(["panal-1 panal-2 panal-3", "halo-1 halo-2 halo-3"], "panal-7")
    with pytest.raises(IllegalMove, match="una sola carta"):
        game.declare_last(0)
    with pytest.raises(IllegalMove, match="penúltima"):
        game.play(0, card_id(game, 0, "panal-1"), declare=True)


# --- Final de ronda y puntos ---


def test_emptying_your_hand_wins_the_round_and_the_points():
    game = rigged(
        ["panal-1", "halo-9", "astro-carga"],
        "panal-7",
        scoring=True,
        target=500,
    )
    game.players[1].hand += [card for card in game.draw_pile if card.code == "camaleon"][:1]
    game.draw_pile = [card for card in game.draw_pile if card not in game.players[1].hand]
    game.play(0, card_id(game, 0, "panal-1"))
    assert game.phase == Phase.ROUND_OVER and game.winner == 0
    assert game.players[0].score == 9 + 50 + 20
    assert not game.game_over
    game.next_round()
    assert game.round_number == 2 and game.phase in (Phase.PLAYING, Phase.CHOOSE_COLOR)


def test_without_scoring_each_round_is_a_whole_game():
    game = rigged(["panal-1", "halo-9"], "panal-7")
    game.play(0, card_id(game, 0, "panal-1"))
    assert game.game_over and game.players[0].score == 0
    with pytest.raises(IllegalMove, match="terminado"):
        game.next_round()


def test_reaching_the_target_ends_the_game():
    game = rigged(["panal-1", "camaleon4"], "panal-7", scoring=True, target=50)
    game.play(0, card_id(game, 0, "panal-1"))
    assert game.players[0].score == 50 and game.game_over


def test_a_last_carga_still_makes_the_next_player_draw():
    game = rigged(["panal-carga", "halo-1", "astro-1"], "panal-7")
    game.play(0, card_id(game, 0, "panal-carga"))
    assert game.winner == 0 and len(game.players[1].hand) == 3
    assert game.total_cards() == 108


# --- Opciones de la casa: acumular ---


def test_stacking_draw_two_when_the_house_allows_it():
    game = rigged(
        ["panal-carga panal-1", "halo-carga halo-1", "astro-1 astro-2"], "panal-7", stack_draw2=True
    )
    game.play(0, card_id(game, 0, "panal-carga"))
    assert game.pending_draw == 2 and game.turn == 1
    assert [card.code for card in game.legal_plays(1)] == ["halo-carga"]
    game.play(1, card_id(game, 1, "halo-carga"))
    assert game.pending_draw == 4 and game.turn == 2
    game.draw(2)  # no tiene Carga: roba las 4 y pierde el turno
    assert len(game.players[2].hand) == 6 and game.turn == 0 and game.pending_draw == 0


def test_stacking_draw_four_turns_off_the_challenge():
    game = rigged(["camaleon4 halo-1", "camaleon4 astro-1", "cumbre-1 cumbre-2"], "panal-7", stack_draw4=True)
    game.play(0, card_id(game, 0, "camaleon4"), HALO)
    assert game.phase == Phase.PLAYING and game.pending_draw == 4 and game.turn == 1
    game.play(1, card_id(game, 1, "camaleon4"), ASTRO)
    assert game.pending_draw == 8
    game.draw(2)
    assert len(game.players[2].hand) == 10


def test_stacking_is_off_by_default():
    rules = PrismaRules()
    assert not rules.stack_draw2 and not rules.stack_draw4 and rules.challenge and not rules.scoring


# --- Simulación: siempre 108 cartas ---


@pytest.mark.parametrize("players", [2, 3, 4, 6])
def test_random_games_never_lose_or_create_cards(players):
    rng = random.Random(players)
    for game_number in range(40):
        game = PrismaGame([f"J{i}" for i in range(players)], PrismaRules(scoring=game_number % 2 == 0), rng=random.Random(game_number))
        game.start_round()
        for _ in range(3000):
            if game.phase == Phase.ROUND_OVER:
                if game.game_over:
                    break
                game.next_round()
            random_move(game, rng)
            assert game.total_cards() == 108
        ids = [card.id for card in game.draw_pile + game.discard] + [
            card.id for player in game.players for card in player.hand
        ]
        assert sorted(ids) == list(range(108))


def test_a_round_nobody_can_finish_goes_to_whoever_has_fewest_cards():
    """Sin nada que robar ni que rebarajar, una vuelta entera sin jugar tranca la ronda."""
    game = PrismaGame(["Ana", "Luis", "Eva"], rng=random.Random(3))
    game.start_round()
    if game.phase == Phase.CHOOSE_COLOR:
        game.choose_color(game.turn, "halo")
    # Todas las cartas en las manos; Luis se queda con las suyas, que son las menos.
    rest = game.draw_pile + game.discard[:-1]
    game.draw_pile, game.discard = [], game.discard[-1:]
    for index, card in enumerate(rest):
        game.players[0 if index % 2 else 2].hand.append(card)
    fewest = min(game.players, key=lambda player: len(player.hand)).seat
    for _ in range(2):
        game.draw(game.turn)  # se puede robar aunque se tenga jugada: aquí no sale nada
        assert game.phase == Phase.PLAYING
    game.draw(game.turn)
    assert game.phase == Phase.ROUND_OVER and game.winner == fewest == 1
    assert [event.kind for event in game.events[-2:]] == ["blocked", "round_over"]
    assert game.total_cards() == 108 and game.game_over


def test_playing_a_card_resets_the_count_of_dry_turns():
    game = PrismaGame(["Ana", "Luis"], rng=random.Random(5))
    game.start_round()
    game.dry_turns = 1
    if game.phase == Phase.CHOOSE_COLOR:
        game.choose_color(game.turn, "halo")
    playable = game.legal_plays(game.turn)
    if playable:
        card = playable[0]
        game.play(game.turn, card.id, "halo" if card.is_wild else None)
        assert game.dry_turns == 0
