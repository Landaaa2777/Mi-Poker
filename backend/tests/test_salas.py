"""Salas con amigos: crear, entrar con el código, sala de espera en tiempo real, anfitrión y salir."""

import asyncio

import anyio
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from accounts import Cost, User
from games.registry import find_game
from server.app import create_app
from server.salas import (
    CODE_ALPHABET,
    CODE_LENGTH,
    IDLE_SECONDS,
    LEFT,
    SalaError,
    Salas,
    Viewer,
    new_code,
    normalize_code,
)

PASSWORD = "una clave de prueba"
POKER = find_game("poker")
BLACKJACK = find_game("blackjack")


# --- Ayudantes ---


class Clock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


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
def portal():
    # Un solo bucle de eventos para todos los navegadores de un test, como en el
    # servidor de verdad: así los avisos de una sala llegan de unos a otros.
    with anyio.from_thread.start_blocking_portal() as portal:
        yield portal


@pytest.fixture
def browser(app, portal):
    """Abre un navegador; con nombre, además crea esa cuenta y entra con ella."""

    def open_browser(name=None):
        client = TestClient(app)
        client.portal = portal
        if name:
            response = client.post("/api/register", json={"username": name, "password": PASSWORD})
            assert response.status_code == 201
        return client

    return open_browser


def create(client, game="poker"):
    response = client.post("/api/salas", json={"game": game})
    assert response.status_code == 201, response.text
    return response.json()["code"]


def join(client, code):
    return client.post(f"/api/salas/{code}")


def view(socket):
    """El siguiente aviso de la sala que llega por el WebSocket."""
    message = socket.receive_json()
    assert message["type"] == "sala", message
    return message["sala"]


def who(sala):
    """Quién está, con su estado: {"Ana": "conectada", ...}."""
    return {m["name"]: "conectada" if m["connected"] else "desconectada" for m in sala["members"]}


def close_tab(socket):
    """Cierra la conexión como lo haría una pestaña al cerrarse.

    (Al salir del `with`, el cliente de pruebas además cancela la tarea del
    servidor; con un navegador de verdad eso no pasa, así que se cierra antes.)
    """
    socket.close()


def refused(client, url, **headers):
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(url, headers=headers) as socket:
            socket.receive_json()
    return closed.value.code


# --- Códigos ---


def test_codes_are_short_unambiguous_and_hard_to_guess():
    codes = {new_code(lambda code: False) for _ in range(300)}
    assert len(codes) == 300  # al azar: no se repiten
    for code in codes:
        assert len(code) == CODE_LENGTH == 6 and set(code) <= set(CODE_ALPHABET)
    assert not set("0O1IL") & set(CODE_ALPHABET)  # nada que se confunda al leerlo
    assert len(CODE_ALPHABET) ** CODE_LENGTH > 800_000_000


def test_a_taken_code_is_never_given_twice():
    asked = []

    def taken(code):
        asked.append(code)
        return len(asked) < 3  # los dos primeros que salen ya están en uso

    assert new_code(taken) == asked[-1] and len(asked) == 3


def test_typed_codes_are_forgiving_but_strict():
    assert normalize_code(" k7p-2qx ") == "K7P2QX"
    assert normalize_code("K7P 2QX") == "K7P2QX"
    for wrong in ("K7P2Q", "K7P2QXX", "K7P2Q0", "K7P2QI", "", "../../x"):
        assert normalize_code(wrong) is None


# --- El almacén de salas ---


def test_the_host_creates_and_people_have_priority_over_bots():
    salas = Salas()
    ana, luis = User(1, "Ana"), User(2, "Luis")
    sala = asyncio.run(salas.create(POKER, ana))
    assert sala.host_id == ana.id and list(sala.members) == [ana.id]
    sala.configure(ana.id, POKER, {"bots": 5})  # Ana y 5 bots: la mesa llena
    asyncio.run(salas.join(sala.code.lower(), luis))
    assert sala.options.bots == 4  # Luis entra y sobra un bot
    assert salas.of_user(luis.id) is sala


def test_an_idle_sala_closes_on_its_own():
    clock = Clock()
    salas = Salas(clock=clock)
    quiet = asyncio.run(salas.create(POKER, User(1, "Ana")))
    busy = asyncio.run(salas.create(POKER, User(2, "Luis")))

    async def nothing(*_):
        return None

    salas.connect(busy, Viewer(2, nothing, nothing, nothing))
    clock.now += IDLE_SECONDS + 1
    salas.sweep()
    assert salas.get(quiet.code) is None  # nadie conectado en media hora: se cierra
    assert salas.get(busy.code) is busy  # con alguien conectado, sigue


def test_the_sala_limit_is_respected():
    salas = Salas(limit=2)
    asyncio.run(salas.create(POKER, User(1, "Ana")))
    asyncio.run(salas.create(POKER, User(2, "Luis")))
    with pytest.raises(SalaError, match="demasiadas salas"):
        asyncio.run(salas.create(POKER, User(3, "Eva")))


# --- Por HTTP ---


def test_creating_a_sala_needs_an_account_and_our_own_page(browser):
    guest = browser()
    assert guest.post("/api/salas", json={"game": "poker"}).status_code == 401
    ana = browser("Ana")
    foreign = {"Origin": "http://otra-web.example"}
    assert ana.post("/api/salas", json={"game": "poker"}, headers=foreign).status_code == 403
    assert ana.post("/api/salas", json={"game": "ajedrez"}).status_code == 404
    soon = ana.post("/api/salas", json={"game": "salas"})
    assert soon.status_code == 409 and "no se puede jugar en una sala" in soon.json()["message"]
    for body in ({}, {"game": 7}, {"game": "poker", "x": 1}):
        assert ana.post("/api/salas", json=body).status_code == 422


def test_friends_join_with_the_code_or_the_link(browser):
    ana, luis = browser("Ana"), browser("Luis")
    code = create(ana)
    assert len(code) == 6
    response = join(luis, code.lower())  # escrito a mano, en minúsculas
    assert response.status_code == 200
    assert response.json() == {"code": code, "game": "poker", "status": "waiting"}
    for client in (ana, luis):
        assert client.get("/api/salas/mia").json() == {"sala": response.json()}
    assert join(luis, code).status_code == 200  # volver a entrar no cambia nada


def test_joining_needs_an_account_and_a_real_code(browser):
    ana = browser("Ana")
    code = create(ana)
    assert join(browser(), code).status_code == 401
    luis = browser("Luis")
    missing = join(luis, "ZZZZZZ" if code != "ZZZZZZ" else "YYYYYY")
    assert missing.status_code == 404 and missing.json() == {"message": "No hay ninguna sala con ese código"}
    assert join(luis, "no-es-un-codigo").status_code == 404
    assert join(luis, code).status_code == 200


def test_guessing_codes_is_slowed_down(browser):
    ana, luis = browser("Ana"), browser("Luis")
    code = create(ana)
    wrong = "ZZZZZZ" if code != "ZZZZZZ" else "YYYYYY"
    for _ in range(10):
        assert join(luis, wrong).status_code == 404
    blocked = join(luis, code)  # ni siquiera con el bueno, hasta que pase el rato
    assert blocked.status_code == 429 and "Espera" in blocked.json()["message"]
    assert int(blocked.headers["Retry-After"]) > 0


def test_a_full_sala_lets_nobody_else_in(browser):
    host = browser("Anfitriona")
    code = create(host, "blackjack")  # el blackjack es de 5 como mucho
    for name in ("Uno", "Dos", "Tres", "Cuatro"):
        assert join(browser(name), code).status_code == 200
    full = join(browser("Cinco"), code)
    assert full.status_code == 409 and full.json() == {"message": "La sala está llena"}


def test_each_person_is_in_one_sala_at_a_time(browser):
    ana, luis = browser("Ana"), browser("Luis")
    first = create(ana)
    join(luis, first)
    second = create(ana)  # Ana se va a otra sala: deja la primera, y Luis pasa a llevarla
    assert ana.get("/api/salas/mia").json()["sala"]["code"] == second
    third = create(browser("Eva"))
    join(luis, third)  # Luis también se va: la primera se queda vacía y se cierra
    assert join(browser("Otro"), first).status_code == 404


def test_leaving_by_http(browser):
    ana, luis = browser("Ana"), browser("Luis")
    code = create(ana)
    join(luis, code)
    assert luis.post(f"/api/salas/{code}/salir").json() == {"sala": None}
    assert luis.get("/api/salas/mia").json() == {"sala": None}
    assert luis.post(f"/api/salas/{code}/salir").status_code == 404  # ya no está
    assert ana.post(f"/api/salas/{code}/salir", headers={"Origin": "http://otra-web.example"}).status_code == 403


# --- La sala de espera, en tiempo real ---


def test_the_waiting_room_updates_in_real_time(browser):
    ana, luis = browser("Ana"), browser("Luis")
    code = create(ana)
    with ana.websocket_connect(f"/ws/sala/{code}") as ana_socket:
        sala = view(ana_socket)
        assert sala["code"] == code and sala["game"] == "poker" and sala["status"] == "waiting"
        assert sala["you"] == "Ana" and sala["host"] == "Ana" and who(sala) == {"Ana": "conectada"}
        assert (sala["min_people"], sala["max_people"]) == (2, 6) and not sala["can_start"]
        assert "player_name" not in sala["options"] and sala["options"]["bots"] == 0
        assert [field["key"] for field in sala["fields"]][0] == "bots"

        join(luis, code)  # Ana lo ve en el momento, aunque Luis aún no ha abierto la sala
        assert who(view(ana_socket)) == {"Ana": "conectada", "Luis": "desconectada"}
        with luis.websocket_connect(f"/ws/sala/{code}") as luis_socket:
            mine = view(luis_socket)
            assert mine["you"] == "Luis" and mine["host"] == "Ana" and mine["can_start"]
            assert who(view(ana_socket)) == {"Ana": "conectada", "Luis": "conectada"}
            # Luis cierra la pestaña: no sale de la sala, solo se desconecta.
            close_tab(luis_socket)
            assert who(view(ana_socket)) == {"Ana": "conectada", "Luis": "desconectada"}
    assert join(luis, code).status_code == 200  # y puede volver con el mismo enlace


def test_only_members_can_watch_a_sala(browser):
    ana = browser("Ana")
    code = create(ana)
    assert refused(browser(), f"/ws/sala/{code}") == 4401  # sin cuenta
    assert refused(browser("Curioso"), f"/ws/sala/{code}") == 4404  # no es de la sala
    assert refused(browser("Curiosa"), "/ws/sala/ZZZZZZ") == 4404  # ni se sabe si existe
    assert refused(ana, f"/ws/sala/{code}", Origin="http://otra-web.example") == 4403


def test_only_the_host_changes_the_options(browser):
    ana, luis = browser("Ana"), browser("Luis")
    code = create(ana)
    join(luis, code)
    with ana.websocket_connect(f"/ws/sala/{code}") as ana_socket, luis.websocket_connect(
        f"/ws/sala/{code}"
    ) as luis_socket:
        for socket in (ana_socket, ana_socket, luis_socket):
            view(socket)  # las llegadas de los dos

        luis_socket.send_json({"type": "configure", "options": {"bots": 1}})
        assert luis_socket.receive_json() == {
            "type": "error",
            "message": "Solo el anfitrión puede cambiar las opciones",
        }

        ana_socket.send_json({"type": "configure", "options": {"bots": 2, "starting_stack": 2000}})
        for socket in (ana_socket, luis_socket):
            options = view(socket)["options"]
            assert options["bots"] == 2 and options["starting_stack"] == 2000

        ana_socket.send_json({"type": "configure", "options": {"bots": 5}})  # 2 personas + 5 > 6
        assert "como mucho 4 bots" in ana_socket.receive_json()["message"]
        ana_socket.send_json({"type": "configure", "options": {"small_blind": 50, "big_blind": 10}})
        assert ana_socket.receive_json()["type"] == "error"
        ana_socket.send_json({"type": "configure", "options": {"color": "rojo"}})
        assert ana_socket.receive_json()["type"] == "error"

        # Otro juego: sus opciones empiezan en las de por defecto.
        ana_socket.send_json({"type": "configure", "game": "blackjack", "options": {}})
        for socket in (ana_socket, luis_socket):
            sala = view(socket)
            assert sala["game"] == "blackjack" and sala["max_people"] == 5
            assert sala["options"]["min_bet"] == 10
        ana_socket.send_json({"type": "configure", "game": "ajedrez", "options": {}})
        assert ana_socket.receive_json() == {"type": "error", "message": "Ese juego no existe"}
        ana_socket.send_json({"type": "dance"})
        assert ana_socket.receive_json()["type"] == "error"


def test_leaving_passes_the_host_on_and_the_last_one_closes_the_sala(browser):
    ana, luis = browser("Ana"), browser("Luis")
    code = create(ana)
    join(luis, code)
    with luis.websocket_connect(f"/ws/sala/{code}") as luis_socket:
        view(luis_socket)
        with ana.websocket_connect(f"/ws/sala/{code}") as ana_socket:
            view(ana_socket)
            view(luis_socket)
            ana_socket.send_json({"type": "leave"})
            with pytest.raises(WebSocketDisconnect) as closed:
                ana_socket.receive_json()
            assert closed.value.code == LEFT
        sala = view(luis_socket)
        assert sala["host"] == "Luis" and who(sala) == {"Luis": "conectada"}
        luis_socket.send_json({"type": "leave"})
        with pytest.raises(WebSocketDisconnect):
            luis_socket.receive_json()
    assert join(browser("Eva"), code).status_code == 404  # sin nadie, la sala ya no existe


def test_signing_out_disconnects_but_keeps_the_place(browser):
    ana, luis = browser("Ana"), browser("Luis")
    code = create(ana)
    join(luis, code)
    with ana.websocket_connect(f"/ws/sala/{code}") as ana_socket:
        view(ana_socket)
        with luis.websocket_connect(f"/ws/sala/{code}") as luis_socket:
            view(luis_socket)
            view(ana_socket)
            luis.post("/api/logout")
            with pytest.raises(WebSocketDisconnect) as closed:
                luis_socket.receive_json()
            assert closed.value.code == 4401
            close_tab(luis_socket)  # el navegador da por cerrada la conexión
            assert who(view(ana_socket)) == {"Ana": "conectada", "Luis": "desconectada"}
    luis.post("/api/login", json={"username": "Luis", "password": PASSWORD})
    assert luis.get("/api/salas/mia").json()["sala"]["code"] == code


def test_the_menu_knows_which_games_have_salas(browser):
    games = {game["id"]: game for game in browser().get("/api/juegos").json()}
    assert games["poker"]["rooms"] and games["blackjack"]["rooms"] and games["prisma"]["rooms"]
    assert not games["salas"]["rooms"]
