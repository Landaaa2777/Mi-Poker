"""Nivel Fácil: suelto y pasivo.

Juega demasiadas manos, iguala casi todo, apuesta poco con manos fuertes y
casi nunca hace farol. Sus errores son los típicos de un principiante.
"""

from __future__ import annotations

from poker_engine import Action

from .base import CALL, FOLD, Bot, Spot
from .postflop import read_hand
from .preflop import top_fraction


class EasyBot(Bot):
    level = "easy"
    level_name = "Fácil"

    def _choose(self, spot: Spot) -> Action:
        return self._preflop(spot) if spot.preflop else self._postflop(spot)

    def _preflop(self, spot: Spot) -> Action:
        style = self.personality
        top = top_fraction(spot.hole)
        # Con una mano excelente sube, pero solo el mínimo.
        if top <= 0.04 and spot.raises <= 1 and self._chance(0.5 * style.aggression):
            return self._raise(spot, spot.legal.min_raise_to)
        if spot.to_call == 0:
            return CALL

        price = spot.to_call / (spot.stack + spot.to_call)
        if spot.to_call <= spot.big_blind:
            limit = 0.8
        elif price <= 0.1:
            limit = 0.65
        elif price <= 0.35:
            limit = 0.4
        else:
            limit = 0.18
        return CALL if top <= limit / style.tightness else FOLD

    def _postflop(self, spot: Spot) -> Action:
        style = self.personality
        read = read_hand(spot.hole, spot.board)
        small_bet = spot.bet_to(1 / 3)

        if spot.to_call == 0:
            if read.strength >= 0.85 and self._chance(0.6 * style.aggression):
                return self._raise(spot, small_bet)
            if read.strength >= 0.6 and self._chance(0.3 * style.aggression):
                return self._raise(spot, small_bet)
            if self._chance(0.03 * style.bluff):
                return self._raise(spot, small_bet)
            return CALL

        if read.strength >= 0.85 and self._chance(0.3 * style.aggression):
            return self._raise(spot, spot.legal.min_raise_to)
        # Con cualquier pareja o proyecto no suelta la mano, cueste lo que cueste.
        if read.strength >= 0.4 or read.outs >= 4:
            return CALL
        if spot.bet_fraction <= 0.5 and self._chance(0.5 / style.tightness):
            return CALL
        return FOLD
