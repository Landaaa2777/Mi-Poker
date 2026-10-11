"""Cuentas y sesiones guardadas en SQLite. Python puro: no sabe nada de FastAPI."""

from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from .passwords import DEFAULT_COST, Cost, hash_password, verify_password
from .stats import HandOutcome, LevelStats

USERNAME_MIN, USERNAME_MAX = 3, 16
PASSWORD_MIN, PASSWORD_MAX = 8, 128
SESSION_SECONDS = 30 * 24 * 3600  # una sesión dura 30 días

_USERNAME = re.compile(r"[A-Za-z0-9_-]+")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    username      TEXT    NOT NULL,           -- tal como lo escribió al registrarse
    username_key  TEXT    NOT NULL UNIQUE,    -- en minúsculas: "Joker" y "joker" son la misma cuenta
    password_hash TEXT    NOT NULL,
    created_at    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT    PRIMARY KEY,           -- el token solo lo tiene el navegador
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS stats (
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    difficulty   TEXT    NOT NULL,            -- nivel de los bots: una fila por nivel jugado
    hands_played INTEGER NOT NULL DEFAULT 0,
    hands_won    INTEGER NOT NULL DEFAULT 0,
    biggest_win  INTEGER NOT NULL DEFAULT 0,
    best_hand    INTEGER NOT NULL DEFAULT 0,  -- categoría de mano; 0 = aún no enseñó ninguna
    games_played INTEGER NOT NULL DEFAULT 0,
    games_won    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, difficulty)
);
"""
# Cada tabla se crea solo si falta, así que una base de datos de una versión
# anterior se pone al día sola al abrirla.
SCHEMA_VERSION = 2


@dataclass(frozen=True)
class User:
    id: int
    username: str


class AccountError(Exception):
    """Algo que el usuario puede corregir; el mensaje es para mostrárselo."""


class UsernameTaken(AccountError):
    pass


def check_username(username: str) -> str:
    """El nombre de usuario limpio, o AccountError si no vale."""
    username = username.strip()
    if not USERNAME_MIN <= len(username) <= USERNAME_MAX:
        raise AccountError(
            f"El nombre de usuario debe tener entre {USERNAME_MIN} y {USERNAME_MAX} caracteres"
        )
    if not _USERNAME.fullmatch(username):
        raise AccountError(
            "El nombre de usuario solo puede llevar letras sin acento, números, guion y guion bajo"
        )
    return username


def check_password(password: str) -> str:
    if len(password) < PASSWORD_MIN:
        raise AccountError(f"La contraseña debe tener al menos {PASSWORD_MIN} caracteres")
    if len(password) > PASSWORD_MAX:
        raise AccountError(f"La contraseña no puede pasar de {PASSWORD_MAX} caracteres")
    return password


def token_hash(token: str) -> str:
    """Lo que se guarda de un token de sesión. Quien lea la base de datos no puede usarlo."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AccountStore:
    """Usuarios y sesiones. La base de datos no se crea hasta que hace falta."""

    def __init__(
        self,
        path: Path | str,
        cost: Cost = DEFAULT_COST,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.path = Path(path)
        self.cost = cost
        self.clock = clock
        self._ready = False
        self._setup_lock = threading.Lock()

    # --- Cuentas ---

    def register(self, username: str, password: str) -> User:
        username = check_username(username)
        hashed = hash_password(check_password(password), self.cost)
        try:
            with self._connect() as db:
                cursor = db.execute(
                    "INSERT INTO users (username, username_key, password_hash, created_at)"
                    " VALUES (?, ?, ?, ?)",
                    (username, username.lower(), hashed, int(self.clock())),
                )
        except sqlite3.IntegrityError:
            raise UsernameTaken("Ese nombre de usuario ya está en uso") from None
        assert cursor.lastrowid is not None
        return User(cursor.lastrowid, username)

    def authenticate(self, username: str, password: str) -> User | None:
        """El usuario, si la contraseña es la suya. No distingue por qué falla."""
        with self._connect() as db:
            row = db.execute(
                "SELECT id, username, password_hash FROM users WHERE username_key = ?",
                (username.strip().lower(),),
            ).fetchone()
        if len(password) > PASSWORD_MAX:
            return None
        if row is None:
            verify_password(password, self._decoy)
            return None
        return User(row[0], row[1]) if verify_password(password, row[2]) else None

    # --- Sesiones ---

    def create_session(self, user: User) -> str:
        """Abre una sesión y devuelve su token, que solo debe conocer el navegador."""
        token = secrets.token_urlsafe(32)
        now = int(self.clock())
        with self._connect() as db:
            db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
            db.execute(
                "INSERT INTO sessions (token_hash, user_id, created_at, expires_at)"
                " VALUES (?, ?, ?, ?)",
                (token_hash(token), user.id, now, now + SESSION_SECONDS),
            )
        return token

    def user_for_token(self, token: str | None) -> User | None:
        if not token or not self.path.exists():
            return None
        with self._connect() as db:
            row = db.execute(
                "SELECT users.id, users.username FROM sessions"
                " JOIN users ON users.id = sessions.user_id"
                " WHERE sessions.token_hash = ? AND sessions.expires_at > ?",
                (token_hash(token), int(self.clock())),
            ).fetchone()
        return User(row[0], row[1]) if row else None

    def delete_session(self, token: str | None) -> None:
        if not token or not self.path.exists():
            return
        with self._connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))

    # --- Perfil y estadísticas ---

    def member_since(self, user: User) -> int | None:
        """Cuándo se creó la cuenta, en segundos desde 1970."""
        with self._connect() as db:
            row = db.execute("SELECT created_at FROM users WHERE id = ?", (user.id,)).fetchone()
        return row[0] if row else None

    def record_hand(self, user: User, outcome: HandOutcome) -> None:
        """Suma una mano terminada a las estadísticas de la cuenta."""
        with self._connect() as db:
            db.execute(
                "INSERT INTO stats (user_id, difficulty, hands_played, hands_won, biggest_win,"
                " best_hand, games_played, games_won) VALUES (?, ?, 1, ?, ?, ?, ?, ?)"
                " ON CONFLICT (user_id, difficulty) DO UPDATE SET"
                " hands_played = hands_played + 1,"
                " hands_won = hands_won + excluded.hands_won,"
                " biggest_win = MAX(biggest_win, excluded.biggest_win),"
                " best_hand = MAX(best_hand, excluded.best_hand),"
                " games_played = games_played + excluded.games_played,"
                " games_won = games_won + excluded.games_won",
                (
                    user.id,
                    outcome.difficulty,
                    int(outcome.chips_won > 0),
                    outcome.chips_won,
                    outcome.best_hand or 0,
                    int(outcome.first_hand),
                    int(outcome.game_won),
                ),
            )

    def stats(self, user: User) -> list[LevelStats]:
        """Lo acumulado por la cuenta contra cada nivel que ha jugado."""
        with self._connect() as db:
            found = db.execute(
                "SELECT difficulty, hands_played, hands_won, biggest_win, best_hand,"
                " games_played, games_won FROM stats WHERE user_id = ? ORDER BY difficulty",
                (user.id,),
            ).fetchall()
        return [
            LevelStats(level, played, won, biggest, best or None, games, games_won)
            for level, played, won, biggest, best, games, games_won in found
        ]

    # --- Interno ---

    @cached_property
    def _decoy(self) -> str:
        """Hash de una contraseña que nadie tiene.

        Se verifica contra él cuando el usuario no existe, para que la
        respuesta tarde lo mismo que si existiera.
        """
        return hash_password(secrets.token_urlsafe(16), self.cost)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Una conexión por operación: se confirma al salir bien y se cierra siempre."""
        self._setup()
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            db.execute("PRAGMA foreign_keys = ON")
            with db:
                yield db

    def _setup(self) -> None:
        if self._ready:
            return
        with self._setup_lock:
            if self._ready:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(self.path, timeout=5)) as db:
                with db:
                    db.executescript(_SCHEMA)
                    db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self._ready = True
