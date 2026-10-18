"""Servidor: el saldo de fichas de una cuenta se lleva a la mesa y cambia con cada mano."""

import pytest
from fastapi.testclient import TestClient

from accounts import REFILL_BELOW, STARTING_BALANCE, Cost
from server.app import create_app
from games.poker.protocol import MAX_STACK
from games.poker.tests.test_server import Table, facing_a_bet, my_turn, poker_url

GUEST = "invitado-de-prueba"
PASSWORD = "una clave de prueba"
JOKER = {"username": "Joker", "password": PASSWORD}
# Dos ciegas de fichas: jugando todo o nada, la mesa se acaba en pocas manos.
TINY = {"bots": 1, "starting_stack": 20, "small_blind": 5, "big_blind": 10}


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


@pytest.fixture
def table(joker):
    with joker.websocket_connect(poker_url(joker, None)) as socket:
        assert socket.receive_json()["user"] == {"username": "Joker", "balance": STARTING_BALANCE}
        yield Table(socket, None)


def balance(client):
    """El saldo según el servidor. Solo es estable si no hay ninguna mano jugándose sola."""
    return client.get("/api/me").json()["user"]["balance"]


def set_balance(client, chips):
    """Deja la cuenta con `chips` fichas, tocando la base de datos directamente."""
    store = client.app.state.accounts
    user = store.authenticate(JOKER["username"], PASSWORD)
    store.add_chips(user, chips - store.balance(user))


def my_stack(state):
    return state["seats"][0]["stack"]


def my_bet(state):
    """Lo que llevo puesto en el bote en la mano en curso."""
    return state["seats"][0]["contributed"]


def just_dealt(table, **message):
    """Envía una intención que reparte y devuelve la mesa recién repartida, antes de que nadie juegue."""
    table.send(**message)
    return table.receive()["state"]


def mid_hand(table, **config):
    """Empieza partidas hasta quedar a media mano: con fichas ya apostadas y el turno en mi mano."""
    for _ in range(200):
        state = my_turn(table, needs=facing_a_bet, **config)
        state = table.request(type="action", action="call")
        if state["hand_in_progress"] and my_bet(state) > 0:
            return state
    raise AssertionError("No llegó ninguna mano que siguiera después de igualar")


def play_out(table, state, action="all_in"):
    """Juega la partida en curso hasta que se acabe la mesa. Devuelve el último estado."""
    for _ in range(500):
        state = table.play_hand(state, action)
        if state["human_out"] or state["game_over"]:
            return state
        state = table.request(type="next_hand")
    raise AssertionError("La partida no terminó")


# --- Qué se dice del saldo ---


def test_the_options_explain_the_balance_rules(joker):
    with joker.websocket_connect(poker_url(joker, None)) as socket:
        options = socket.receive_json()["options"]
    assert options["starting_balance"] == STARTING_BALANCE == 10_000
    assert options["refill_below"] == REFILL_BELOW == 100


def test_the_profile_shows_the_balance(joker):
    assert joker.get("/api/profile").json()["user"]["balance"] == STARTING_BALANCE


def test_guests_have_no_balance_and_bring_any_chips_they_like(app):
    guest = TestClient(app)
    with guest.websocket_connect(poker_url(guest)) as socket:
        assert socket.receive_json()["user"] is None
        state = just_dealt(
            Table(socket, None), type="new_game", config={"starting_stack": MAX_STACK, "bots": 1}
        )
    assert state["balance"] is None
    assert state["config"]["starting_stack"] == MAX_STACK


# --- Las fichas de la mesa salen del saldo ---


def test_sitting_down_does_not_change_the_balance(table):
    """El saldo cuenta las fichas que tengo en la mesa: sentarme no me quita nada."""
    state = just_dealt(table, type="new_game", config={"bots": 2, "starting_stack": 2_000})
    assert state["hand_in_progress"] and my_stack(state) + my_bet(state) == 2_000
    assert state["balance"] == STARTING_BALANCE


def test_every_hand_moves_the_balance_by_what_i_won_or_lost(table):
    owned, hands = STARTING_BALANCE, 0
    while hands < 10:  # si una mesa se acaba pronto, se sigue en otra
        state = table.request(type="new_game", config={"bots": 3, "starting_stack": 1_000})
        bank = owned - 1_000  # lo que no llevé a esta mesa
        while True:
            state = table.play_hand(state)
            hands += 1
            owned = state["balance"]
            assert owned == bank + my_stack(state)
            if state["human_out"] or state["game_over"] or hands >= 10:
                break
            state = table.request(type="next_hand")


def test_the_balance_waits_for_the_end_of_the_hand(table):
    state = mid_hand(table, bots=2, starting_stack=1_000)
    assert state["hand_number"] == 1
    at_the_start = state["balance"]  # el de antes de esta mano: aún no ha cambiado
    while state["hand_in_progress"]:
        assert state["balance"] == at_the_start
        state = table.request(type="action", action="call")
    assert state["balance"] == at_the_start - 1_000 + my_stack(state)


def test_the_balance_is_the_same_everywhere(joker, table):
    state = table.play_hand(table.request(type="new_game", config={"bots": 2}))
    assert balance(joker) == state["balance"]
    assert joker.get("/api/profile").json()["user"]["balance"] == state["balance"]


def test_a_whole_table_wins_or_costs_exactly_what_was_brought(table, joker):
    expected = STARTING_BALANCE
    for _ in range(12):
        final = play_out(table, table.request(type="new_game", config=TINY))
        won = final["game_over"] and final["winner_seat"] == 0
        expected += 20 if won else -20  # gano las 20 del rival o pierdo las mías
        assert final["balance"] == expected == balance(joker)


def test_chips_carry_over_from_one_table_to_the_next(table):
    first = table.play_hand(table.request(type="new_game", config={"bots": 2, "starting_stack": 500}))
    carried = first["balance"]
    assert carried == STARTING_BALANCE - 500 + my_stack(first)
    second = table.request(type="new_game", config={"bots": 2, "starting_stack": 3_000})
    final = table.play_hand(second)
    assert final["hand_number"] == 1
    assert final["balance"] == carried - 3_000 + my_stack(final)


# --- No se puede llevar más de lo que se tiene ---


def test_i_cannot_bring_more_chips_than_i_have(table, joker):
    message = table.error(type="new_game", config={"starting_stack": STARTING_BALANCE + 1})
    assert "hasta 10000" in message
    assert balance(joker) == STARTING_BALANCE
    state = just_dealt(
        table, type="new_game", config={"starting_stack": STARTING_BALANCE, "bots": 1}
    )
    assert state["config"]["starting_stack"] == STARTING_BALANCE  # todo el saldo sí


def test_a_refused_table_leaves_the_current_hand_alone(table, joker):
    state = mid_hand(table, bots=2, starting_stack=1_000)
    available = state["balance"] - my_bet(state)
    # Pido una mesa con todo mi saldo, pero parte está apostada en esta mano.
    message = table.error(type="new_game", config={"starting_stack": state["balance"], "bots": 2})
    assert f"hasta {available}" in message
    assert balance(joker) == state["balance"]  # no se me ha cobrado nada
    after = table.request(type="action", action="call")
    assert after["hand_number"] == state["hand_number"]  # y la mano sigue
    assert after["config"]["starting_stack"] == 1_000


def test_without_chips_there_is_no_table(joker):
    set_balance(joker, 0)
    with joker.websocket_connect(poker_url(joker, None)) as socket:
        assert socket.receive_json()["user"]["balance"] == 0
        table = Table(socket, None)
        assert "No te quedan fichas" in table.error(type="new_game", config={"starting_stack": 10})
        assert "No te quedan fichas" in table.error(type="new_game", config=TINY)


# --- Dejar una mano a medias ---


def test_leaving_a_hand_halfway_costs_what_i_had_bet(table):
    state = mid_hand(table, bots=3, starting_stack=1_000)
    before, bet = state["balance"], my_bet(state)
    fresh = just_dealt(table, type="restart")
    assert fresh["hand_number"] == 1
    assert fresh["balance"] == before - bet


def test_leaving_a_hand_halfway_for_another_table_costs_the_same(table):
    state = mid_hand(table, bots=3, starting_stack=1_000)
    before, bet = state["balance"], my_bet(state)
    fresh = just_dealt(table, type="new_game", config={"bots": 1, "starting_stack": 400})
    assert fresh["balance"] == before - bet
    assert my_stack(fresh) + my_bet(fresh) == 400


def test_leaving_between_hands_costs_nothing(table):
    state = table.play_hand(table.request(type="new_game", config={"bots": 2}))
    after_hand = state["balance"]
    fresh = just_dealt(table, type="new_game", config={"bots": 2, "starting_stack": 700})
    assert fresh["balance"] == after_hand


# --- Recarga gratis ---


def test_the_refill_needs_a_session_and_our_own_page(app, joker):
    assert TestClient(app).post("/api/refill").status_code == 401
    set_balance(joker, 0)
    assert joker.post("/api/refill", headers={"Origin": "http://otra-web.example"}).status_code == 403
    assert balance(joker) == 0


def test_the_refill_is_refused_while_there_are_chips(joker):
    response = joker.post("/api/refill")
    assert response.status_code == 400 and "menos de 100" in response.json()["message"]
    set_balance(joker, REFILL_BELOW)
    assert joker.post("/api/refill").status_code == 400
    assert balance(joker) == REFILL_BELOW


def test_the_refill_gives_back_the_starting_balance_once(joker):
    set_balance(joker, REFILL_BELOW - 1)
    response = joker.post("/api/refill")
    assert response.status_code == 200 and response.json() == {"balance": STARTING_BALANCE}
    assert balance(joker) == STARTING_BALANCE
    assert joker.post("/api/refill").status_code == 400  # no se acumula


def test_after_going_broke_a_refill_lets_me_play_again(joker):
    set_balance(joker, 20)
    with joker.websocket_connect(poker_url(joker, None)) as socket:
        socket.receive_json()
        table = Table(socket, None)
        final = play_out(table, table.request(type="new_game", config=TINY))
        while not final["human_out"]:  # gané la mesa: me lo vuelvo a jugar hasta perderlo
            set_balance(joker, 20)
            final = play_out(table, table.request(type="new_game", config=TINY))
        assert final["balance"] == 0
        assert "No te quedan fichas" in table.error(type="restart")
        assert joker.post("/api/refill").json() == {"balance": STARTING_BALANCE}
        state = just_dealt(table, type="restart")
        assert state["hand_number"] == 1 and state["balance"] == STARTING_BALANCE


# --- La base de datos falla ---


def test_a_failure_reading_the_balance_does_not_break_the_table(app, table, monkeypatch, caplog):
    state = my_turn(table, bots=2)
    known = state["balance"]

    def broken(*_):
        raise OSError("disco roto")

    monkeypatch.setattr(app.state.accounts, "balance", broken)
    state = table.request(type="action", action="fold")
    assert state["balance"] == known  # se muestra el último saldo que se pudo leer
    assert "No se pudo leer el saldo" in caplog.text
