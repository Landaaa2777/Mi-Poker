"""Servidor: una mesa de blackjack por WebSocket, de principio a fin."""

import pytest
from fastapi.testclient import TestClient

from accounts import STARTING_BALANCE, Cost
from server.app import create_app

GUEST = "invitado-de-prueba"
JOKER = {"username": "Joker", "password": "una clave de prueba"}


def blackjack_url(client, guest_id=GUEST):
    body = {"game": "blackjack"} if guest_id is None else {"game": "blackjack", "guest_id": guest_id}
    response = client.post("/api/partidas", json=body)
    assert response.status_code == 200, response.text
    query = "" if guest_id is None else f"?guest_id={guest_id}"
    return f"/ws/blackjack/{response.json()['partida_id']}{query}"


@pytest.fixture
def app(tmp_path):
    return create_app(
        bot_delay=(0, 0),
        serve_frontend=False,
        database=tmp_path / "cuentas.db",
        password_cost=Cost(n=16, r=1, p=1),
        require_account=False,  # estos tests juegan como invitado
    )


class Table:
    """Cliente de prueba: manda intenciones y guarda los estados que llegan."""

    def __init__(self, socket):
        self.socket = socket
        self.states = []

    def receive(self):
        message = self.socket.receive_json()
        if message["type"] == "state":
            self.states.append(message["state"])
        return message

    def settle(self):
        """Lee estados hasta que me toca decidir algo o termina la ronda."""
        while True:
            message = self.receive()
            assert message["type"] == "state", message
            state = message["state"]
            if (
                state["phase"] in ("complete", "betting")
                or state["legal_actions"]
                or state["insurance_offered"]
            ):
                return state

    def request(self, **message):
        self.socket.send_json(message)
        return self.settle()

    def error(self, **message):
        self.socket.send_json(message)
        reply = self.receive()
        assert reply["type"] == "error", reply
        return reply["message"]

    def play_round(self, bet=10, action="stand"):
        """Apuesta y juega la ronda entera: sin seguro, y siempre la misma jugada."""
        state = self.request(type="bet", amount=bet)
        while state["phase"] not in ("complete", "betting"):
            if state["insurance_offered"]:
                state = self.request(type="insurance", take=False)
            else:
                chosen = action if action in state["legal_actions"] else "stand"
                state = self.request(type="action", action=chosen)
        return state


@pytest.fixture
def table(app):
    client = TestClient(app)
    with client.websocket_connect(blackjack_url(client)) as socket:
        hello = socket.receive_json()
        assert hello["type"] == "hello" and hello["game"] == "blackjack" and hello["state"] is None
        yield Table(socket)


def me(state):
    return state["seats"][state["human_seat"]]


def test_the_hello_explains_the_options(app):
    client = TestClient(app)
    with client.websocket_connect(blackjack_url(client)) as socket:
        options = socket.receive_json()["options"]
    assert options["max_bots"] == 4
    fields = {field["key"]: field for field in options["fields"]}
    assert set(fields) == {
        "bots", "difficulty", "starting_stack", "min_bet", "max_bet", "dealer_hits_soft_17", "surrender"
    }
    assert fields["surrender"]["type"] == "toggle" and fields["surrender"]["default"] is False
    assert fields["min_bet"]["step"] == 10


def test_sitting_down_with_the_chosen_table(table):
    table.socket.send_json(
        {"type": "new_game", "config": {"bots": 4, "difficulty": "hard", "starting_stack": 700}}
    )
    state = table.receive()["state"]
    assert state["phase"] == "betting" and state["human_seat"] == 2
    assert len(state["seats"]) == 5
    assert me(state)["is_human"] and me(state)["name"] == "Tú" and me(state)["stack"] == 700
    bots = [seat for seat in state["seats"] if not seat["is_human"]]
    assert all(seat["level"] == "Difícil" for seat in bots)
    assert len({seat["name"] for seat in state["seats"]}) == 5


def test_whole_rounds_never_show_the_hole_card_early(table):
    table.socket.send_json({"type": "new_game", "config": {"bots": 3, "starting_stack": 2000}})
    table.receive()
    for _ in range(25):
        first = len(table.states)
        final = table.play_round(bet=20, action="hit")
        for seen in table.states[first:]:
            dealer = seen["dealer"]
            if dealer["hole_hidden"]:
                assert dealer["cards"][1] is None and len(dealer["cards"]) == 2
            assert all(event["card"] is None for event in seen["events"] if event["kind"] == "hole_card")
            assert "shoe" not in seen or set(seen["shoe"]) == {"remaining", "total", "cut_reached"}
        assert final["phase"] == "complete" and not final["dealer"]["hole_hidden"]
        assert all(card is not None for card in final["dealer"]["cards"])
        if final["human_out"]:
            break


def test_chips_move_with_each_round(table):
    table.socket.send_json({"type": "new_game", "config": {"bots": 0, "starting_stack": 500}})
    table.receive()
    stack = 500
    for _ in range(10):
        final = table.play_round(bet=50)
        hands = me(final)["hands"]
        stack += sum(hand["payout"] - hand["bet"] for hand in hands)
        assert me(final)["stack"] == stack
        if final["human_out"]:
            break


def test_illegal_intentions_are_rejected(table):
    assert "sentarse" in table.error(type="bet", amount=10)
    assert "reiniciar" in table.error(type="restart")
    table.socket.send_json({"type": "new_game", "config": {"bots": 1}})
    table.receive()
    assert "entre 10 y 500" in table.error(type="bet", amount=5)
    assert "10 en 10" in table.error(type="bet", amount=25)
    assert "Mensaje inválido" in table.error(type="new_game", config={"bots": 9})
    assert "mínima no puede superar" in table.error(type="new_game", config={"min_bet": 600})
    for bad in (
        {"type": "action", "action": "ver_carta_tapada"},
        {"type": "bet", "amount": "100"},
        {"type": "insurance", "take": "sí"},
        {"type": "trampa"},
    ):
        assert "Mensaje inválido" in table.error(**bad)
    assert "momento de jugar" in table.error(type="action", action="hit")
    assert "seguro" in table.error(type="insurance", take=True)


def test_busted_human_can_restart(table):
    config = {"bots": 0, "starting_stack": 20, "min_bet": 10, "max_bet": 20}
    table.socket.send_json({"type": "new_game", "config": config})
    table.receive()
    final = None
    for _ in range(300):
        final = table.play_round(bet=10, action="hit")
        if final["human_out"]:
            break
        if me(final)["stack"] >= 40:  # si gano demasiado, empiezo otra vez para no eternizarme
            table.socket.send_json({"type": "restart"})
            table.receive()
    assert final["human_out"]
    assert "fichas" in table.error(type="bet", amount=10)
    table.socket.send_json({"type": "restart"})
    fresh = table.receive()["state"]
    assert me(fresh)["stack"] == 20 and not fresh["human_out"]


# --- Con cuenta: el saldo es el mismo que el del poker ---


@pytest.fixture
def joker(app):
    client = TestClient(app)
    assert client.post("/api/register", json=JOKER).status_code == 201
    return client


def balance(client):
    return client.get("/api/me").json()["user"]["balance"]


def test_each_round_moves_the_account_balance(joker):
    with joker.websocket_connect(blackjack_url(joker, None)) as socket:
        socket.receive_json()
        table = Table(socket)
        socket.send_json({"type": "new_game", "config": {"bots": 1, "starting_stack": 1000}})
        assert table.receive()["state"]["balance"] == STARTING_BALANCE
        for _ in range(8):
            final = table.play_round(bet=100)
            assert final["balance"] == STARTING_BALANCE - 1000 + me(final)["stack"]
            assert balance(joker) == final["balance"]


def test_leaving_a_round_halfway_costs_the_bet(joker):
    with joker.websocket_connect(blackjack_url(joker, None)) as socket:
        socket.receive_json()
        table = Table(socket)
        socket.send_json({"type": "new_game", "config": {"bots": 0, "starting_stack": 1000}})
        table.receive()
        for _ in range(50):
            state = table.request(type="bet", amount=100)
            if state["insurance_offered"]:
                state = table.request(type="insurance", take=False)
            if state["phase"] == "playing":
                break
            # La ronda terminó sola (blackjack de alguien): otra.
        assert state["phase"] == "playing"
        before = balance(joker)
        socket.send_json({"type": "restart"})
        fresh = table.receive()["state"]
    assert fresh["balance"] == before - 100 == balance(joker)


def test_chips_seated_at_poker_cannot_also_go_to_blackjack(joker):
    poker = joker.post("/api/partidas", json={"game": "poker"}).json()["partida_id"]
    with joker.websocket_connect(f"/ws/poker/{poker}") as socket:
        socket.receive_json()
        socket.send_json({"type": "new_game", "config": {"bots": 1, "starting_stack": 6000}})
        socket.receive_json()
    with joker.websocket_connect(blackjack_url(joker, None)) as socket:
        assert socket.receive_json()["elsewhere"] == 6000  # el "hello" ya lo avisa
        table = Table(socket)
        message = table.error(type="new_game", config={"bots": 1, "starting_stack": 5000})
        assert "hasta 4000" in message
        socket.send_json({"type": "new_game", "config": {"bots": 1, "starting_stack": 4000}})
        assert me(table.receive()["state"])["stack"] == 4000
    # Y al revés: con 4000 en el blackjack, el poker no puede rehacer su mesa con 10000.
    with joker.websocket_connect(f"/ws/poker/{poker}") as socket:
        socket.receive_json()
        socket.send_json({"type": "new_game", "config": {"bots": 1, "starting_stack": 10_000}})
        reply = socket.receive_json()
    assert reply["type"] == "error" and "hasta" in reply["message"]


def test_the_hub_sees_the_blackjack_partida(joker):
    with joker.websocket_connect(blackjack_url(joker, None)) as socket:
        socket.receive_json()
        socket.send_json({"type": "new_game", "config": {"bots": 0}})
        socket.receive_json()
    partidas = joker.get("/api/partidas").json()["partidas"]
    assert [(p["game"], p["in_progress"]) for p in partidas] == [("blackjack", True)]
