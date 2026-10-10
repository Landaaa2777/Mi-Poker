"""Contraseñas: se guarda un hash con sal, nunca la contraseña.

El hash es scrypt, una función lenta a propósito y que gasta memoria: probar
contraseñas por fuerza bruta contra una base de datos robada sale caro. Cada
contraseña lleva su propia sal, así que dos iguales dan hashes distintos.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import unicodedata
from dataclasses import dataclass

SALT_BYTES = 16
KEY_BYTES = 32
MAX_MEMORY = 2**27  # 128 MiB: tope de memoria de una derivación
MAX_N = 2**20  # un hash guardado no puede pedir más trabajo que este


@dataclass(frozen=True)
class Cost:
    """Cuánto cuesta calcular un hash. Los valores por defecto siguen a OWASP."""

    n: int = 2**15
    r: int = 8
    p: int = 3


DEFAULT_COST = Cost()


def hash_password(password: str, cost: Cost = DEFAULT_COST) -> str:
    """Hash listo para guardar. Lleva dentro el coste y la sal para poder verificarlo."""
    salt = secrets.token_bytes(SALT_BYTES)
    key = _derive(password, salt, cost, KEY_BYTES)
    return f"scrypt${cost.n}${cost.r}${cost.p}${salt.hex()}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """¿Es esta la contraseña del hash guardado? Un hash ilegible cuenta como que no."""
    try:
        scheme, n, r, p, salt, key = stored.split("$")
        cost = Cost(int(n), int(r), int(p))
        expected = bytes.fromhex(key)
        if scheme != "scrypt" or cost.n > MAX_N or not expected:
            return False
        derived = _derive(password, bytes.fromhex(salt), cost, len(expected))
    except ValueError:
        return False
    # Comparación en tiempo constante: no delata cuántos bytes coinciden.
    return hmac.compare_digest(derived, expected)


def _derive(password: str, salt: bytes, cost: Cost, length: int) -> bytes:
    # La misma contraseña puede teclearse con bytes distintos según el sistema
    # (una "é" de una pieza o de dos): se normaliza antes de derivar.
    normalized = unicodedata.normalize("NFKC", password).encode("utf-8")
    return hashlib.scrypt(
        normalized, salt=salt, n=cost.n, r=cost.r, p=cost.p, maxmem=MAX_MEMORY, dklen=length
    )
