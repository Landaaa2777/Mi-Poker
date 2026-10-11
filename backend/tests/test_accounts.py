"""Cuentas: contraseñas con hash, usuarios, sesiones y estadísticas en SQLite, y freno de intentos."""

import sqlite3
from contextlib import closing

import pytest

import accounts.store
from accounts import (
    DEFAULT_COST,
    SESSION_SECONDS,
    AccountError,
    AccountStore,
    Cost,
    HandOutcome,
    LevelStats,
    Throttle,
    UsernameTaken,
    hash_password,
    total,
    verify_password,
)

FAST = Cost(n=16, r=1, p=1)  # los tests no necesitan un hash caro
PASSWORD = "una clave de prueba"


class Clock:
    def __init__(self, now=1_000_000.0):
        self.now = now

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def store(tmp_path, clock):
    return AccountStore(tmp_path / "cuentas.db", FAST, clock)


def rows(store, query):
    with closing(sqlite3.connect(store.path)) as db:
        return db.execute(query).fetchall()


# --- Contraseñas ---


def test_a_hash_verifies_its_own_password_and_no_other():
    stored = hash_password(PASSWORD, FAST)
    assert stored.startswith("scrypt$") and PASSWORD not in stored
    assert verify_password(PASSWORD, stored)
    assert not verify_password(PASSWORD + " ", stored)
    assert not verify_password("", stored)


def test_equal_passwords_get_different_hashes():
    assert hash_password(PASSWORD, FAST) != hash_password(PASSWORD, FAST)


def test_the_default_cost_is_the_recommended_one():
    assert DEFAULT_COST == Cost(n=2**15, r=8, p=3)
    assert hash_password(PASSWORD).startswith("scrypt$32768$8$3$")


def test_the_same_text_typed_with_different_bytes_is_the_same_password():
    composed, decomposed = "contraseña larga", "contraseña larga"
    assert composed != decomposed
    assert verify_password(decomposed, hash_password(composed, FAST))


@pytest.mark.parametrize(
    "stored",
    [
        "",
        "texto cualquiera",
        "scrypt$16$1$1$zz$zz",
        "scrypt$16$1$1$00$",
        "otro$16$1$1$00$00",
        "scrypt$15$1$1$00$00",  # n debe ser potencia de dos
        "scrypt$1099511627776$8$1$00$00",  # pediría una cantidad absurda de trabajo
    ],
)
def test_an_unreadable_hash_never_verifies(stored):
    assert not verify_password(PASSWORD, stored)


# --- Usuarios ---


def test_register_keeps_a_hash_and_never_the_password(store):
    user = store.register("Joker", PASSWORD)
    assert user.username == "Joker"
    [(username, key, stored)] = rows(store, "SELECT username, username_key, password_hash FROM users")
    assert (username, key) == ("Joker", "joker")
    assert verify_password(PASSWORD, stored)
    assert PASSWORD.encode() not in store.path.read_bytes()


def test_usernames_are_unique_whatever_the_case(store):
    store.register("Joker", PASSWORD)
    with pytest.raises(UsernameTaken):
        store.register("JOKER", "otra clave distinta")
    assert len(rows(store, "SELECT id FROM users")) == 1


@pytest.mark.parametrize("username", ["ab", "x" * 17, "con espacio", "ñandú", "a@b.com", "", "  "])
def test_invalid_usernames_are_rejected(store, username):
    with pytest.raises(AccountError):
        store.register(username, PASSWORD)


@pytest.mark.parametrize("password", ["", "corta12", "x" * 129])
def test_invalid_passwords_are_rejected(store, password):
    with pytest.raises(AccountError):
        store.register("joker", password)


def test_spaces_around_the_username_are_dropped(store):
    assert store.register("  joker_99 ", PASSWORD).username == "joker_99"


def test_authenticate_needs_the_right_password(store):
    registered = store.register("Joker", PASSWORD)
    assert store.authenticate("joker", PASSWORD) == registered
    assert store.authenticate(" JOKER ", PASSWORD) == registered
    assert store.authenticate("joker", "otra clave distinta") is None
    assert store.authenticate("nadie", PASSWORD) is None
    assert store.authenticate("joker", "x" * 5000) is None


def test_an_unknown_user_costs_the_same_work_as_a_wrong_password(store, monkeypatch):
    """Si no, el tiempo de respuesta diría qué nombres de usuario existen."""
    store.register("joker", PASSWORD)
    checks = []
    real = accounts.store.verify_password
    monkeypatch.setattr(
        accounts.store, "verify_password", lambda *args: checks.append(1) or real(*args)
    )
    store.authenticate("joker", "otra clave distinta")
    store.authenticate("nadie", "otra clave distinta")
    assert len(checks) == 2


# --- Sesiones ---


def test_a_session_token_identifies_its_user(store):
    joker, ana = store.register("joker", PASSWORD), store.register("ana", PASSWORD)
    token, other = store.create_session(joker), store.create_session(ana)
    assert token != other and len(token) >= 43
    assert store.user_for_token(token) == joker
    assert store.user_for_token(other) == ana
    assert store.user_for_token("inventado") is None
    assert store.user_for_token("") is None
    assert store.user_for_token(None) is None


def test_the_database_keeps_only_a_hash_of_the_token(store):
    token = store.create_session(store.register("joker", PASSWORD))
    assert token.encode() not in store.path.read_bytes()
    [(saved,)] = rows(store, "SELECT token_hash FROM sessions")
    assert saved != token and len(saved) == 64


def test_closing_a_session_ends_only_that_one(store):
    user = store.register("joker", PASSWORD)
    phone, laptop = store.create_session(user), store.create_session(user)
    store.delete_session(phone)
    assert store.user_for_token(phone) is None
    assert store.user_for_token(laptop) == user


def test_sessions_expire_and_are_cleaned_up(store, clock):
    user = store.register("joker", PASSWORD)
    token = store.create_session(user)
    clock.now += SESSION_SECONDS - 1
    assert store.user_for_token(token) == user
    clock.now += 1
    assert store.user_for_token(token) is None
    store.create_session(user)
    assert len(rows(store, "SELECT token_hash FROM sessions")) == 1


def test_the_database_is_not_created_until_it_is_needed(tmp_path):
    store = AccountStore(tmp_path / "carpeta" / "cuentas.db", FAST)
    assert store.user_for_token("lo que sea") is None
    store.delete_session("lo que sea")
    assert not store.path.exists() and not store.path.parent.exists()
    store.register("joker", PASSWORD)
    assert store.path.exists()


def test_accounts_survive_reopening_the_database(store):
    token = store.create_session(store.register("joker", PASSWORD))
    reopened = AccountStore(store.path, FAST, store.clock)
    assert reopened.authenticate("joker", PASSWORD).username == "joker"
    assert reopened.user_for_token(token).username == "joker"


# --- Freno de intentos ---


def test_throttle_blocks_after_too_many_failures_and_lets_go_later(clock):
    throttle = Throttle(max_failures=3, window=60, clock=clock)
    for _ in range(2):
        throttle.fail("joker|1.2.3.4")
    assert throttle.wait_seconds("joker|1.2.3.4") == 0
    throttle.fail("joker|1.2.3.4")
    assert throttle.wait_seconds("joker|1.2.3.4") == 60
    assert throttle.wait_seconds("ana|1.2.3.4") == 0
    clock.now += 45
    assert throttle.wait_seconds("joker|1.2.3.4") == 15
    clock.now += 15
    assert throttle.wait_seconds("joker|1.2.3.4") == 0


def test_throttle_forgets_failures_after_a_success(clock):
    throttle = Throttle(max_failures=2, window=60, clock=clock)
    throttle.fail("joker")
    throttle.reset("joker")
    throttle.fail("joker")
    assert throttle.wait_seconds("joker") == 0


# --- Estadísticas ---


def test_a_new_account_has_no_stats(store, clock):
    user = store.register("joker", PASSWORD)
    assert store.stats(user) == []
    assert total([]) == LevelStats()
    assert store.member_since(user) == int(clock.now)


def test_each_finished_hand_adds_up(store):
    user = store.register("joker", PASSWORD)
    for outcome in [
        HandOutcome("easy", first_hand=True),
        HandOutcome("easy", chips_won=300, best_hand=6),
        HandOutcome("easy", chips_won=120, best_hand=2),
        HandOutcome("easy", best_hand=4),
        HandOutcome("easy", chips_won=40, game_won=True),
    ]:
        store.record_hand(user, outcome)
    assert store.stats(user) == [
        LevelStats("easy", hands_played=5, hands_won=3, biggest_win=300, best_hand=6,
                   games_played=1, games_won=1)
    ]


def test_stats_are_kept_per_level_and_per_account(store):
    joker, ana = store.register("joker", PASSWORD), store.register("ana", PASSWORD)
    store.record_hand(joker, HandOutcome("easy", chips_won=50, best_hand=3, first_hand=True))
    store.record_hand(joker, HandOutcome("expert", chips_won=900, first_hand=True, game_won=True))
    store.record_hand(joker, HandOutcome("expert"))
    store.record_hand(ana, HandOutcome("easy"))

    easy, expert = store.stats(joker)
    assert (easy.difficulty, easy.hands_played, easy.best_hand) == ("easy", 1, 3)
    assert (expert.difficulty, expert.hands_played, expert.best_hand) == ("expert", 2, None)
    assert total([easy, expert]) == LevelStats(
        hands_played=3, hands_won=2, biggest_win=900, best_hand=3, games_played=2, games_won=1
    )
    assert store.stats(ana) == [LevelStats("easy", hands_played=1)]


def test_a_database_from_before_the_stats_is_upgraded_in_place(tmp_path):
    """Las cuentas creadas con la versión anterior siguen ahí y ya pueden tener estadísticas."""
    path = tmp_path / "antigua.db"
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript(
            """
            CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL,
                username_key TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL);
            CREATE TABLE sessions (token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL);
            PRAGMA user_version = 1;
            """
        )
        db.execute(
            "INSERT INTO users (username, username_key, password_hash, created_at)"
            " VALUES ('Joker', 'joker', ?, 123)",
            (hash_password(PASSWORD, FAST),),
        )
    store = AccountStore(path, FAST)
    user = store.authenticate("joker", PASSWORD)
    assert user is not None and store.member_since(user) == 123
    store.record_hand(user, HandOutcome("medium", chips_won=10))
    assert store.stats(user) == [LevelStats("medium", hands_played=1, hands_won=1, biggest_win=10)]
    assert rows(store, "PRAGMA user_version") == [(2,)]
