"""Nivel Medio: juego ordenado y directo.

Elige sus manos por la fuerza de las cartas iniciales, compara los outs de sus
proyectos con las pot odds y respeta las apuestas grandes. Casi no hace farol.
"""

from __future__ import annotations

from poker_engine import Action

from .base import CALL, FOLD, Bot, Spot
from .postflop import read_hand
from .preflop import top_fraction

# Rango de apertura según cuántos rivales quedan por hablar.
_OPEN_RANGE = {0: 0.45, 1: 0.45, 2: 0.32, 3: 0.24, 4: 0.18, 5: 0.14}


class MediumBot(Bot):
    level = "medium"
    level_name = "Medio"

    def _choose(self, spot: Spot) -> Action:
        return self._preflop(spot) if spot.preflop else self._postflop(spot)

    def _preflop(self, spot: Spot) -> Action:
        style = self.personality
        top = top_fraction(spot.hole) * style.tightness
        bb = spot.big_blind

        if spot.raises == 0:
            if spot.to_call == 0:  # ciega grande sin subidas
                return self._raise(spot, (3 + spot.limpers) * bb) if top <= 0.08 else CALL
            if top <= _OPEN_RANGE[min(spot.seats_behind, 5)]:
                return self._raise(spot, (3 + spot.limpers) * bb)
            if spot.to_call < bb and top <= 0.55:  # completar la ciega pequeña
                return CALL
            if spot.limpers and top <= 0.4:
                return CALL
            return FOLD

        committed = spot.to_call > 0.3 * (spot.stack + spot.to_call)
        if spot.raises == 1 and not committed:
            if top <= 0.035:
                return self._raise(spot, 3 * spot.view.current_bet)
            size = spot.view.current_bet / bb
            call_range = 0.16 if size <= 5 else 0.08 if size <= 12 else 0.04
            return CALL if top <= call_range else FOLD

        # Resubidas o apuestas que comprometen el stack: solo manos premium.
        if top <= 0.012:
            return self._raise(spot, spot.legal.max_raise_to)
        if top <= 0.035 and not committed:
            return CALL
        return FOLD

    def _postflop(self, spot: Spot) -> Action:
        style = self.personality
        read = read_hand(spot.hole, spot.board)
        strength = read.strength

        if spot.to_call == 0:
            if strength >= 0.85:
                return self._raise(spot, spot.bet_to(0.75))
            if strength >= 0.62 / style.aggression:
                return self._raise(spot, spot.bet_to(0.6))
            continuation = (
                spot.street == "flop"
                and spot.opponents == 1
                and spot.preflop_aggressor_seat == spot.me.seat
            )
            if continuation and self._chance(0.4 * style.bluff):
                return self._raise(spot, spot.bet_to(0.5))
            return CALL

        # Cuanto más grande la apuesta, mejor mano hace falta para seguir.
        size = spot.bet_fraction
        needed = 0.42 if size <= 0.35 else 0.55 if size <= 0.7 else 0.68 if size <= 1.1 else 0.8
        needed += 0.06 * max(0, spot.raises - 1) + 0.03 * max(0, spot.opponents - 1)
        needed = min(0.9, needed * (0.9 + 0.1 * style.tightness))

        if strength >= 0.88 and (spot.raises <= 1 or strength >= 0.95):
            return self._raise(spot, spot.bet_to(0.8))
        if strength >= needed:
            return CALL
        cards_to_come = 5 - len(spot.board)
        if read.draw_equity(min(cards_to_come, 1)) >= spot.pot_odds:
            return CALL
        return FOLD
