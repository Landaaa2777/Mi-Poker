"""Cuentas de usuario: registro, contraseñas, sesiones y estadísticas.

Python puro y sin dependencias: se prueba solo con pytest. El servidor web
está en `server/`; aquí no hay nada de FastAPI.
"""

from .passwords import DEFAULT_COST, Cost, hash_password, verify_password
from .stats import HandOutcome, LevelStats, total
from .store import (
    PASSWORD_MAX,
    PASSWORD_MIN,
    SESSION_SECONDS,
    USERNAME_MAX,
    USERNAME_MIN,
    AccountError,
    AccountStore,
    User,
    UsernameTaken,
    check_password,
    check_username,
    token_hash,
)
from .throttle import Throttle

__all__ = [
    "DEFAULT_COST",
    "PASSWORD_MAX",
    "PASSWORD_MIN",
    "SESSION_SECONDS",
    "USERNAME_MAX",
    "USERNAME_MIN",
    "AccountError",
    "AccountStore",
    "Cost",
    "HandOutcome",
    "LevelStats",
    "Throttle",
    "User",
    "UsernameTaken",
    "check_password",
    "check_username",
    "hash_password",
    "token_hash",
    "total",
    "verify_password",
]
