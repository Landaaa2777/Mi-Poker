"""Servidor: una partida de Prisma por WebSocket, de principio a fin."""

import random

import pytest
from fastapi.testclient import TestClient

from games.prisma.tests.helpers import card_id, rigged
from server.app import create_app

GUEST = "invitado-de-prueba"


def prisma_url(client, guest_id=GUEST):
    response = client.post("/api/partidas", json={"game": "prisma", "guest_id": guest_id})
    assert response.status_code == 200, response.text
    return f"/ws/prisma/{response.json()['partida_id']}?guest_id={guest_id}"


@pytest.fixture
def app():
    return create_app(bot_delay=(0, 0), serve_frontend=False, require_account=False)


class Table:
    def __init__(self, socket, session):
        self.socket, self.session = socket, session
        self.states = []

    def receive(self):
        message = self.socket.receive_json()
        if message["type"] == "state":
            self.states.append(message["state"])
        return message

    def settle(self):
        """Lee estados hasta que me toca decidir algo o acaba la ronda."""
        while True:
            message = self.receive()
            assert message["type"] == "state", message
            state = message["state"]
            legal = state["legal"]
            mine = (
                legal["play"] or legal["draw"] or legal["pass"] or legal["choose_color"] or legal["challenge"] or legal["roulette"]
            )
            if state["phase"] == "round_over" or mine:
                return state

    def request(self, **message):
        self.socket.send_json(message)
        return self.settle()

    def error(self, **message):
        self.socket.send_json(message)
        reply = self.receive()
        assert reply["type"] == "error", reply
        return reply["message"]


@pytest.fixture
def table(app):
    client = TestClient(app)
    with client.websocket_connect(prisma_url(client)) as socket:
        hello = socket.receive_json()
        assert hello["type"] == "hello" and hello["game"] == "prisma" and hello["state"] is None
        yield Table(socket, lambda: app.state.partidas.find(GUEST, "prisma").session)


def cards_in(value):
    """Todas las cartas (diccionarios con id y tipo) que aparecen en un estado."""
    found = []
    if isinstance(value, dict):
        if {"id", "kind", "color", "number"} <= set(value):
            found.append(value["id"])
        for item in value.values():
            found += cards_in(item)
    elif isinstance(value, list):
        for item in value:
            found += cards_in(item)
    return found


def visible_to_me(state):
    """Las cartas que tengo derecho a ver: las mías, las que se han jugado o volteado,
    en Sin tregua las que destapa la Ruleta y las que barre el Barrido, y mi mano
    tal como quedó tras un cambio de manos (el 7 y el 0) o un Eclipse."""
    ids = {card["id"] for card in state["hand"]} | {state["top"]["id"]}
    for event in state["events"]:
        if event["card"]:
            ids.add(event["card"]["id"])
        if event["seat"] == state["human_seat"] or event["kind"] in ("reveal", "sweep", *HAND_MOVES):
            ids |= {card["id"] for card in event["cards"]}
    return ids


HAND_MOVES = ("swap", "rotate", "eclipse")  # eventos que llevan la foto de las manos


def play_any(state, rng):
    """Una intención legal cualquiera para el estado recibido."""
    legal = state["legal"]
    colors = state["colors"]  # los que están en juego (los de sombra, en la sombra)
    if legal["choose_color"]:
        return {"type": "color", "color": rng.choice(colors)}
    if legal["roulette"]:
        return {"type": "roulette", "color": rng.choice(colors)}
    if legal["challenge"]:
        return {"type": rng.choice(["challenge", "accept"])}
    if legal["play"]:
        chosen = rng.choice(legal["play"])
        card = next(card for card in state["hand"] if card["id"] == chosen)
        color = rng.choice(colors) if card["color"] is None and card["kind"] != "ruleta" else None
        message = {"type": "play", "card": card["id"], "color": color}
        message["declare"] = len(state["hand"]) == 2 and card["kind"] != "barrido"
        if state["mode"] == "sin_tregua" and card["number"] == 7 and len(state["hand"]) > 1:
            rivals = [p["seat"] for p in state["players"] if p["seat"] != state["human_seat"] and not p["out"]]
            message["target"] = rng.choice(rivals)
        return message
    return {"type": "pass"} if legal["pass"] else {"type": "draw"}


def test_the_hello_explains_the_options(app):
    client = TestClient(app)
    with client.websocket_connect(prisma_url(client)) as socket:
        options = socket.receive_json()["options"]
    fields = {field["key"]: field for field in options["fields"]}
    assert set(fields) == {"mode", "bots", "difficulty", "challenge", "scoring", "target", "stack_draw2", "stack_draw4"}
    assert fields["mode"]["default"] == "clasico" and fields["mode"]["type"] == "choice"
    assert [choice["value"] for choice in fields["mode"]["choices"]] == ["clasico", "doble_cara", "sin_tregua"]
    assert fields["challenge"]["default"] is True
    assert fields["stack_draw2"]["default"] is False and fields["stack_draw4"]["default"] is False
    # Cada opción dice con qué modo tiene sentido: el panel esconde las demás.
    assert fields["stack_draw2"]["when"] == {"mode": ["clasico"]} == fields["stack_draw4"]["when"]
    assert fields["challenge"]["when"] == {"mode": ["clasico", "doble_cara"]}
    assert fields["target"]["when"] == {"scoring": [True]}
    assert "when" not in fields["bots"]


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard", "expert"])
def test_whole_games_never_show_cards_of_others(table, difficulty):
    rng = random.Random(difficulty)
    table.socket.send_json({"type": "new_game", "config": {"bots": 3, "difficulty": difficulty}})
    state = table.settle()
    for _ in range(400):
        if state["phase"] == "round_over":
            break
        state = table.request(**play_any(state, rng))
    assert state["phase"] == "round_over" and state["winner"] is not None
    for seen in table.states:
        assert set(cards_in(seen)) <= visible_to_me(seen)
        assert seen["draw_count"] + seen["discard_count"] + sum(p["count"] for p in seen["players"]) == 108
        assert all("hand" not in player for player in seen["players"])
    assert len(table.states[0]["hand"]) in (7, 9)  # 9 si la carta inicial fue una Carga +2 para mí


def test_illegal_intentions_are_rejected(table):
    assert "empezar una partida" in table.error(type="draw")
    table.socket.send_json({"type": "new_game", "config": {"bots": 2}})
    table.settle()
    session = table.session()
    session.game = rigged(["panal-1 halo-2 camaleon", "astro-1 astro-2 astro-3", "cumbre-1 cumbre-2 cumbre-3"], "panal-7")
    hand = {card.id for card in session.game.players[0].hand}
    foreign = next(i for i in range(108) if i not in hand)
    assert "no casa" in table.error(type="play", card=card_id(session.game, 0, "halo-2"))
    assert "Elige un color" in table.error(type="play", card=card_id(session.game, 0, "camaleon"))
    assert "No tienes esa carta" in table.error(type="play", card=foreign)
    assert "Mensaje inválido" in table.error(type="play", card=999)
    assert "Mensaje inválido" in table.error(type="play", card="7")
    assert "Mensaje inválido" in table.error(type="color", color="rojo")
    assert "Mensaje inválido" in table.error(type="ver_cartas")
    assert "nadie a quien pillar" in table.error(type="catch")
    assert "no ha terminado" in table.error(type="next_round")
    assert "elegir el color" not in table.error(type="pass")


def test_forgetting_to_say_last_gets_you_caught(table):
    table.socket.send_json({"type": "new_game", "config": {"bots": 1, "difficulty": "expert"}})
    table.settle()
    session = table.session()
    # Mesa preparada: tengo dos cartas y el bot (que siempre pilla) juega después.
    session.game = rigged(["panal-1 panal-2", "halo-1 halo-2"], "panal-7")
    session.game.players[0].name = "Tú"
    session.bots[1].catch_chance = 1.0
    state = table.request(type="play", card=card_id(session.game, 0, "panal-1"))
    assert any(e["kind"] == "caught" and e["seat"] == 0 for e in state["events"])
    assert len(state["hand"]) == 3


def test_saying_last_with_the_card_keeps_you_safe(table):
    table.socket.send_json({"type": "new_game", "config": {"bots": 1, "difficulty": "expert"}})
    table.settle()
    session = table.session()
    session.game = rigged(["panal-1 panal-2", "halo-1 halo-2"], "panal-7")
    session.bots[1].catch_chance = 1.0
    state = table.request(type="play", card=card_id(session.game, 0, "panal-1"), declare=True)
    assert not any(e["kind"] == "caught" for e in state["events"])
    assert len(state["hand"]) == 1


def test_i_can_catch_a_bot_that_forgets(table):
    table.socket.send_json({"type": "new_game", "config": {"bots": 1, "difficulty": "easy"}})
    table.settle()
    session = table.session()
    # Juego yo (avisando de mi última carta); el bot se queda con una y no avisa.
    session.game = rigged(["panal-3 halo-5", "panal-1 panal-2"], "panal-7")
    bot = session.bots[1]
    bot.declare_chance = 0.0
    bot.says_last = lambda view: False
    state = table.request(type="play", card=card_id(session.game, 0, "panal-3"), declare=True)
    assert state["players"][1]["vulnerable"] and state["legal"]["catch"]
    table.socket.send_json({"type": "catch"})
    state = table.receive()["state"]
    assert state["players"][1]["count"] == 3
    assert any(e["kind"] == "caught" and e["seat"] == 1 and e["target"] == 0 for e in state["events"])


def test_playing_to_points_goes_round_after_round(table):
    rng = random.Random(4)
    table.socket.send_json(
        {"type": "new_game", "config": {"bots": 1, "scoring": True, "target": 50, "difficulty": "easy"}}
    )
    state = table.settle()
    rounds = 1
    for _ in range(3000):
        if state["phase"] == "round_over":
            if state["game_over"]:
                break
            state = table.request(type="next_round")
            rounds += 1
            continue
        state = table.request(**play_any(state, rng))
    assert state["game_over"]
    assert max(player["score"] for player in state["players"]) >= 50
    assert state["round_number"] == rounds


# --- Los modos nuevos ---

from games.prisma.engine import Color, Mode, Phase  # noqa: E402

DECK = {"clasico": 108, "doble_cara": 112, "sin_tregua": 168}


@pytest.mark.parametrize("mode", ["doble_cara", "sin_tregua"])
@pytest.mark.parametrize("difficulty", ["easy", "expert"])
def test_whole_games_in_each_mode_never_show_what_is_hidden(table, mode, difficulty):
    rng = random.Random(f"{mode}{difficulty}")
    table.socket.send_json({"type": "new_game", "config": {"bots": 3, "difficulty": difficulty, "mode": mode}})
    state = table.settle()
    for _ in range(600):
        if state["phase"] == "round_over":
            break
        state = table.request(**play_any(state, rng))
    assert state["phase"] == "round_over" and state["winner"] is not None
    for seen in table.states:
        assert seen["mode"] == mode
        assert set(cards_in(seen)) <= visible_to_me(seen)
        total = seen["draw_count"] + seen["discard_count"] + seen["aside_count"] + sum(p["count"] for p in seen["players"])
        assert total == DECK[mode]
        me = seen["players"][seen["human_seat"]]
        assert me["backs"] == []  # la otra cara de mis cartas no la veo
        for player in seen["players"]:
            assert all("id" not in face for face in player["backs"])
            if mode == "doble_cara" and player["seat"] != seen["human_seat"]:
                assert len(player["backs"]) == player["count"]
            if mode == "sin_tregua":
                assert player["backs"] == []
        assert all("back" not in card for card in seen["hand"])


def test_the_house_options_only_count_in_the_classic_mode(table):
    table.socket.send_json({"type": "new_game", "config": {"bots": 1, "mode": "sin_tregua", "stack_draw2": True}})
    table.settle()
    rules = table.session().game.rules
    assert rules.mode == Mode.SIN_TREGUA and not rules.stack_draw2


def test_the_roulette_and_the_seven_over_the_wire(table):
    table.socket.send_json({"type": "new_game", "config": {"bots": 2, "mode": "sin_tregua"}})
    table.settle()
    session = table.session()
    game = rigged(["panal-7 panal-1 halo-2", "halo-1 halo-3 halo-4", "cumbre-1 cumbre-2 cumbre-3"], "panal-5", mode=Mode.SIN_TREGUA)
    session.game = game
    assert "con quién" in table.error(type="play", card=card_id(game, 0, "panal-7"))
    assert "Mensaje inválido" in table.error(type="play", card=card_id(game, 0, "panal-7"), target=9)
    theirs = {card.id for card in game.players[2].hand}
    table.socket.send_json({"type": "play", "card": card_id(game, 0, "panal-7"), "target": 2})
    state = table.receive()["state"]  # justo tras mi jugada, antes de que jueguen los bots
    assert any(event["kind"] == "swap" and event["target"] == 2 for event in state["events"])
    assert {card["id"] for card in state["hand"]} == theirs  # ahora tengo sus cartas
    assert state["players"][2]["count"] == 2  # y él, las dos que me quedaban


def test_choosing_the_colour_of_a_roulette(table):
    table.socket.send_json({"type": "new_game", "config": {"bots": 2, "mode": "sin_tregua"}})
    table.settle()
    session = table.session()
    game = rigged(["panal-1 halo-2", "halo-1 halo-3", "cumbre-1 cumbre-2"], "panal-5", mode=Mode.SIN_TREGUA)
    session.game = game
    # Me toca la Ruleta: elijo el color, y las cartas destapadas las ve todo el mundo.
    game.phase, game.turn = Phase.ROULETTE, 0
    assert "no está en juego" in table.error(type="roulette", color="brasa")
    table.socket.send_json({"type": "roulette", "color": "halo"})
    state = table.receive()["state"]
    reveal = next(event for event in state["events"] if event["kind"] == "reveal")
    assert reveal["cards"] and reveal["cards"][-1]["color"] in ("halo", Color.HALO)


def test_dark_colours_are_accepted_only_on_the_dark_side(table):
    table.socket.send_json({"type": "new_game", "config": {"bots": 1, "mode": "doble_cara"}})
    table.settle()
    session = table.session()
    session.game.phase, session.game.turn = Phase.CHOOSE_COLOR, 0
    assert "no está en juego" in table.error(type="color", color="jade")
