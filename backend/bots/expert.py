"""Nivel Experto: como Difícil, pero se adapta a cada rival.

Lleva la cuenta de lo que cada rival hace a la vista de todos (cuánto sube,
apuesta, paga y se retira) y usa esas frecuencias en vez de suponer un rival
típico. Con eso ajusta sus rangos, apuesta por valor más fino contra quien paga
de más y calcula cuándo un farol es rentable. Sigue sin ver ninguna carta oculta.
"""

from __future__ import annotations

from dataclasses import dataclass

from poker_engine import TableView

from .base import Spot
from .hard import HardBot, _clamp
from .postflop import HandRead

# Peso de la suposición inicial frente a lo observado, en número de jugadas.
_PRIOR_WEIGHT = 8


@dataclass(slots=True)
class RivalStats:
    """Jugadas públicas de un rival: veces que pudo hacer algo y veces que lo hizo."""

    open_chances: int = 0
    opens: int = 0
    bet_chances: int = 0
    bets: int = 0
    faced_bets: int = 0
    raises: int = 0
    folds: int = 0


class ExpertBot(HardBot):
    level = "expert"
    level_name = "Experto"
    default_simulations = 3000

    size_cap = 2.0
    size_slope = 3.0  # cuánto crece la apuesta de valor con la frecuencia de pago rival

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._stats: dict[str, RivalStats] = {}

    def observe(self, view: TableView) -> None:
        names = {s.seat: s.name for s in view.seats if s.seat != view.viewer_seat}
        preflop = True
        bet_made = False
        for event in view.events:
            if event.kind == "board":
                preflop, bet_made = False, False
                continue
            if event.kind != "action":
                continue
            raised = event.action == "raise"
            if event.seat in names:
                stats = self._stats.setdefault(names[event.seat], RivalStats())
                if not bet_made:
                    if preflop:
                        stats.open_chances += 1
                        stats.opens += raised
                    else:
                        stats.bet_chances += 1
                        stats.bets += raised
                elif not preflop:
                    stats.faced_bets += 1
                    stats.raises += raised
                    stats.folds += event.action == "fold"
            bet_made = bet_made or raised

    def _observed(self, done: int, chances: int, typical: float) -> float:
        """Frecuencia observada, suavizada con la del rival típico al principio."""
        return (done + typical * _PRIOR_WEIGHT) / (chances + _PRIOR_WEIGHT)

    def _rival(self, name: str) -> RivalStats:
        return self._stats.get(name) or RivalStats()

    def _open_frequency(self, name: str) -> float:
        stats = self._rival(name)
        return self._observed(stats.opens, stats.open_chances, self.TYPICAL_OPEN)

    def _bet_frequency(self, name: str) -> float:
        stats = self._rival(name)
        return self._observed(stats.bets, stats.bet_chances, self.TYPICAL_BET)

    def _raise_frequency(self, name: str) -> float:
        stats = self._rival(name)
        return self._observed(stats.raises, stats.faced_bets, self.TYPICAL_RAISE)

    def _call_frequency(self, name: str) -> float:
        stats = self._rival(name)
        folds = self._observed(stats.folds, stats.faced_bets, 1 - self.TYPICAL_CALL)
        return 1 - folds

    def _value_size(self, strength: float, calls: float) -> float:
        # Agresión selectiva: apuesta más grande contra quien paga casi todo.
        center = _clamp(0.65 + self.size_slope * (calls - 0.5), 0.45, self.size_cap)
        if strength >= 0.9:
            center += 0.1
        return center + self.rng.uniform(-0.1, 0.1)

    def _bluff_probability(
        self, spot: Spot, strength: float, read: HandRead, size: float
    ) -> float:
        """Farolea según lo rentable que sea: cuánto se retiran los rivales."""
        style = self.personality
        semi_bluff = read.outs >= 8 and spot.street != "river"
        if strength >= 0.45 and not semi_bluff:
            return 0.0
        all_fold = 1.0
        for rival in spot.rivals:
            all_fold *= 1 - self._call_frequency(rival.name)
        # Un farol de tamaño s (en botes) gana fichas si se retiran más de s / (1 + s).
        edge = all_fold - size / (1 + size)
        if semi_bluff:
            edge += 0.25  # si pagan, el proyecto todavía puede ligar
        if spot.in_position:
            edge += 0.04
        if spot.street == "flop" and spot.preflop_aggressor_seat == spot.me.seat:
            edge += 0.06
        if edge <= 0:
            return 0.03 * style.bluff  # algo de aleatoriedad para no ser predecible
        return min(0.75, (0.1 + 2.0 * edge) * style.bluff)
