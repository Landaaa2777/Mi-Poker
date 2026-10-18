"""Partidas en las salas: el anfitrión empieza, cada persona ve su mesa y salir es abandonar."""

import anyio
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from accounts import Cost
from server.app import create_app
from server.salas import LEFT

PASSWORD = "una clave de prueba"


@pytest.fixture
def app(tmp_path):
    # Sin pausas entre manos y con tiempo de sobra para decidir: nada se juega solo.
    return create_app(
        bot_delay=(0, 0),
        simulations=30,
        serve_frontend=False,
        database=tmp_path / "cuentas.db",
        password_cost=Cost(n=16, r=1, p=1),
        turn_seconds=30,
        pause_seconds=0,
    )


@pytest.fixture
def portal():
    with anyio.from_thread.start_blocking_portal() as portal:
        yield portal


@pytest.fixture
def browser(app, portal):
    def open_browser(name):
        client = TestClient(app)
        client.portal = portal
        assert client.post("/api/register", json={"username": name, "password": PASSWORD}).status_code == 201
        return client

    return open_browser


def create(client, game="poker"):
    return client.post("/api/salas", json={"game": game}).json()["code"]


def wait_for(socket, kind, check=lambda value: True, limit=200):
    """Lee mensajes hasta el primero de ese tipo que cumpla `check`, y devuelve su contenido."""
    for _ in range(limit):
        message = socket.receive_json()
        if message["type"] == kind:
            value = message.get(kind, message.get("message"))
            if check(value):
                return value
    raise AssertionError(f"No llegó ningún «{kind}» así")


def table(app, code):
    return app.state.salas.get(code).session


@pytest.fixture
def two(browser):
    """Ana (anfitriona) y Luis en una sala de poker, los dos conectados."""
    ana, luis = browser("Ana"), browser("Luis")
    code = create(ana)
    luis.post(f"/api/salas/{code}")
    return ana, luis, code


def test_the_host_starts_and_each_person_sees_their_own_table(app, two):
    ana, luis, code = two
    with ana.websocket_connect(f"/ws/sala/{code}") as a, luis.websocket_connect(f"/ws/sala/{code}") as b:
        luis_view = wait_for(b, "sala")
        assert luis_view["can_start"] and not luis_view["game_over"]
        b.send_json({"type": "start"})
        assert wait_for(b, "error") == "Solo el anfitrión puede empezar la partida"
        a.send_json({"type": "start"})
        for socket, name in ((a, "Ana"), (b, "Luis")):
            assert wait_for(socket, "sala", lambda sala: sala["status"] == "playing")
            state = wait_for(socket, "state")
            me = state["human_seat"]
            assert state["seats"][me]["name"] == name and state["seats"][me]["is_human"]
            other = state["seats"][1 - me]
            assert other["person"] and not other["is_human"] and other["hole_cards"] is None
            assert len(state["hole_cards"]) == 2 and state["balance"] == 10_000
        # Juega quien tiene el turno, y los dos ven la jugada.
        session = table(app, code)
        first = session.game.hand.to_act.seat
        sockets = {session.seat_of[1]: a, session.seat_of[2]: b}
        sockets[first].send_json({"type": "action", "action": "call"})
        for socket in (a, b):
            wait_for(socket, "state", lambda state: state["to_act_seat"] != first)
        sockets[first].send_json({"type": "action", "action": "call"})
        assert wait_for(sockets[first], "error") == "No es tu turno"
        sockets[first].send_json({"type": "dance"})
        assert "inválido" in wait_for(sockets[first], "error")


def test_starting_needs_two_people_and_enough_chips(app, browser):
    ana, luis = browser("Ana"), browser("Luis")
    code = create(ana)
    with ana.websocket_connect(f"/ws/sala/{code}") as a:
        wait_for(a, "sala")
        a.send_json({"type": "start"})
        assert wait_for(a, "error") == "Hacen falta al menos dos personas para empezar"
        luis.post(f"/api/salas/{code}")
        store = app.state.accounts
        store.add_chips(store.authenticate("Luis", PASSWORD), -9_500)  # a Luis le quedan 500
        a.send_json({"type": "start"})
        assert wait_for(a, "error") == "A Luis no le llegan las fichas: tiene 500 libres y la mesa pide 1000"
        a.send_json({"type": "configure", "options": {"starting_stack": 500}})
        a.send_json({"type": "start"})
        assert wait_for(a, "sala", lambda sala: sala["status"] == "playing")


def test_nobody_joins_once_playing_but_members_come_back(app, browser, two):
    ana, luis, code = two
    with ana.websocket_connect(f"/ws/sala/{code}") as a:
        a.send_json({"type": "start"})
        wait_for(a, "sala", lambda sala: sala["status"] == "playing")
        late = browser("Eva").post(f"/api/salas/{code}")
        assert late.status_code == 409 and late.json() == {"message": "La partida de esta sala ya ha empezado"}
        # Luis no estaba conectado: al abrir el enlace, vuelve a su sitio y ve su mesa.
        assert luis.post(f"/api/salas/{code}").status_code == 200
        with luis.websocket_connect(f"/ws/sala/{code}") as b:
            assert wait_for(b, "sala")["status"] == "playing"
            state = wait_for(b, "state")
            assert state["seats"][state["human_seat"]]["name"] == "Luis"


def test_leaving_a_game_is_abandoning_it(app, browser, two):
    ana, luis, code = two
    with ana.websocket_connect(f"/ws/sala/{code}") as a:
        a.send_json({"type": "start"})
        wait_for(a, "sala", lambda sala: sala["status"] == "playing")
        with luis.websocket_connect(f"/ws/sala/{code}") as b:
            wait_for(b, "state")
            b.send_json({"type": "leave"})
            with pytest.raises(WebSocketDisconnect) as closed:
                while True:
                    b.receive_json()
            assert closed.value.code == LEFT
        # Sin rival, la partida termina y la sala vuelve a la espera, con la mesa final a la vista.
        sala = wait_for(a, "sala", lambda sala: sala["status"] == "waiting")
        assert sala["game_over"] and [member["name"] for member in sala["members"]] == ["Ana"]
        session = table(app, code)
        assert session.finished and session.game.players[session.seat_of[2]].stack == 0
        assert luis.get("/api/salas/mia").json() == {"sala": None}
        # Luis perdió lo que llevaba apostado en la mano (como mucho, la ciega grande).
        assert 9_990 <= luis.get("/api/me").json()["user"]["balance"] <= 10_000
        # Otra partida: entra alguien nuevo y la anfitriona vuelve a empezar.
        assert browser("Eva").post(f"/api/salas/{code}").status_code == 200
        a.send_json({"type": "start"})
        assert wait_for(a, "sala", lambda sala: sala["status"] == "playing")
        assert table(app, code) is not session


def test_chips_seated_in_a_sala_cannot_go_to_a_bot_table(app, two):
    ana, luis, code = two
    with ana.websocket_connect(f"/ws/sala/{code}") as a:
        a.send_json({"type": "configure", "options": {"starting_stack": 6000}})
        a.send_json({"type": "start"})
        wait_for(a, "sala", lambda sala: sala["status"] == "playing")
        partida = ana.post("/api/partidas", json={"game": "poker"}).json()["partida_id"]
        with ana.websocket_connect(f"/ws/poker/{partida}") as bots:
            assert bots.receive_json()["elsewhere"] == 6000


def test_hands_played_in_salas_count_as_with_friends(app, two):
    ana, luis, code = two
    with ana.websocket_connect(f"/ws/sala/{code}") as a, luis.websocket_connect(f"/ws/sala/{code}") as b:
        a.send_json({"type": "start"})
        session = wait_for(a, "state") and table(app, code)
        sockets = {session.seat_of[1]: a, session.seat_of[2]: b}
        sockets[session.game.hand.to_act.seat].send_json({"type": "action", "action": "fold"})
        wait_for(a, "state", lambda state: state["hand_number"] == 2)
    for client in (ana, luis):
        levels = client.get("/api/profile").json()["stats"]["levels"]
        assert [(level["difficulty"], level["name"], level["hands_played"]) for level in levels] == [
            ("friends", "Con amigos", 1)
        ]


def test_blackjack_and_prisma_are_played_in_salas_too(app, browser):
    ana, luis = browser("Ana"), browser("Luis")
    for game in ("blackjack", "prisma"):
        code = create(ana, game)
        luis.post(f"/api/salas/{code}")
        with ana.websocket_connect(f"/ws/sala/{code}") as a, luis.websocket_connect(f"/ws/sala/{code}") as b:
            a.send_json({"type": "start"})
            if game == "blackjack":
                wait_for(a, "state", lambda state: state["phase"] == "betting")
                a.send_json({"type": "bet", "amount": 50})
                b.send_json({"type": "bet", "amount": 50})
                state = wait_for(b, "state", lambda state: state["round_number"] == 1)
                assert state["dealer"]["hole_hidden"] or state["phase"] == "complete"
            else:
                state = wait_for(b, "state")
                assert len(state["hand"]) >= 7 and state["players"][state["human_seat"]]["name"] == "Luis"
            a.send_json({"type": "leave"})
            b.send_json({"type": "leave"})
            for socket in (a, b):
                with pytest.raises(WebSocketDisconnect):
                    while True:
                        socket.receive_json()
