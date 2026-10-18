"""Desde la etapa 5 hace falta cuenta para jugar, y crearla es lo más fácil posible.

Estos tests usan el servidor como de verdad: sin `require_account=False`.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from accounts import Cost
from server.accounts_api import SESSION_COOKIE
from server.app import create_app

GUEST = "invitado-de-prueba"
PASSWORD = "una clave de prueba"
JOKER = {"username": "Joker", "password": PASSWORD}
GAMES = ("poker", "blackjack", "prisma")


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


def open_partida(client, game="poker", **extra):
    return client.post("/api/partidas", json={"game": game, **extra})


def refused(client, url):
    """Código con el que el servidor cierra el WebSocket sin dejarlo entrar."""
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(url) as socket:
            socket.receive_json()
    return closed.value.code


# --- Sin cuenta no se juega ---


@pytest.mark.parametrize("game", GAMES)
def test_a_guest_cannot_open_a_partida(client, game):
    response = open_partida(client, game, guest_id=GUEST)
    assert response.status_code == 401
    assert response.json() == {"message": "Entra en tu cuenta para jugar"}
    assert client.get(f"/api/partidas?guest_id={GUEST}").json() == {"partidas": []}


def test_a_guest_cannot_sit_at_a_table(app, client):
    client.post("/api/register", json=JOKER)
    partida = open_partida(client).json()["partida_id"]
    guest = TestClient(app)
    assert refused(guest, f"/ws/poker/{partida}?guest_id={GUEST}") == 4401
    assert refused(guest, f"/ws/poker/no-existe?guest_id={GUEST}") == 4401


def test_a_made_up_cookie_is_not_an_account(app):
    browser = TestClient(app, cookies={SESSION_COOKIE: "inventada"})
    assert open_partida(browser, guest_id=GUEST).status_code == 401


def test_with_an_account_every_game_opens(client):
    client.post("/api/register", json=JOKER)
    for game in GAMES:
        partida = open_partida(client, game)
        assert partida.status_code == 200, partida.text
        with client.websocket_connect(f"/ws/{game}/{partida.json()['partida_id']}") as socket:
            hello = socket.receive_json()
        assert hello["game"] == game and hello["user"]["username"] == "Joker"
    assert len(client.get("/api/partidas").json()["partidas"]) == 3


def test_after_logout_the_partidas_are_out_of_reach(client):
    client.post("/api/register", json=JOKER)
    partida = open_partida(client).json()["partida_id"]
    client.post("/api/logout")
    assert open_partida(client).status_code == 401
    assert client.get("/api/partidas").json() == {"partidas": []}
    assert refused(client, f"/ws/poker/{partida}") == 4401
    # Al volver a entrar, la partida sigue ahí.
    client.post("/api/login", json=JOKER)
    assert open_partida(client).json()["partida_id"] == partida


# --- Crear la cuenta y entrar ---


def test_the_email_is_optional(client):
    response = client.post("/api/register", json={**JOKER, "email": " Joker@Ejemplo.com"})
    assert response.status_code == 201
    # Lo que se sabe de la cuenta en cada respuesta no cambia: el correo solo sale en el perfil.
    assert response.json() == {"user": {"username": "Joker", "balance": 10_000}}
    assert client.get("/api/profile").json()["user"]["email"] == "joker@ejemplo.com"
    for name, extra in (("Harley", {}), ("Ivy", {"email": None}), ("Selina", {"email": ""})):
        browser = TestClient(client.app)
        reply = browser.post("/api/register", json={"username": name, "password": PASSWORD, **extra})
        assert reply.status_code == 201
        assert browser.get("/api/profile").json()["user"]["email"] is None


def test_you_can_sign_in_with_the_email(client):
    client.post("/api/register", json={**JOKER, "email": "joker@ejemplo.com"})
    browser = TestClient(client.app)
    wrong = browser.post("/api/login", json={"username": "joker@ejemplo.com", "password": "otra clave"})
    assert wrong.status_code == 401
    right = browser.post("/api/login", json={"username": "JOKER@ejemplo.com", "password": PASSWORD})
    assert right.status_code == 200 and right.json()["user"]["username"] == "Joker"
    assert open_partida(browser).status_code == 200


def test_a_taken_or_malformed_email_is_explained(client):
    client.post("/api/register", json={**JOKER, "email": "joker@ejemplo.com"})
    browser = TestClient(client.app)
    harley = {"username": "Harley", "password": PASSWORD}
    taken = browser.post("/api/register", json={**harley, "email": "JOKER@ejemplo.com"})
    assert taken.status_code == 409 and taken.json() == {"message": "Ese correo ya está en uso"}
    malformed = browser.post("/api/register", json={**harley, "email": "harley"})
    assert malformed.status_code == 400 and "correo" in malformed.json()["message"]
    assert browser.get("/api/me").json() == {"user": None}


@pytest.mark.parametrize("email", [7, ["joker@ejemplo.com"], "x" * 301])
def test_the_email_must_be_short_text(client, email):
    assert client.post("/api/register", json={**JOKER, "email": email}).status_code == 422


def test_logging_in_takes_no_email_field(client):
    client.post("/api/register", json=JOKER)
    body = {**JOKER, "email": "joker@ejemplo.com"}
    assert TestClient(client.app).post("/api/login", json=body).status_code == 422
