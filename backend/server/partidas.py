"""Partidas en memoria: una por identidad (cuenta o invitado) y por juego.

Cada partida tiene un id largo y al azar. El navegador lo pide por HTTP
(`POST /api/partidas`) y con él se conecta a `/ws/{juego}/{partida_id}`. El id
va ligado a su dueño: si otra identidad intenta usarlo, el servidor la rechaza.

Las partidas no se guardan en disco: se pierden al apagar el servidor.
"""

from __future__ import annotations

import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass

from accounts import User
from core.session import GameSession

MAX_PARTIDAS = 500  # con más, se descarta la más antigua

_GUEST_ID = re.compile(r"[A-Za-z0-9_-]{8,64}")


def owner_key(user: User | None, guest_id: str | None) -> str | None:
    """Quién es el dueño de una partida: su cuenta o, sin ella, su identificador de invitado.

    Devuelve None si no hay cuenta y el identificador de invitado no vale. Los
    identificadores de invitado no llevan ":", así que no chocan con las cuentas.

    >>> owner_key(None, "invitado-123")
    'invitado-123'
    >>> owner_key(None, "corto") is None
    True
    """
    if user is not None:
        return f"user:{user.id}"
    if guest_id and _GUEST_ID.fullmatch(guest_id):
        return guest_id
    return None


@dataclass
class Partida:
    id: str  # secreto: quien lo tiene puede conectarse, si además es el dueño
    game: str  # id del juego, como en el registro: "poker", "blackjack"…
    owner: str  # ver `owner_key`
    session: GameSession  # la partida en sí, que sabe jugar a su juego


class Partidas:
    """Todas las partidas abiertas del servidor."""

    def __init__(self, limit: int = MAX_PARTIDAS) -> None:
        self.limit = limit
        self._by_id: dict[str, Partida] = {}  # en orden de creación
        self._by_owner: dict[tuple[str, str], str] = {}  # (dueño, juego) -> id

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, partida_id: str) -> Partida | None:
        return self._by_id.get(partida_id)

    def find(self, owner: str, game: str) -> Partida | None:
        """La partida de `owner` en ese juego, si tiene una."""
        partida_id = self._by_owner.get((owner, game))
        return self._by_id.get(partida_id) if partida_id else None

    def of_owner(self, owner: str) -> list[Partida]:
        """Todas las partidas de una identidad, una por juego como mucho."""
        return [partida for partida in self._by_id.values() if partida.owner == owner]

    def open(self, owner: str, game: str, create: Callable[[str], GameSession]) -> Partida:
        """La partida de `owner` en ese juego. Si no tiene, se crea con `create(partida_id)`."""
        existing = self.find(owner, game)
        if existing is not None:
            return existing
        if len(self._by_id) >= self.limit:
            self._discard(next(iter(self._by_id)))
        partida_id = secrets.token_urlsafe(16)
        partida = Partida(partida_id, game, owner, create(partida_id))
        self._by_id[partida_id] = partida
        self._by_owner[owner, game] = partida_id
        return partida

    def chips_elsewhere(self, owner: str, partida_id: str) -> int:
        """Fichas que `owner` tiene sentadas en sus otras mesas: no las puede llevar a esta."""
        return sum(
            partida.session.seated_chips()
            for partida in self.of_owner(owner)
            if partida.id != partida_id
        )

    def _discard(self, partida_id: str) -> None:
        partida = self._by_id.pop(partida_id)
        del self._by_owner[partida.owner, partida.game]
        partida.session.close()
