"""Servidor: partida completa por WebSocket, intenciones rechazadas y cartas ocultas."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from server.app import create_app
from server.protocol import NOTICE
from server.session import BOT_DELAY, HUMAN_SEAT
from test_views import cards_in, hidden_from

GUEST = "invitado-de-prueba"


@pytest.fixture
def app():
    return create_app(bot_delay=(0, 0), simulations=30, serve_frontend=False)


@pytest.fixture
def table(app):
    with TestClient(app).websocket_connect(f"/ws?guest_id={GUEST}") as socket:
        hello = socket.receive_json()
        assert hello["type"] == "hello" and hello["state"] is None
        yield Table(socket, app.state.sessions[GUEST])


class Table:
    """Cliente de prueba: envía intenciones y guarda todos los estados recibidos."""

    def __init__(self, socket, session):
        self.socket, self.session = socket, session
        self.states = []

    def send(self, **message):
        self.socket.send_json(message)

    def receive(self):
        message = self.socket.receive_json()
        if message["type"] == "state":
            self.states.append(message["state"])
        return message

    def wait_for_turn(self):
        """Lee estados hasta que le toca al humano o termina la mano."""
        while True:
            message = self.receive()
            assert message["type"] == "state", message
            state = message["state"]
            if not state["hand_in_progress"] or state["to_act_seat"] == HUMAN_SEAT:
                return state

    def request(self, **message):
        self.send(**message)
        return self.wait_for_turn()

    def error(self, **message):
        self.send(**message)
        reply = self.receive()
        assert reply["type"] == "error", reply
        return reply["message"]

    def play_hand(self, state, action="call"):
        while state["hand_in_progress"]:
            chosen = action
            # Ir all-in no siempre es legal: si el rival ya lo está, solo queda igualar.
            if action == "all_in" and not state["legal_actions"]["can_raise"]:
                chosen = "call"
            state = self.request(type="action", action=chosen)
        return state


def new_game(table, **config):
    """Empieza una partida y espera a que me toque jugar o a que acabe la mano."""
    return table.request(type="new_game", config=config)


def first_state(table, **config):
    """El estado tal como queda nada más repartir, antes de que juegue nadie."""
    table.send(type="new_game", config=config)
    return table.receive()["state"]


def can_raise(legal):
    return legal["can_raise"]


def facing_a_bet(legal):
    """Tengo algo que igualar y además puedo subir."""
    return legal["call_amount"] > 0 and legal["can_raise"]


def my_turn(table, needs=lambda legal: True, **config):
    """Empieza partidas hasta que me toca jugar en la primera mano.

    El reparto es al azar: a veces los bots se retiran antes de que me llegue el
    turno y la mano termina sin mí. Entonces se reinicia y se prueba otra vez.
    `needs` permite exigir algo más de mis acciones legales.
    """
    state = new_game(table, **config)
    for _ in range(200):
        legal = state["legal_actions"]
        if state["hand_in_progress"] and legal is not None and needs(legal):
            return state
        state = table.request(type="restart")
    raise AssertionError("No llegó ninguna mano en la que me tocara jugar")


def chips(state):
    in_pot = state["pot"] if state["hand_in_progress"] else 0
    return in_pot + sum(seat["stack"] for seat in state["seats"])


def test_connection_needs_a_guest_id(app):
    client = TestClient(app)
    for query in ("", "?guest_id=corto", "?guest_id=con espacios raros!"):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/ws{query}") as socket:
                socket.receive_json()


def test_hello_offers_the_configuration_options(app):
    with TestClient(app).websocket_connect(f"/ws?guest_id={GUEST}") as socket:
        options = socket.receive_json()["options"]
    assert options["notice"] == NOTICE == "Solo para entretenimiento. Sin dinero real."
    assert [level["id"] for level in options["levels"]] == ["easy", "medium", "hard", "expert"]
    assert options["max_bots"] == 5
    assert options["defaults"]["bots"] == 3


def test_bots_think_between_0_8_and_2_5_seconds():
    assert BOT_DELAY == (0.8, 2.5)


@pytest.mark.parametrize("bots", [1, 5])
def test_new_game_uses_the_chosen_configuration(table, bots):
    state = first_state(
        table, bots=bots, difficulty="hard", starting_stack=500, small_blind=10, big_blind=20
    )
    assert state["notice"] == NOTICE
    assert len(state["seats"]) == bots + 1
    assert state["small_blind"] == 10 and state["big_blind"] == 20
    assert chips(state) == 500 * (bots + 1)
    human, *rivals = state["seats"]
    assert human["is_human"] and human["name"] == "Tú"
    for seat in rivals:
        assert not seat["is_human"] and seat["level"] == "Difícil" and seat["style"]
    assert len({seat["name"] for seat in state["seats"]}) == bots + 1
    assert len(state["hole_cards"]) == 2
    # Solo recibo mis acciones legales cuando el turno es mío.
    assert state["hand_in_progress"] and state["to_act_seat"] is not None
    assert (state["legal_actions"] is not None) == (state["to_act_seat"] == HUMAN_SEAT)


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard", "expert"])
def test_full_game_never_leaks_hidden_cards(table, difficulty):
    """Se juegan manos enteras; ningún estado enseña cartas ajenas sin showdown ni el mazo."""
    state = new_game(
        table, bots=3, difficulty=difficulty, starting_stack=300, small_blind=10, big_blind=20
    )
    showdowns = 0

    for _ in range(40):
        first = len(table.states) - 1
        state = table.play_hand(state)
        # La mano ya terminó: el servidor no cambia nada hasta la siguiente intención.
        hidden = hidden_from(table.session.game, HUMAN_SEAT)
        for seen in table.states[first:]:
            assert not cards_in(seen) & hidden
            assert "deck" not in str(seen)
        assert chips(state) == 300 * 4

        result = state["result"]
        assert sum(result["payouts"].values()) == state["pot"]
        if result["showdown"]:
            showdowns += 1
            assert set(result["hand_names"]) == set(result["shown_hands"])
        else:
            assert all(seat["hole_cards"] is None for seat in state["seats"][1:])

        if state["human_out"] or state["game_over"]:
            break
        number = state["hand_number"]
        state = table.request(type="next_hand")
        assert state["hand_number"] == number + 1
    assert showdowns > 0


def test_before_showdown_only_the_human_cards_are_visible(table):
    state = first_state(table, bots=5)
    assert state["result"] is None
    assert state["seats"][0]["hole_cards"] == state["hole_cards"]
    assert all(seat["hole_cards"] is None for seat in state["seats"][1:])
    assert cards_in(state) == set(state["hole_cards"]) | set(state["board"])


def test_illegal_intentions_are_rejected_without_changing_the_game(table):
    assert "empezar una partida" in table.error(type="next_hand")
    assert "reiniciar" in table.error(type="restart")
    assert "Mensaje inválido" in table.error(type="new_game", config={"bots": 9})
    blinds = {"small_blind": 50, "big_blind": 10}
    assert "ciega pequeña" in table.error(type="new_game", config=blinds)

    legal = my_turn(table, facing_a_bet, bots=1)["legal_actions"]
    before = table.session.state()
    too_much, too_little = legal["max_raise_to"] + 1, legal["min_raise_to"] - 1
    assert "Monto inválido" in table.error(type="action", action="raise", amount=too_much)
    assert "Monto inválido" in table.error(type="action", action="raise", amount=too_little)
    assert "No puedes pasar" in table.error(type="action", action="check")
    assert "todavía no ha terminado" in table.error(type="next_hand")
    for bad in (
        {"type": "action", "action": "trampa"},
        {"type": "action", "action": "raise", "amount": "400"},
        {"type": "action", "action": "raise", "amount": -5},
        {"type": "ver_cartas"},
        {"type": "action", "action": "call", "seat": 1},
    ):
        assert "Mensaje inválido" in table.error(**bad)
    table.socket.send_text("esto no es JSON")
    assert table.receive()["type"] == "error"
    assert table.session.state() == before


def test_cannot_act_when_the_hand_is_over(table):
    my_turn(table, bots=1)
    state = table.request(type="action", action="fold")
    assert not state["hand_in_progress"]
    assert "No hay ninguna mano en curso" in table.error(type="action", action="call")


def test_raise_with_amount_and_all_in(table):
    state = my_turn(table, can_raise, bots=2, difficulty="easy", starting_stack=400)
    target = state["legal_actions"]["min_raise_to"]
    table.send(type="action", action="raise", amount=target)
    after = table.receive()["state"]
    assert after["seats"][0]["bet"] == target
    last = after["events"][-1]
    assert (last["kind"], last["seat"], last["action"], last["amount"]) == ("action", 0, "raise", target)

    state = after if after["to_act_seat"] == HUMAN_SEAT else table.wait_for_turn()
    state = table.play_hand(state, action="all_in")
    assert state["result"] is not None


def test_busted_human_is_offered_a_free_restart(table):
    config = dict(bots=1, difficulty="expert", starting_stack=100, small_blind=25, big_blind=50)
    state = new_game(table, **config)
    for _ in range(200):
        state = table.play_hand(state, action="all_in")
        if state["game_over"]:
            break
        state = table.request(type="next_hand")
    assert state["game_over"] and state["winner_seat"] in (0, 1)
    assert state["human_out"] == (state["winner_seat"] == 1)
    assert "reiníciala" in table.error(type="next_hand")

    state = table.request(type="restart")
    assert state["hand_number"] == 1 and not state["human_out"] and not state["game_over"]
    assert chips(state) == 200
    assert state["config"]["difficulty"] == "expert"


def test_reconnecting_with_the_same_guest_id_resumes_the_game(app):
    client = TestClient(app)
    with client.websocket_connect(f"/ws?guest_id={GUEST}") as socket:
        socket.receive_json()
        mine = new_game(Table(socket, None), bots=2)
    with client.websocket_connect(f"/ws?guest_id={GUEST}") as socket:
        resumed = socket.receive_json()["state"]
    assert resumed["hole_cards"] == mine["hole_cards"]
    assert resumed["hand_number"] == mine["hand_number"]
    with client.websocket_connect("/ws?guest_id=otro-invitado") as socket:
        assert socket.receive_json()["state"] is None
