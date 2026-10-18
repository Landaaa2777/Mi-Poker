"""Pasada de seguridad: lo que un cliente tramposo no puede hacer en ningún juego.

El servidor es la única autoridad. Aquí se intenta, en los tres juegos:
- entrar en la partida de otro, o desde otra web;
- mandar mensajes rotos o inventados para forzar algo;
- encontrar en lo que llega al navegador el mazo, el zapato o cartas ajenas.
"""

import json
import random

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from core.shuffle import SYSTEM_RNG
from games.blackjack.engine import Shoe
from games.poker.engine import deck as poker_deck
from games.prisma.engine import PrismaGame
from server.app import create_app

GUEST = "invitado-de-prueba"
GAMES = ["poker", "blackjack", "prisma"]
# Lo mínimo para empezar una partida en cada juego.
START = {
    "poker": {"type": "new_game", "config": {"bots": 2}},
    "blackjack": {"type": "new_game", "config": {"bots": 2}},
    "prisma": {"type": "new_game", "config": {"bots": 2}},
}
# Nombres de campos que nunca deben viajar al navegador.
SECRETS = {"deck", "draw_pile", "shoe_cards", "hole_card", "cards_left", "rng", "seed"}


@pytest.fixture
def app():
    # Bots muy lentos: así nada cambia solo mientras se prueban los mensajes.
    return create_app(
        bot_delay=(30, 30), simulations=30, serve_frontend=False, require_account=False
    )


def url(client, game, guest_id=GUEST):
    response = client.post("/api/partidas", json={"game": game, "guest_id": guest_id})
    assert response.status_code == 200, response.text
    return f"/ws/{game}/{response.json()['partida_id']}?guest_id={guest_id}"


def keys_in(value) -> set[str]:
    """Todas las claves de un estado, a cualquier profundidad."""
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in keys_in(item)}
    if isinstance(value, list):
        return {key for item in value for key in keys_in(item)}
    return set()


@pytest.mark.parametrize("game", GAMES)
def test_nobody_else_can_open_my_partida(app, game):
    client = TestClient(app)
    mine = url(client, game)
    partida = mine.split("/")[3].split("?")[0]
    attempts = [
        mine.replace(GUEST, "otro-invitado-cualquiera"),  # otra identidad con mi id de partida
        mine.split("?")[0],  # sin identidad
        f"/ws/{'poker' if game != 'poker' else 'blackjack'}/{partida}?guest_id={GUEST}",  # otro juego
        f"/ws/{game}/inventada?guest_id={GUEST}",
    ]
    for wrong in attempts:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(wrong) as socket:
                socket.receive_json()


@pytest.mark.parametrize("game", GAMES)
def test_other_sites_cannot_open_a_table(app, game):
    client = TestClient(app)
    foreign = {"Origin": "http://otra-web.example"}
    reply = client.post("/api/partidas", json={"game": game, "guest_id": GUEST}, headers=foreign)
    assert reply.status_code == 403
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(url(client, game), headers=foreign) as socket:
            socket.receive_json()


GARBAGE = [
    "",
    "esto no es JSON",
    "null",
    "[]",
    "{}",
    "42",
    '{"type": "ver_cartas"}',
    '{"type": "dame_fichas", "amount": 1000000}',
    '{"type": "new_game", "config": {"bots": 99}}',
    '{"type": "new_game", "config": {"starting_stack": -5}}',
    '{"type": "new_game", "config": {"campo_inventado": true}}',
    '{"type": "' + "x" * 5000 + '"}',
    '{"type": "action", "action": "ver_mazo"}',
    '{"type": "action", "action": "raise", "amount": "mucho"}',
    '{"type": "play", "card": -1}',
    '{"type": "bet", "amount": -100}',
    '{"type": "insurance", "take": "quizá"}',
    '{"type": "color", "color": "rojo"}',
]


@pytest.mark.parametrize("game", GAMES)
def test_broken_or_made_up_messages_never_change_the_game(app, game):
    client = TestClient(app)
    with client.websocket_connect(url(client, game)) as socket:
        socket.receive_json()
        socket.send_json(START[game])
        socket.receive_json()
        session = app.state.partidas.find(GUEST, game).session
        before = json.dumps(session.state(), sort_keys=True)
        for text in GARBAGE:
            socket.send_text(text)
            reply = socket.receive_json()
            assert reply["type"] == "error", (text, reply)
            assert json.dumps(session.state(), sort_keys=True) == before, text
        # Y la mesa sigue funcionando después de todo eso.
        socket.send_json({"type": "restart"})
        assert socket.receive_json()["type"] == "state"


@pytest.mark.parametrize("game", GAMES)
def test_the_browser_never_receives_the_deck(app, game):
    client = TestClient(app)
    with client.websocket_connect(url(client, game)) as socket:
        hello = socket.receive_json()
        socket.send_json(START[game])
        state = socket.receive_json()["state"]
    assert not keys_in(hello) & SECRETS
    assert not keys_in(state) & SECRETS
    text = json.dumps(state)
    assert len(text) < 60_000  # un estado normal; el mazo entero no cabría así como así


def test_random_fuzzing_never_breaks_a_table(app):
    """Mensajes al azar con piezas válidas mezcladas: el servidor siempre contesta y sigue vivo."""
    rng = random.Random(7)
    pieces = {
        "type": ["action", "play", "bet", "draw", "pass", "insurance", "color", "next_hand", "next_round", "catch"],
        "action": ["fold", "call", "raise", "hit", "split", "nada"],
        "amount": [0, -1, 10, 10**12, "10"],
        "card": [0, 107, 108, -3, "x"],
        "color": ["halo", "rojo", None],
        "take": [True, "no"],
    }
    client = TestClient(app)
    for game in GAMES:
        with client.websocket_connect(url(client, game)) as socket:
            socket.receive_json()
            socket.send_json(START[game])
            socket.receive_json()
            for _ in range(60):
                message = {key: rng.choice(values) for key, values in pieces.items() if rng.random() < 0.6}
                socket.send_json(message)
                assert socket.receive_json()["type"] in ("state", "error")


def test_every_game_shuffles_with_the_system_generator():
    assert poker_deck._SYSTEM_RNG is SYSTEM_RNG
    assert Shoe(1)._rng is None  # sin generador propio: usa el del sistema
    assert PrismaGame(["a", "b"]).rng is SYSTEM_RNG
    assert type(SYSTEM_RNG).__name__ == "SystemRandom"
