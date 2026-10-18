"""Servidor: las estadísticas de cada cuenta se guardan al terminar cada mano."""

import pytest
from fastapi.testclient import TestClient

from accounts import Cost, LevelStats
from games.poker.engine import CATEGORY_NAMES
from server.accounts_api import public_stats
from server.app import create_app
from games.poker.tests.test_server import Table, poker_url

GUEST = "invitado-de-prueba"
JOKER = {"username": "Joker", "password": "una clave de prueba"}
HAND_ORDER = list(CATEGORY_NAMES.values())  # de la peor a la mejor
NOTHING = {
    "hands_played": 0,
    "hands_won": 0,
    "biggest_win": 0,
    "best_hand": None,
    "games_played": 0,
    "games_won": 0,
}


@pytest.fixture
def app(tmp_path):
    return create_app(
        bot_delay=(0, 0),
        simulations=30,
        serve_frontend=False,
        database=tmp_path / "cuentas.db",
        password_cost=Cost(n=16, r=1, p=1),
        require_account=False,  # estos tests juegan como invitado
    )


@pytest.fixture
def joker(app):
    client = TestClient(app)
    assert client.post("/api/register", json=JOKER).status_code == 201
    return client


def stats(client):
    return client.get("/api/profile").json()["stats"]


def play(socket, hands, action="call", **config):
    """Empieza una partida y juega hasta `hands` manos. Devuelve cómo acabó cada una."""
    table = Table(socket, None)
    finished = []
    state = table.request(type="new_game", config=config)
    while True:
        finished.append(table.play_hand(state, action))
        if len(finished) == hands or finished[-1]["human_out"] or finished[-1]["game_over"]:
            return finished
        state = table.request(type="next_hand")


def expected(finished):
    """Las estadísticas que deberían salir de unas manos ya jugadas, vistas desde el cliente."""
    won = [state["result"]["payouts"].get("0", 0) for state in finished]
    shown = [state["result"]["hand_names"].get("0") for state in finished]
    shown = [name for name in shown if name]
    return {
        "hands_played": len(finished),
        "hands_won": sum(amount > 0 for amount in won),
        "biggest_win": max(won, default=0),
        "best_hand": max(shown, key=HAND_ORDER.index, default=None),
        "games_played": sum(state["hand_number"] == 1 for state in finished),
        "games_won": sum(state["game_over"] and state["winner_seat"] == 0 for state in finished),
    }


def test_the_profile_needs_a_session(app):
    response = TestClient(app).get("/api/profile")
    assert response.status_code == 401 and response.json()["message"]


def test_a_new_account_starts_from_zero(joker):
    profile = joker.get("/api/profile").json()
    assert profile["user"]["username"] == "Joker"
    assert isinstance(profile["user"]["member_since"], int)
    assert profile["stats"] == {"total": NOTHING, "levels": []}
    assert "password" not in str(profile).lower()


def test_every_finished_hand_is_counted_as_the_player_saw_it(joker):
    with joker.websocket_connect(poker_url(joker, None)) as socket:
        socket.receive_json()
        finished = play(socket, hands=12, bots=3, difficulty="easy")
    assert len(finished) > 1
    result = stats(joker)
    assert result["total"] == expected(finished)
    assert result["levels"] == [{"difficulty": "easy", "name": "Fácil", **expected(finished)}]


def test_stats_are_saved_before_the_player_sees_the_result(joker):
    """Al llegar el final de la mano al cliente, el perfil ya la cuenta."""
    with joker.websocket_connect(poker_url(joker, None)) as socket:
        socket.receive_json()
        for hands in (1, 2, 3):
            play(socket, hands=1, bots=2, difficulty="easy")
            assert stats(joker)["total"]["hands_played"] == hands


def test_levels_are_listed_from_weakest_to_strongest(joker):
    with joker.websocket_connect(poker_url(joker, None)) as socket:
        socket.receive_json()
        hard = play(socket, hands=1, bots=1, difficulty="hard")
        easy = play(socket, hands=2, bots=1, difficulty="easy")
    result = stats(joker)
    assert [level["name"] for level in result["levels"]] == ["Fácil", "Difícil"]
    assert result["levels"][0] == {"difficulty": "easy", "name": "Fácil", **expected(easy)}
    assert result["levels"][1] == {"difficulty": "hard", "name": "Difícil", **expected(hard)}
    assert result["total"] == expected(hard + easy)


def test_winning_or_losing_a_whole_game_is_counted(joker):
    with joker.websocket_connect(poker_url(joker, None)) as socket:
        socket.receive_json()
        finished = []
        for _ in range(4):
            # Todo o nada contra un solo rival y con dos ciegas de fichas: aunque el
            # rival se retire siempre, las ciegas lo dejan sin nada en pocas manos.
            finished += play(
                socket, hands=200, action="all_in", bots=1, difficulty="easy",
                starting_stack=20, small_blind=5, big_blind=10,
            )
            assert finished[-1]["game_over"]
    result = stats(joker)["total"]
    assert result == expected(finished)
    assert result["games_played"] == 4 and 0 <= result["games_won"] <= 4
    assert result["games_won"] == sum(state["winner_seat"] == 0 for state in finished)


def test_a_hand_left_halfway_is_not_counted(joker):
    with joker.websocket_connect(poker_url(joker, None)) as socket:
        socket.receive_json()
        table = Table(socket, None)
        state = table.request(type="new_game", config={"bots": 5, "difficulty": "easy"})
        restarts = 0
        while not state["hand_in_progress"]:  # los bots la acabaron sin mí: otra
            state = table.request(type="restart")
            restarts += 1
        after = table.request(type="restart")  # la dejo a medias; esto reparte otra
    # Cuentan las que terminaron sin mí, y la última si también acabó sola. La que dejé, no.
    finished = restarts + (0 if after["hand_in_progress"] else 1)
    assert stats(joker)["total"]["hands_played"] == finished


def test_guests_have_no_stats(app, joker):
    guest = TestClient(app)
    with guest.websocket_connect(poker_url(guest)) as socket:
        socket.receive_json()
        play(socket, hands=3, bots=2, difficulty="easy")
    assert guest.get("/api/profile").status_code == 401
    assert stats(joker) == {"total": NOTHING, "levels": []}


def test_each_account_keeps_its_own_stats(app, joker):
    ana = TestClient(app)
    ana.post("/api/register", json={**JOKER, "username": "Ana"})
    with ana.websocket_connect(poker_url(ana, None)) as socket:
        socket.receive_json()
        finished = play(socket, hands=2, bots=2, difficulty="medium")
    assert stats(ana)["total"] == expected(finished)
    assert stats(joker)["total"] == NOTHING


def test_a_failure_saving_stats_does_not_break_the_hand(app, joker, monkeypatch, caplog):
    def broken(*_):
        raise OSError("disco lleno")

    monkeypatch.setattr(app.state.accounts, "record_hand", broken)
    with joker.websocket_connect(poker_url(joker, None)) as socket:
        socket.receive_json()
        [state] = play(socket, hands=1, bots=2, difficulty="easy")
    assert not state["hand_in_progress"] and state["result"] is not None
    assert "No se pudo guardar el resultado de una mano" in caplog.text
    assert stats(joker)["total"] == NOTHING


def test_the_best_hand_travels_by_name():
    assert public_stats(LevelStats(best_hand=6))["best_hand"] == "Color"
    assert public_stats(LevelStats(best_hand=10))["best_hand"] == "Escalera real"
    assert public_stats(LevelStats())["best_hand"] is None
