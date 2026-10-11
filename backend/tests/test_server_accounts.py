"""Servidor: registro, inicio y cierre de sesión, y la partida de cada cuenta."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from accounts import Cost
from server.accounts_api import SESSION_COOKIE, WRONG_CREDENTIALS
from server.app import create_app

GUEST = "invitado-de-prueba"
PASSWORD = "una clave de prueba"
JOKER = {"username": "Joker", "password": PASSWORD}
JOKER_USER = {"username": "Joker", "balance": 10_000}  # lo que el cliente sabe de la cuenta


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


@pytest.fixture
def joker(client):
    """Un cliente con la cuenta ya creada y la sesión iniciada."""
    assert client.post("/api/register", json=JOKER).status_code == 201
    return client


def hello(client, query=f"?guest_id={GUEST}"):
    with client.websocket_connect(f"/ws{query}") as socket:
        return socket.receive_json()


def session_cookie(response):
    return next(
        header for header in response.headers.get_list("set-cookie") if header.startswith(SESSION_COOKIE)
    )


# --- Registro ---


def test_register_creates_the_account_and_signs_in(client):
    response = client.post("/api/register", json=JOKER)
    assert response.status_code == 201
    assert response.json() == {"user": JOKER_USER}
    assert client.get("/api/me").json() == {"user": JOKER_USER}


def test_the_session_cookie_is_hidden_from_scripts(client):
    cookie = session_cookie(client.post("/api/register", json=JOKER)).lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "max-age=2592000" in cookie
    assert "secure" not in cookie  # en local se sirve por http


def test_over_https_the_cookie_is_marked_secure(app):
    client = TestClient(app, base_url="https://testserver")
    assert "secure" in session_cookie(client.post("/api/register", json=JOKER)).lower()


def test_no_reply_ever_carries_the_password(client):
    replies = [
        client.post("/api/register", json=JOKER),
        client.post("/api/login", json=JOKER),
        client.get("/api/me"),
        client.post("/api/login", json={**JOKER, "password": PASSWORD + "!"}),
    ]
    for reply in replies:
        assert PASSWORD not in reply.text and "password" not in reply.text.lower()


@pytest.mark.parametrize(
    "credentials",
    [
        {"username": "ab", "password": PASSWORD},
        {"username": "con espacio", "password": PASSWORD},
        {"username": "joker", "password": "corta"},
    ],
)
def test_register_explains_what_is_wrong(client, credentials):
    response = client.post("/api/register", json=credentials)
    assert response.status_code == 400 and response.json()["message"]
    assert client.get("/api/me").json() == {"user": None}


def test_register_refuses_a_taken_username(joker):
    response = TestClient(joker.app).post("/api/register", json={**JOKER, "username": "JOKER"})
    assert response.status_code == 409
    assert "ya está en uso" in response.json()["message"]


@pytest.mark.parametrize(
    "body", [{}, {"username": "joker"}, {**JOKER, "extra": 1}, {"username": 7, "password": PASSWORD}]
)
def test_malformed_requests_are_rejected(client, body):
    assert client.post("/api/register", json=body).status_code == 422
    assert client.post("/api/login", json=body).status_code == 422


# --- Inicio y cierre de sesión ---


def test_login_with_the_right_password(joker):
    other_browser = TestClient(joker.app)
    assert other_browser.get("/api/me").json() == {"user": None}
    response = other_browser.post("/api/login", json={"username": "joker", "password": PASSWORD})
    assert response.status_code == 200 and response.json() == {"user": JOKER_USER}
    assert other_browser.get("/api/me").json() == {"user": JOKER_USER}


def test_a_failed_login_does_not_say_whether_the_user_exists(joker):
    browser = TestClient(joker.app)
    wrong_password = browser.post("/api/login", json={**JOKER, "password": "otra clave distinta"})
    unknown_user = browser.post("/api/login", json={"username": "nadie", "password": PASSWORD})
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json() == {"message": WRONG_CREDENTIALS}
    assert browser.get("/api/me").json() == {"user": None}


def test_repeated_failures_are_slowed_down(joker):
    browser = TestClient(joker.app)
    wrong = {**JOKER, "password": "otra clave distinta"}
    for _ in range(5):
        assert browser.post("/api/login", json=wrong).status_code == 401
    blocked = browser.post("/api/login", json=JOKER)  # ni con la contraseña buena
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0 and "Espera" in blocked.json()["message"]
    assert browser.get("/api/me").json() == {"user": None}
    # A otra cuenta no le afecta.
    assert browser.post("/api/register", json={"username": "ana", "password": PASSWORD}).status_code == 201


def test_a_successful_login_clears_earlier_failures(joker):
    browser = TestClient(joker.app)
    wrong = {**JOKER, "password": "otra clave distinta"}
    for _ in range(3):
        for _ in range(4):
            assert browser.post("/api/login", json=wrong).status_code == 401
        assert browser.post("/api/login", json=JOKER).status_code == 200


def test_logout_ends_the_session_for_good(joker):
    token = joker.cookies.get(SESSION_COOKIE)
    assert token
    assert joker.post("/api/logout").json() == {"user": None}
    assert joker.cookies.get(SESSION_COOKIE) is None
    assert joker.get("/api/me").json() == {"user": None}
    # Quien se hubiera guardado la cookie tampoco puede usarla ya.
    thief = TestClient(joker.app, cookies={SESSION_COOKIE: token})
    assert thief.get("/api/me").json() == {"user": None}


def test_logout_without_a_session_is_harmless(client):
    assert client.post("/api/logout").json() == {"user": None}


def test_requests_from_another_site_are_refused(joker):
    foreign = {"Origin": "http://otra-web.example"}
    assert joker.post("/api/logout", headers=foreign).status_code == 403
    assert joker.post("/api/login", json=JOKER, headers=foreign).status_code == 403
    assert joker.post("/api/register", json=JOKER, headers=foreign).status_code == 403
    assert joker.get("/api/me").json() == {"user": JOKER_USER}
    assert joker.post("/api/logout", headers={"Origin": "http://testserver"}).status_code == 200


# --- La partida de cada cuenta ---


def test_guests_keep_playing_without_an_account(client):
    message = hello(client)
    assert message["user"] is None and message["state"] is None
    assert not client.app.state.accounts.path.exists()  # y sin tocar la base de datos


def test_hello_says_which_account_is_connected(joker):
    assert hello(joker)["user"] == JOKER_USER
    assert hello(joker, query="")["user"] == JOKER_USER  # no hace falta ser invitado


def test_a_made_up_cookie_plays_as_a_guest(app):
    client = TestClient(app, cookies={SESSION_COOKIE: "inventada"})
    assert hello(client)["user"] is None
    with pytest.raises(WebSocketDisconnect):
        hello(client, query="")


def test_with_an_account_the_table_name_is_the_account_name(joker):
    with joker.websocket_connect("/ws") as socket:
        socket.receive_json()
        socket.send_json({"type": "new_game", "config": {"player_name": "Impostor", "bots": 2}})
        state = socket.receive_json()["state"]
    assert state["seats"][0]["name"] == "Joker" and state["config"]["player_name"] == "Joker"


def test_a_guest_chooses_the_table_name(client):
    with client.websocket_connect(f"/ws?guest_id={GUEST}") as socket:
        socket.receive_json()
        socket.send_json({"type": "new_game", "config": {"player_name": "Invitada"}})
        assert socket.receive_json()["state"]["seats"][0]["name"] == "Invitada"


def test_each_identity_has_its_own_game(joker):
    with joker.websocket_connect(f"/ws?guest_id={GUEST}") as socket:
        socket.receive_json()
        socket.send_json({"type": "new_game", "config": {}})
        assert socket.receive_json()["state"]["hand_number"] == 1

    # La misma cuenta desde otro navegador retoma su partida...
    other_browser = TestClient(joker.app)
    other_browser.post("/api/login", json=JOKER)
    assert hello(other_browser)["state"]["seats"][0]["name"] == "Joker"
    # ...y un invitado con el mismo identificador no la ve.
    assert hello(TestClient(joker.app))["state"] is None


def test_the_game_of_a_guest_stays_with_the_guest(client):
    with client.websocket_connect(f"/ws?guest_id={GUEST}") as socket:
        socket.receive_json()
        socket.send_json({"type": "new_game", "config": {"player_name": "Invitada"}})
        socket.receive_json()
    client.post("/api/register", json=JOKER)
    assert hello(client)["state"] is None
    client.post("/api/logout")
    assert hello(client)["state"]["seats"][0]["name"] == "Invitada"


def test_logout_closes_the_open_connections_of_that_session(joker):
    with joker.websocket_connect("/ws") as socket:
        socket.receive_json()
        assert len(joker.app.state.connections) == 1
        joker.post("/api/logout")
        # Se comprueba antes de leer: sin el cierre, la lectura se quedaría esperando.
        assert not joker.app.state.connections
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
    assert closed.value.code == 4401


def test_the_table_refuses_connections_from_another_site(joker):
    with pytest.raises(WebSocketDisconnect):
        with joker.websocket_connect("/ws", headers={"Origin": "http://otra-web.example"}) as socket:
            socket.receive_json()
    with joker.websocket_connect("/ws", headers={"Origin": "http://testserver"}) as socket:
        assert socket.receive_json()["user"] == JOKER_USER
