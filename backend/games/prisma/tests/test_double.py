"""Modo Doble cara: cartas de dos caras, el Eclipse que voltea la mesa y sus cartas propias."""

import random
from collections import Counter

import pytest

from games.prisma.engine import (
    DARK_COLORS,
    LIGHT_COLORS,
    Color,
    IllegalMove,
    Kind,
    Mode,
    Phase,
    PrismaGame,
    PrismaRules,
    Side,
    full_deck,
    table_view,
)
from games.prisma.tests.helpers import card_id, codes, random_move, rigged_double

DOUBLE = PrismaRules(mode=Mode.DOBLE)


# --- El mazo ---


def test_the_deck_has_112_cards_with_two_faces():
    deck = full_deck(Mode.DOBLE)
    assert len(deck) == 112
    assert sorted(card.id for card in deck) == list(range(112))
    assert all(card.back is not None and card.back.back is None for card in deck)
    for side, colors, actions, wilds in (
        ([card for card in deck], LIGHT_COLORS, (Kind.CARGA1, Kind.REMOLINO, Kind.PAUSA, Kind.ECLIPSE), (Kind.CAMALEON, Kind.CAMALEON2)),
        ([card.back for card in deck], DARK_COLORS, (Kind.CARGA5, Kind.REMOLINO, Kind.PAUSA_TOTAL, Kind.ECLIPSE), (Kind.CAMALEON, Kind.SABUESO)),
    ):
        for color in colors:
            mine = [face for face in side if face.color == color]
            assert len(mine) == 26
            numbers = Counter(face.number for face in mine if face.kind == Kind.NUMBER)
            assert numbers == {number: 2 for number in range(1, 10)}  # sin ceros
            for action in actions:
                assert sum(face.kind == action for face in mine) == 2
        for wild in wilds:
            assert sum(face.kind == wild for face in side) == 4
        assert {face.color for face in side} == set(colors) | {None}


def test_faces_are_paired_at_random_each_round():
    first = full_deck(Mode.DOBLE, random.Random(1))
    second = full_deck(Mode.DOBLE, random.Random(2))
    pairs = lambda deck: [(card.code, card.back.code) for card in deck]  # noqa: E731
    assert pairs(first) != pairs(second)
    # Pero las caras del mazo son siempre las mismas.
    assert Counter(card.back.code for card in first) == Counter(card.back.code for card in second)


def test_points_depend_on_the_face_in_play():
    faces = {card.code: card for card in full_deck(Mode.DOBLE)}
    darks = {card.back.code: card.back for card in full_deck(Mode.DOBLE)}
    assert faces["panal-carga1"].points_in(Mode.DOBLE) == 10
    assert faces["halo-eclipse"].points_in(Mode.DOBLE) == 20
    assert faces["camaleon"].points_in(Mode.DOBLE) == 40
    assert faces["camaleon2"].points_in(Mode.DOBLE) == 50
    assert darks["brasa-pausa_total"].points_in(Mode.DOBLE) == 30
    assert darks["jade-carga5"].points_in(Mode.DOBLE) == 20
    assert darks["sabueso"].points_in(Mode.DOBLE) == 60
    assert darks["indigo-7"].points_in(Mode.DOBLE) == 7
    assert darks["sabueso"].name() == "Camaleón Sabueso" and darks["ambar-pausa_total"].name() == "Ámbar Pausa total"


# --- Reparto y carta inicial ---


def test_a_round_starts_on_the_light_side():
    game = PrismaGame(["Tú", "Brisa", "Lince"], DOUBLE, rng=random.Random(4))
    game.start_round()
    assert game.side == Side.LUZ and game.colors == LIGHT_COLORS
    assert game.top.color in LIGHT_COLORS or game.top.kind == Kind.CAMALEON
    assert game.total_cards() == 112
    assert [len(player.hand) for player in game.players] == [7, 7, 7]


@pytest.mark.parametrize("first", ["camaleon2", "panal-eclipse"])
def test_a_wild_draw_two_or_an_eclipse_cannot_start(first):
    game = rigged_double(["panal-1", "halo-1"], first, "cumbre-5")
    assert str(game.top) == "cumbre-5"
    assert any(event.kind == "return" for event in game.events)
    assert game.total_cards() == 112


def test_a_starting_draw_one_makes_the_first_player_draw_and_skip():
    game = rigged_double(["panal-1", "halo-1", "cumbre-1"], "astro-carga1")
    assert len(game.players[0].hand) == 2
    assert game.turn == 1


# --- El Eclipse ---


def test_the_eclipse_flips_the_discard_the_deck_and_every_hand():
    game = rigged_double(
        ["panal-eclipse panal-2/brasa-4", "halo-3/jade-6 halo-4/indigo-1"],
        "panal-5/ambar-9",
        "cumbre-7/brasa-2 astro-8/jade-3",
    )
    deck_before = [card.code for card in game.draw_pile]
    game.play(0, card_id(game, 0, "panal-eclipse"))
    assert game.side == Side.SOMBRA and game.colors == DARK_COLORS
    # El descarte se da la vuelta entero: la carta de abajo (el Panal 5) queda arriba, por su sombra.
    assert str(game.top) == "ambar-9" and game.color == Color.AMBAR
    assert game.discard[0].back.kind == Kind.ECLIPSE  # el Eclipse jugado queda abajo
    # El mazo también: la que era la última queda arriba, y se ve la otra cara.
    assert [card.back.code for card in game.draw_pile] == list(reversed(deck_before))
    # Las manos, también.
    assert codes(game, 0) == ["brasa-4"]
    assert codes(game, 1) == ["jade-6", "indigo-1"]
    assert game.turn == 1 and game.phase == Phase.PLAYING
    assert game.total_cards() == 112
    assert game.events[-1].kind == "eclipse" and game.events[-1].result == "sombra"


def test_a_revealed_card_does_nothing():
    # Al voltear, sale arriba una Carga +5: nadie roba.
    game = rigged_double(["panal-eclipse panal-2", "halo-3 halo-4"], "panal-5/brasa-carga5")
    game.play(0, card_id(game, 0, "panal-eclipse"))
    assert str(game.top) == "brasa-carga5"
    assert len(game.players[1].hand) == 2 and game.turn == 1


def test_when_a_wild_is_revealed_the_eclipse_player_chooses_the_colour():
    game = rigged_double(["panal-eclipse panal-2", "halo-3 halo-4"], "panal-5/camaleon")
    game.play(0, card_id(game, 0, "panal-eclipse"))
    assert game.phase == Phase.CHOOSE_COLOR and game.turn == 0
    with pytest.raises(IllegalMove):
        game.choose_color(0, Color.PANAL)  # en la sombra no hay Panal
    game.choose_color(0, Color.JADE)
    assert game.color == Color.JADE and game.turn == 1 and game.phase == Phase.PLAYING


def test_two_eclipses_bring_everything_back():
    game = rigged_double(
        ["panal-eclipse panal-2 panal-3", "halo-3 halo-4/brasa-eclipse halo-5"],
        "panal-5",
    )
    hands = [codes(game, seat) for seat in (0, 1)]
    game.play(0, card_id(game, 0, "panal-eclipse"))  # pasa a la sombra
    eclipse = next(card for card in game.players[1].hand if card.kind == Kind.ECLIPSE)
    # El rival tenía un Eclipse por la cara de sombra: ahora lo puede jugar si casa.
    game.color = eclipse.color
    game.play(1, eclipse.id)
    assert game.side == Side.LUZ
    assert codes(game, 0) == hands[0][1:]
    assert codes(game, 1) == [code for code in hands[1] if code != "halo-4"]
    assert game.total_cards() == 112


def test_on_the_dark_side_cards_match_by_dark_colour():
    game = rigged_double(["panal-eclipse panal-2/brasa-4 panal-3/indigo-4", "halo-3 halo-4 halo-5"], "panal-5/brasa-9")
    game.play(0, card_id(game, 0, "panal-eclipse"))
    game.turn = 0
    assert {card.code for card in game.legal_plays(0)} == {"brasa-4"}  # el mismo color de sombra
    with pytest.raises(IllegalMove):
        game.play(0, card_id(game, 0, "indigo-4"))


# --- Cartas de cada cara ---


def test_draw_one_makes_the_next_draw_one_and_lose_the_turn():
    game = rigged_double(["panal-carga1 panal-2", "halo-3 halo-4", "cumbre-3 cumbre-4"], "panal-5")
    game.play(0, card_id(game, 0, "panal-carga1"))
    assert len(game.players[1].hand) == 3
    assert game.turn == 2


def test_draw_five_and_skip_everyone_on_the_dark_side():
    game = rigged_double(
        ["panal-eclipse panal-2/brasa-carga5 panal-3/brasa-pausa_total panal-4",
         "halo-3 halo-4 halo-5 halo-6", "cumbre-3 cumbre-4 cumbre-5 cumbre-6"],
        "panal-5/brasa-9",
    )
    game.play(0, card_id(game, 0, "panal-eclipse"))
    game.turn = 0
    game.play(0, card_id(game, 0, "brasa-carga5"))
    assert len(game.players[1].hand) == 9 and game.turn == 2
    game.turn = 0
    game.play(0, card_id(game, 0, "brasa-pausa_total"))
    assert game.turn == 0  # todos pierden el turno: vuelve a jugar
    assert game.events[-1].kind == "skip_all"


def test_wild_draw_two_without_challenge_needs_no_colour_in_hand():
    game = rigged_double(["camaleon2 panal-2", "halo-3 halo-4"], "panal-5", challenge=False)
    with pytest.raises(IllegalMove, match="Camaleón \\+2"):
        game.play(0, card_id(game, 0, "camaleon2"), Color.HALO)
    game = rigged_double(["camaleon2 halo-2", "halo-3 halo-4"], "panal-5", challenge=False)
    game.play(0, card_id(game, 0, "camaleon2"), Color.HALO)
    assert len(game.players[1].hand) == 4 and game.turn == 0


def test_challenging_a_wild_draw_two():
    # Farol: tenía Panal. El desafiante gana: quien lo jugó roba 2 y el desafiante juega.
    game = rigged_double(["camaleon2 panal-2 panal-3", "halo-3 halo-4 halo-5"], "panal-5")
    game.play(0, card_id(game, 0, "camaleon2"), Color.HALO)
    assert game.phase == Phase.CHALLENGE and game.turn == 1
    game.challenge(1)
    assert len(game.players[0].hand) == 4 and game.turn == 1
    # Sin farol: el desafiante roba 2 + 2 y pierde el turno.
    game = rigged_double(["camaleon2 halo-2 halo-3", "halo-4 halo-5 halo-6"], "panal-5")
    game.play(0, card_id(game, 0, "camaleon2"), Color.HALO)
    game.challenge(1)
    assert len(game.players[1].hand) == 7 and game.turn == 0


def test_the_hound_makes_the_next_draw_until_the_chosen_colour():
    game = rigged_double(["panal-eclipse panal-2/sabueso panal-3/ambar-1", "halo-3 halo-4 halo-5"], "panal-5/brasa-9")
    game.play(0, card_id(game, 0, "panal-eclipse"))
    game.turn = 0
    # Lo que sale del mazo: dos Brasa, un comodín (no cuenta como color) y luego un Jade.
    pile = game.draw_pile
    jade = next(card for card in pile if card.code == "jade-2")
    wild = next(card for card in pile if card.kind == Kind.CAMALEON)
    brasas = [card for card in pile if card.color == Color.BRASA][:2]
    for card in (jade, wild, *brasas):
        pile.remove(card)
    pile += [jade, wild, *brasas]  # la última es la de arriba
    game.play(0, card_id(game, 0, "sabueso"), Color.JADE)
    assert game.phase == Phase.CHALLENGE  # tenía Ámbar, pero en la mesa había Brasa: no era farol
    game.accept(1)
    drawn = next(event for event in reversed(game.events) if event.kind == "draw")
    assert [card.code for card in drawn.cards] == [brasas[1].code, brasas[0].code, "camaleon", "jade-2"]
    assert drawn.reason == "sabueso"
    assert len(game.players[1].hand) == 7 and game.turn == 0
    assert game.total_cards() == 112


def test_challenging_an_honest_hound_costs_the_colour_plus_two():
    game = rigged_double(["panal-eclipse panal-2/sabueso panal-3/ambar-1", "halo-3 halo-4 halo-5"], "panal-5/brasa-9")
    game.play(0, card_id(game, 0, "panal-eclipse"))
    game.turn = 0
    game.play(0, card_id(game, 0, "sabueso"), Color.JADE)
    before = len(game.players[1].hand)
    game.challenge(1)
    hand = game.players[1].hand[before:]
    jade = min(i for i, card in enumerate(hand) if card.color == Color.JADE)
    assert len(hand) - jade - 1 == 2  # hasta el primer Jade, y dos más
    challenge = next(event for event in reversed(game.events) if event.kind == "challenge")
    assert challenge.result == "innocent" and game.turn == 0


# --- Lo que ve cada uno ---


def test_everyone_sees_the_other_face_of_the_others_cards_but_never_their_own():
    game = rigged_double(["panal-1/brasa-1 panal-2/jade-2", "halo-1/ambar-3 halo-2/indigo-4"], "panal-5")
    mine = table_view(game, 0)
    assert mine.players[0].backs == ()  # mis caras de sombra no las veo
    assert [(face["kind"], face["color"], face["number"]) for face in mine.players[1].backs] == [
        ("number", "ambar", 3),
        ("number", "indigo", 4),
    ]
    # Con un alias al azar, nunca con el id de la carta.
    ids = {card.id for card in game.players[1].hand}
    assert all("id" not in face for face in mine.players[1].backs)
    assert {face["key"] for face in mine.players[1].backs} == {game.aliases[i] for i in ids}
    # Mi mano solo trae la cara en juego.
    assert all(card.back is None for card in mine.hand)
    assert all("back" not in card for card in mine.to_dict()["hand"])
    # La otra cara de la carta de arriba del mazo la ve todo el mundo.
    assert mine.deck_back == {"kind": game.draw_pile[-1].back.kind.value, "color": game.draw_pile[-1].back.color, "number": game.draw_pile[-1].back.number}
    assert mine.side == "luz" and mine.colors == tuple(color.value for color in LIGHT_COLORS)


def test_the_classic_mode_sends_no_other_faces():
    game = PrismaGame(["A", "B"], rng=random.Random(1))
    game.start_round()
    view = table_view(game, 0)
    assert view.deck_back is None and view.mode == "clasico"


def test_points_are_counted_on_the_face_in_play():
    game = rigged_double(["panal-eclipse panal-1/jade-3", "halo-3/sabueso halo-4/brasa-7"], "panal-5")
    game.play(0, card_id(game, 0, "panal-eclipse"))  # sombra: el rival tiene Sabueso (60) y Brasa 7
    game.turn = 0
    game.color = Color.JADE
    game.play(0, card_id(game, 0, "jade-3"))
    assert game.winner == 0
    assert game.events[-1].count == 67


# --- Partidas enteras al azar ---


@pytest.mark.parametrize("seed", range(40))
def test_random_games_keep_all_112_cards(seed):
    rng = random.Random(seed)
    players = rng.randint(2, 6)
    rules = PrismaRules(mode=Mode.DOBLE, challenge=rng.random() < 0.7, scoring=True, target=200)
    game = PrismaGame([f"J{i}" for i in range(players)], rules, rng=random.Random(seed))
    game.start_round()
    for _ in range(4000):
        if game.phase == Phase.ROUND_OVER:
            if game.game_over:
                break
            game.next_round()
        random_move(game, rng)
        assert game.total_cards() == 112
        for player in game.players:
            assert all(card.back is not None for card in player.hand)
        assert all((card.color in game.colors) or card.is_wild for card in game.discard)
    assert game.game_over
