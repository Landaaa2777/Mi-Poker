"""Nivel Difícil: equity por Monte Carlo, pot odds, posición y faroles ocasionales.

Estima con simulación la probabilidad de ganar a una mano al azar y la compara
con lo que suele tener un rival que apuesta. Para eso supone que todos los
rivales juegan como un jugador "típico" (las constantes `TYPICAL_*`).
"""

from __future__ import annotations

from poker_engine import Action

from .base import CALL, FOLD, Bot, Spot
from .equity import estimate_equity
from .postflop import HandRead, read_hand
from .preflop import top_fraction

# Rango de apertura según cuántos rivales quedan por hablar.
_OPEN_RANGE = {0: 0.5, 1: 0.5, 2: 0.4, 3: 0.28, 4: 0.21, 5: 0.16}
_HEADS_UP_OPEN_RANGE = 0.72
_SHORT_STACK_BB = 12


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class HardBot(Bot):
    level = "hard"
    level_name = "Difícil"
    default_simulations = 2000

    # Cómo juega el rival típico que este nivel da por supuesto.
    TYPICAL_OPEN = 0.22  # fracción de manos con las que sube preflop
    TYPICAL_BET = 0.40  # frecuencia con la que apuesta si nadie apostó
    TYPICAL_RAISE = 0.08  # frecuencia con la que sube una apuesta
    TYPICAL_CALL = 0.50  # frecuencia con la que sigue ante una apuesta

    range_scale = 0.85  # < 1 ensancha todos los rangos preflop, > 1 los estrecha
    bluff_base = 0.12
    value_edge = 0.5  # parte de las manos que pagan a la que hay que ganar para apostar
    raise_ahead = 0.7  # ventaja mínima sobre el rango rival para subir una apuesta
    call_margin = 0.06  # equity extra sobre las pot odds para igualar (la mitad en el river)

    # --- Lo que el bot cree de cada rival (el nivel Experto lo sustituye) ---

    def _open_frequency(self, name: str) -> float:
        return self.TYPICAL_OPEN

    def _bet_frequency(self, name: str) -> float:
        return self.TYPICAL_BET

    def _raise_frequency(self, name: str) -> float:
        return self.TYPICAL_RAISE

    def _call_frequency(self, name: str) -> float:
        return self.TYPICAL_CALL

    # --- Decisión ---

    def _choose(self, spot: Spot) -> Action:
        return self._preflop(spot) if spot.preflop else self._postflop(spot)

    def _aggressor_name(self, spot: Spot) -> str:
        seat = spot.aggressor_seat
        return next((s.name for s in spot.view.seats if s.seat == seat), "")

    def _preflop(self, spot: Spot) -> Action:
        style = self.personality
        top = top_fraction(spot.hole) * style.tightness * self.range_scale
        bb = spot.big_blind

        if spot.raises == 0:
            return self._open(spot, top)

        raiser_range = self._open_frequency(self._aggressor_name(spot))
        if spot.raises == 1:
            # Una subida grande suele venir de una mano mejor.
            raiser_range *= min(1.0, (3 * bb / spot.view.current_bet) ** 0.5)
        elif spot.raises == 2:
            raiser_range *= 0.25
        else:
            raiser_range *= 0.1
        raiser_range = _clamp(raiser_range, 0.015, 0.8)

        committed = spot.to_call > 0.3 * (spot.stack + spot.to_call)
        if committed or spot.raises >= 3:
            # Decisión por todo el stack: equity simulada contra el rango del rival.
            equity = estimate_equity(
                spot.hole, (), 1, self.simulations, self.rng, ranges=[raiser_range]
            )
            if equity < spot.pot_odds + 0.03:
                return FOLD
            return self._raise(spot, spot.legal.max_raise_to) if equity >= 0.6 else CALL

        if top <= 0.2 * raiser_range:
            multiple = 3.0 if spot.in_position else 3.6
            return self._raise(spot, multiple * spot.view.current_bet)
        call_range = 0.65 * raiser_range
        if spot.in_position or spot.me.bet >= bb:
            call_range *= 1.3  # con posición, o ya con la ciega grande puesta
        if top <= call_range:
            return CALL
        if spot.raises == 1 and spot.in_position and top <= 1.6 * call_range:
            if self._chance(0.1 * style.bluff):
                return self._raise(spot, 3 * spot.view.current_bet)
        return FOLD

    def _open(self, spot: Spot, top: float) -> Action:
        """Nadie ha subido todavía."""
        style = self.personality
        bb = spot.big_blind
        open_range = _OPEN_RANGE[min(spot.seats_behind, 5)]
        if spot.players_dealt == 2 and spot.to_call > 0:
            open_range = _HEADS_UP_OPEN_RANGE
        size = (self.rng.uniform(2.2, 3.0) + spot.limpers) * bb

        if spot.to_call == 0:  # ciega grande sin subidas
            return self._raise(spot, size + bb) if top <= 0.12 * style.aggression else CALL
        if top <= open_range:
            if spot.stack + spot.me.bet <= _SHORT_STACK_BB * bb:
                return self._raise(spot, spot.legal.max_raise_to)
            return self._raise(spot, size)
        if spot.to_call < bb and top <= 0.6:  # completar la ciega pequeña
            return CALL
        if spot.limpers and top <= 0.35:
            return CALL
        return FOLD

    def _postflop(self, spot: Spot) -> Action:
        # Probabilidad de ganar en el showdown a una mano cualquiera.
        strength = estimate_equity(spot.hole, spot.board, 1, self.simulations, self.rng)
        read = read_hand(spot.hole, spot.board)
        if spot.to_call == 0:
            return self._lead(spot, strength, read)
        return self._respond(spot, strength, read)

    def _lead(self, spot: Spot, strength: float, read: HandRead) -> Action:
        """Nadie ha apostado en esta calle: apostar por valor, farolear o pasar."""
        style = self.personality
        rivals = spot.opponents
        calls = sum(self._call_frequency(s.name) for s in spot.rivals) / rivals
        # Apostar por valor compensa si se gana a más de la mitad de las manos que pagan.
        value_line = 1 - calls * self.value_edge * style.aggression / rivals**0.6
        river = spot.street == "river"

        if strength >= value_line:
            if strength >= 0.93 and not river and not spot.in_position and self._chance(0.2):
                return CALL  # trampa: pasar para subir después
            size = self._value_size(strength, calls)
            return self._raise(spot, spot.bet_to(size))

        size = self.rng.uniform(0.5, 0.75)
        if self._chance(self._bluff_probability(spot, strength, read, size)):
            return self._raise(spot, spot.bet_to(size))
        return CALL

    def _value_size(self, strength: float, calls: float) -> float:
        """Tamaño de la apuesta por valor, en botes: variable y mayor con manos muy fuertes."""
        low, high = (0.75, 1.1) if strength >= 0.9 else (0.6, 0.85)
        return self.rng.uniform(low, high)

    def _bluff_probability(
        self, spot: Spot, strength: float, read: HandRead, size: float
    ) -> float:
        style = self.personality
        river = spot.street == "river"
        if read.outs >= 8 and not river:
            chance = 0.45  # semifarol con proyecto fuerte
        elif strength < 0.45:
            chance = self.bluff_base
            if spot.in_position:
                chance *= 1.5
            if spot.street == "flop" and spot.preflop_aggressor_seat == spot.me.seat:
                chance *= 2.5  # apuesta de continuación
        else:
            return 0.0  # mano con valor de showdown: mejor ver cartas gratis
        crowd = {1: 1.0, 2: 0.4}.get(spot.opponents, 0.1)
        return chance * crowd * style.bluff

    def _respond(self, spot: Spot, strength: float, read: HandRead) -> Action:
        """Hay una apuesta por igualar: subir, igualar o retirarse."""
        style = self.personality
        name = self._aggressor_name(spot)
        river = spot.street == "river"

        # Fracción de manos con las que el rival apuesta así, y cuántas son farol.
        if spot.raises >= 2:
            betting_range = _clamp(self._raise_frequency(name) * 1.6, 0.03, 0.4)
            if spot.raises >= 3:
                betting_range *= 0.5
            bluffs = 0.05
        else:
            frequency = self._bet_frequency(name)
            betting_range = _clamp(frequency * (1.25 - 0.5 * spot.bet_fraction), 0.05, 0.75)
            bluffs = _clamp(frequency - 0.25, 0.02, 0.35)

        # Probabilidad de ir por delante de las manos de valor de ese rango.
        ahead = _clamp((strength - (1 - betting_range)) / betting_range, 0.0, 1.0)
        equity = (1 - bluffs) * ahead + bluffs * min(1.0, strength / 0.5)
        equity *= strength ** (0.5 * (spot.opponents - 1))
        equity = max(equity, read.draw_equity(5 - len(spot.board)) * 0.85)

        if ahead >= self.raise_ahead and spot.raises <= 2 and self._chance(0.85 * style.aggression):
            return self._raise(spot, spot.bet_to(self.rng.uniform(0.7, 1.0)))

        margin = self.call_margin / 2 if river else self.call_margin
        if not spot.in_position:
            margin += 0.02
        if equity >= spot.pot_odds + margin * style.tightness:
            return CALL
        if read.outs >= 8 and not river and spot.raises == 1:
            if self._chance(0.12 * style.bluff):
                return self._raise(spot, spot.bet_to(0.8))
        return FOLD
