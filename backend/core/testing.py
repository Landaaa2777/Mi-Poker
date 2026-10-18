"""Ayudantes para probar las mesas de las salas sin servidor (solo los usan los tests)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from accounts import HandOutcome

from .room import Person, RoomContext


class FakeAccount:
    """Una cuenta en memoria: su saldo cambia con cada mano, como la de verdad."""

    def __init__(self, balance: int = 10_000) -> None:
        self._balance = balance
        self.hands: list[HandOutcome] = []

    def balance(self) -> int:
        return self._balance

    def chips_elsewhere(self) -> int:
        return 0

    def add_chips(self, chips: int) -> None:
        self._balance = max(0, self._balance + chips)

    def hand_finished(self, outcome: HandOutcome) -> None:
        self.hands.append(outcome)
        self.add_chips(outcome.chips_delta)


def room_context(
    options: Any, names: tuple[str, ...] = ("Ana", "Luis"), turn_seconds: float = 30.0
) -> RoomContext:
    """Una sala con esas personas (ids 1, 2, 3…), sin esperas para los bots ni entre manos."""
    people = tuple(Person(index, name, FakeAccount()) for index, name in enumerate(names, start=1))
    return RoomContext(
        people=people,
        options=options,
        bot_delay=(0, 0),
        simulations=30,
        turn_seconds=turn_seconds,
        pause_seconds=0,
    )


async def until(condition: Callable[[], bool], timeout: float = 10.0) -> None:
    """Espera (dejando correr la partida) hasta que se cumpla la condición."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not condition():
        if loop.time() > deadline:
            raise AssertionError("La condición no se cumplió a tiempo")
        await asyncio.sleep(0.005)
