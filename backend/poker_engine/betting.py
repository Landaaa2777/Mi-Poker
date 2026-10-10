"""Reglas de una ronda de apuestas No-Limit."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .actions import Action, ActionType, IllegalActionError
from .player import Player


@dataclass(frozen=True, slots=True)
class LegalActions:
    """Lo que puede hacer el jugador en turno. Retirarse siempre es legal."""

    can_check: bool
    call_amount: int  # fichas a añadir para igualar; 0 si puede pasar
    can_raise: bool
    min_raise_to: int  # apuesta total mínima al subir (0 si no puede subir)
    max_raise_to: int  # apuesta total máxima: all-in (0 si no puede subir)


class BettingRound:
    """Una ronda de apuestas sobre los jugadores de la mano.

    `players` son todos los que recibieron cartas, en orden de turno circular.
    `current_bet` es la apuesta a igualar y `min_raise` el incremento mínimo
    para subir, que pasa a ser el del último raise completo de la ronda.
    """

    def __init__(
        self,
        players: Sequence[Player],
        first_index: int,
        current_bet: int,
        min_raise: int,
    ) -> None:
        self.players = list(players)
        self.current_bet = current_bet
        self.last_raise_size = min_raise
        # Apuesta vigente cuando cada jugador actuó por última vez. Decide si
        # un all-in corto posterior le reabre o no la posibilidad de subir.
        self._acted_at: dict[int, int] = {}
        self._index: int | None = None
        self._seek(first_index)

    @property
    def is_complete(self) -> bool:
        return self._index is None

    @property
    def to_act(self) -> Player | None:
        return None if self._index is None else self.players[self._index]

    def _opponents(self, player: Player) -> list[Player]:
        return [p for p in self.players if p is not player and p.live]

    def _target_bet(self, player: Player) -> int:
        """Apuesta que el jugador debe igualar."""
        opponents = self._opponents(player)
        if opponents and all(p.all_in for p in opponents):
            # Nadie más puede apostar: basta cubrir el mayor all-in. Solo
            # difiere de current_bet cuando una ciega se puso incompleta.
            return max(p.bet for p in opponents)
        return self.current_bet

    def _needs_action(self, player: Player) -> bool:
        if not player.can_act:
            return False
        opponents = self._opponents(player)
        if not opponents:
            return False
        if all(p.all_in for p in opponents):
            return player.bet < max(p.bet for p in opponents)
        return player.seat not in self._acted_at or player.bet < self.current_bet

    def _seek(self, start: int) -> None:
        count = len(self.players)
        for offset in range(count):
            index = (start + offset) % count
            if self._needs_action(self.players[index]):
                self._index = index
                return
        self._index = None

    def legal_actions(self) -> LegalActions:
        player = self.to_act
        if player is None:
            raise IllegalActionError("La ronda de apuestas ya terminó")

        to_call = max(0, self._target_bet(player) - player.bet)
        max_raise_to = player.bet + player.stack
        acted_at = self._acted_at.get(player.seat)
        reopened = acted_at is None or self.current_bet - acted_at >= self.last_raise_size
        can_raise = (
            reopened
            and max_raise_to > self.current_bet
            and any(p.can_act for p in self._opponents(player))
        )
        if not can_raise:
            return LegalActions(to_call == 0, min(to_call, player.stack), False, 0, 0)
        # Con menos fichas que el raise mínimo solo se puede subir yendo all-in.
        min_raise_to = min(self.current_bet + self.last_raise_size, max_raise_to)
        return LegalActions(to_call == 0, min(to_call, player.stack), True, min_raise_to, max_raise_to)

    def apply(self, action: Action) -> Action:
        """Valida y ejecuta la acción del jugador en turno.

        Devuelve la acción normalizada: un CALL sin nada que igualar es CHECK,
        y ALL_IN se convierte en el RAISE o CALL equivalente.
        """
        player = self.to_act
        legal = self.legal_actions()
        assert player is not None

        if action.type is ActionType.FOLD:
            player.folded = True
            applied = Action(ActionType.FOLD)
        elif action.type is ActionType.CHECK:
            if not legal.can_check:
                raise IllegalActionError("No puedes pasar: hay una apuesta por igualar")
            applied = Action(ActionType.CHECK)
        elif action.type is ActionType.CALL:
            applied = self._call(player, legal)
        elif action.type is ActionType.ALL_IN:
            if legal.can_raise:
                applied = self._raise_to(player, legal.max_raise_to)
            elif legal.call_amount == player.stack:
                applied = self._call(player, legal)
            else:
                raise IllegalActionError("No puedes subir: la apuesta no se ha reabierto")
        elif action.type is ActionType.RAISE:
            amount = action.amount
            if not legal.can_raise:
                raise IllegalActionError("No puedes subir en este momento")
            if not isinstance(amount, int) or isinstance(amount, bool):
                raise IllegalActionError("El monto debe ser un número entero de fichas")
            if not legal.min_raise_to <= amount <= legal.max_raise_to:
                raise IllegalActionError(
                    f"Monto inválido: debe estar entre {legal.min_raise_to} y {legal.max_raise_to}"
                )
            applied = self._raise_to(player, amount)
        else:
            raise IllegalActionError(f"Acción desconocida: {action.type!r}")

        self._acted_at[player.seat] = self.current_bet
        assert self._index is not None
        self._seek(self._index + 1)
        return applied

    def _call(self, player: Player, legal: LegalActions) -> Action:
        if legal.call_amount == 0:
            return Action(ActionType.CHECK)
        return Action(ActionType.CALL, player.commit(legal.call_amount))

    def _raise_to(self, player: Player, amount: int) -> Action:
        increment = amount - self.current_bet
        player.commit(amount - player.bet)
        if increment >= self.last_raise_size:
            self.last_raise_size = increment
        self.current_bet = amount
        return Action(ActionType.RAISE, amount)
