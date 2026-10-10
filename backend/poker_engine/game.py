"""Partida de varias manos: configuración, botón, eliminación y reinicio."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .deck import Deck
from .hand import Hand
from .player import Player

MIN_PLAYERS = 2
MAX_PLAYERS = 6

_SYSTEM_RNG = random.SystemRandom()


class GameStateError(RuntimeError):
    """La operación no es posible en el estado actual de la partida."""


@dataclass(frozen=True, slots=True)
class GameConfig:
    """Configuración elegida antes de empezar. Las fichas son virtuales."""

    player_names: tuple[str, ...]
    starting_stack: int = 1000
    small_blind: int = 5
    big_blind: int = 10

    def __post_init__(self) -> None:
        if not MIN_PLAYERS <= len(self.player_names) <= MAX_PLAYERS:
            raise ValueError(f"La mesa admite de {MIN_PLAYERS} a {MAX_PLAYERS} jugadores")
        for value in (self.starting_stack, self.small_blind, self.big_blind):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError("Fichas y blinds deben ser enteros positivos")
        if self.small_blind > self.big_blind:
            raise ValueError("La ciega pequeña no puede superar a la grande")
        if self.starting_stack < self.big_blind:
            raise ValueError("Las fichas iniciales deben cubrir al menos la ciega grande")


class Game:
    """Estado de la mesa entre manos. Todo vive en memoria."""

    def __init__(self, config: GameConfig, button_seat: int | None = None) -> None:
        if button_seat is not None and not 0 <= button_seat < len(config.player_names):
            raise ValueError("Asiento de botón inválido")
        self.config = config
        self._initial_button = button_seat
        self.reset()

    def reset(self) -> None:
        """Reinicia la partida: todos vuelven a las fichas iniciales."""
        self.players = [
            Player(seat, name, self.config.starting_stack)
            for seat, name in enumerate(self.config.player_names)
        ]
        self.hand: Hand | None = None
        self.hand_number = 0
        self.button_seat: int | None = None

    @property
    def hand_in_progress(self) -> bool:
        return self.hand is not None and not self.hand.is_complete

    @property
    def is_over(self) -> bool:
        """Queda un solo jugador con fichas."""
        return not self.hand_in_progress and sum(p.stack > 0 for p in self.players) < 2

    @property
    def winner(self) -> Player | None:
        if not self.is_over:
            return None
        return next((p for p in self.players if p.stack > 0), None)

    @property
    def total_chips(self) -> int:
        """Todas las fichas de la mesa: stacks más el bote de la mano en curso."""
        in_pot = self.hand.pot if self.hand is not None and self.hand_in_progress else 0
        return sum(p.stack for p in self.players) + in_pot

    def start_hand(self, deck: Deck | None = None) -> Hand:
        if self.hand_in_progress:
            raise GameStateError("Ya hay una mano en curso")
        if self.is_over:
            raise GameStateError("La partida terminó: queda un solo jugador con fichas")
        self.button_seat = self._next_button()
        self.hand_number += 1
        self.hand = Hand(
            self.players,
            self.button_seat,
            self.config.small_blind,
            self.config.big_blind,
            deck=deck,
            number=self.hand_number,
        )
        return self.hand

    def _next_button(self) -> int:
        seats = [p.seat for p in self.players if p.stack > 0]
        if self.button_seat is None:
            if self._initial_button is not None and self._initial_button in seats:
                return self._initial_button
            return _SYSTEM_RNG.choice(seats)
        # El botón pasa al siguiente jugador con fichas, en sentido horario.
        return next((s for s in seats if s > self.button_seat), seats[0])
