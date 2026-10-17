"""Partidas: una por identidad y juego, con un id secreto que solo vale para su dueño."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from accounts import Cost
from server.app import create_app
from server.partidas import MAX_PARTIDAS, Partidas, owner_key

GUEST = "invitado-de-prueba"
JOKER = {"username": "Joker", "password": "una clave de prueba"}


class FakeSession:
    """Una partida de mentira: solo sabe cuántas fichas tiene sentadas."""

    def __init__(self, seated=0):
        self.seated = seated
        self.closed = False
        self.in_progress = False

    def seated_chips(self):
        return self.seated

    def close(self):
        self.closed = True


@pytest.fixture
def app(tmp_path):
    return create_app(
        bot_delay=(0, 0),
        simulations=30,
        serve_frontend=False,
        database=tmp_path / "cuentas.db",
        password_cost=Cost(n=16, r=1, p=1),
    )


@pytest.fixture
def client(app):
    return TestClient(app)


def open_poker(client, guest_id=GUEST):
    body = {"game": "poker"} if guest_id is None else {"game": "poker", "guest_id": guest_id}
    return client.post("/api/partidas", json=body)


# --- El almacén de partidas ---


def test_the_owner_is_the_account_or_else_the_guest():
    class User:
        id = 7

    assert owner_key(User(), GUEST) == "user:7"  # con cuenta, da igual el invitado
    assert owner_key(None, GUEST) == GUEST
    for bad in ("", "corto", "con espacios raros!", "user:7", None):
        assert owner_key(None, bad) is None


def test_each_owner_has_one_partida_per_game():
    partidas = Partidas()
    poker = partidas.open("ana", "poker", lambda pid: FakeSession())
    assert partidas.open("ana", "poker", lambda pid: FakeSession()) is poker
    blackjack = partidas.open("ana", "blackjack", lambda pid: FakeSession())
    other = partidas.open("luis", "poker", lambda pid: FakeSession())
    assert len({poker.id, blackjack.id, other.id}) == 3
    assert len(poker.id) >= 20  # largo y al azar: no se puede adivinar
    assert partidas.get(poker.id) is poker and partidas.find("ana", "blackjack") is blackjack
    assert {p.game for p in partidas.of_owner("ana")} == {"poker", "blackjack"}
    assert len(partidas) == 3


def test_chips_seated_elsewhere_are_counted_but_not_here():
    partidas = Partidas()
    poker = partidas.open("ana", "poker", lambda pid: FakeSession(seated=1_500))
    blackjack = partidas.open("ana", "blackjack", lambda pid: FakeSession(seated=400))
    partidas.open("luis", "poker", lambda pid: FakeSession(seated=9_999))
    assert partidas.chips_elsewhere("ana", poker.id) == 400
    assert partidas.chips_elsewhere("ana", blackjack.id) == 1_500
    assert partidas.chips_elsewhere("luis", "otra") == 9_999


def test_the_oldest_partida_is_dropped_when_there_are_too_many():
    partidas = Partidas(limit=2)
    first = partidas.open("a", "poker", lambda pid: FakeSession())
    partidas.open("b", "poker", lambda pid: FakeSession())
    partidas.open("c", "poker", lambda pid: FakeSession())
    assert len(partidas) == 2 and partidas.get(first.id) is None
    assert first.session.closed  # sus bots dejan de jugar
    assert partidas.find("a", "poker") is None
    assert MAX_PARTIDAS == 500


# --- Por HTTP ---


def test_asking_twice_gives_the_same_partida(client):
    first = open_poker(client).json()
    second = open_poker(client).json()
    assert first == second == {"game": "poker", "partida_id": first["partida_id"], "in_progress": False}


def test_unknown_and_coming_soon_games_have_no_partida(client):
    unknown = client.post("/api/partidas", json={"game": "ajedrez", "guest_id": GUEST})
    assert unknown.status_code == 404
    soon = client.post("/api/partidas", json={"game": "minijuegos", "guest_id": GUEST})
    assert soon.status_code == 409 and "todavía" in soon.json()["message"]


def test_malformed_requests_are_rejected(client):
    for body in ({}, {"game": 7, "guest_id": GUEST}, {"game": "poker", "guest_id": GUEST, "x": 1}):
        assert client.post("/api/partidas", json=body).status_code == 422


def test_my_partidas_say_whether_they_are_in_progress(client):
    assert client.get(f"/api/partidas?guest_id={GUEST}").json() == {"partidas": []}
    partida = open_poker(client).json()
    with client.websocket_connect(f"/ws/poker/{partida['partida_id']}?guest_id={GUEST}") as socket:
        socket.receive_json()
        socket.send_json({"type": "new_game", "config": {"bots": 1}})
        socket.receive_json()
    mine = client.get(f"/api/partidas?guest_id={GUEST}").json()["partidas"]
    assert mine == [{"game": "poker", "partida_id": partida["partida_id"], "in_progress": True}]
    # Otro invitado no ve las mías, y sin identidad no hay nada que ver.
    assert client.get("/api/partidas?guest_id=otro-invitado").json() == {"partidas": []}
    assert client.get("/api/partidas").json() == {"partidas": []}


def test_an_account_and_its_guest_have_different_partidas(client):
    as_guest = open_poker(client).json()["partida_id"]
    client.post("/api/register", json=JOKER)
    as_joker = open_poker(client).json()["partida_id"]
    assert as_guest != as_joker
    assert open_poker(client, None).json()["partida_id"] == as_joker  # con cuenta no hace falta invitado


# --- El WebSocket de cada partida ---


def test_a_partida_only_opens_for_its_owner_and_its_game(client):
    partida = open_poker(client).json()["partida_id"]
    good = f"/ws/poker/{partida}?guest_id={GUEST}"
    with client.websocket_connect(good) as socket:
        hello = socket.receive_json()
    assert hello["type"] == "hello" and hello["game"] == "poker"
    for wrong in (
        f"/ws/poker/{partida}?guest_id=otro-invitado",  # no es el dueño
        f"/ws/blackjack/{partida}?guest_id={GUEST}",  # no es de ese juego
        f"/ws/poker/{partida}",  # sin identidad
        f"/ws/poker/no-existe?guest_id={GUEST}",
    ):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(wrong) as socket:
                socket.receive_json()


def test_a_stolen_partida_id_is_useless_to_someone_else(app, client):
    partida = open_poker(client).json()["partida_id"]
    thief = TestClient(app)
    thief.post("/api/register", json=JOKER)
    with pytest.raises(WebSocketDisconnect):
        with thief.websocket_connect(f"/ws/poker/{partida}?guest_id={GUEST}") as socket:
            socket.receive_json()
