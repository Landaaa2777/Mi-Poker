"""Freno a los intentos de inicio de sesión repetidos."""

from __future__ import annotations

import time
from collections.abc import Callable

MAX_KEYS = 10_000  # para que la memoria no crezca sin límite


class Throttle:
    """Tras `max_failures` fallos en `window` segundos, la clave queda bloqueada un rato.

    La clave es lo que identifica a quien lo intenta, por ejemplo la cuenta y
    la dirección desde la que llega. Todo vive en memoria: al reiniciar el
    servidor se olvida.
    """

    def __init__(
        self,
        max_failures: int = 5,
        window: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_failures = max_failures
        self.window = window
        self.clock = clock
        self._failures: dict[str, list[float]] = {}

    def wait_seconds(self, key: str) -> int:
        """Segundos que faltan para poder intentarlo otra vez; 0 si ya se puede."""
        recent = self._recent(key)
        if len(recent) < self.max_failures:
            return 0
        return max(1, round(recent[0] + self.window - self.clock()))

    def fail(self, key: str) -> None:
        recent = self._recent(key)
        recent.append(self.clock())
        if len(self._failures) >= MAX_KEYS and key not in self._failures:
            self._failures.pop(next(iter(self._failures)))  # se olvida la más antigua
        self._failures[key] = recent

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)

    def _recent(self, key: str) -> list[float]:
        """Los fallos de la clave que aún cuentan."""
        oldest = self.clock() - self.window
        recent = [moment for moment in self._failures.get(key, []) if moment > oldest]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent
