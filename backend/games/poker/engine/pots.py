"""Bote principal, side pots y reparto."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

from .evaluator import HandValue


@dataclass(frozen=True, slots=True)
class Pot:
    amount: int
    eligible: tuple[int, ...]  # asientos que pueden ganarlo


@dataclass(frozen=True, slots=True)
class PotAward:
    amount: int
    eligible: tuple[int, ...]
    winners: tuple[int, ...]
    payouts: dict[int, int]  # asiento -> fichas recibidas de este bote


def build_pots(contributions: Mapping[int, int], folded: Collection[int]) -> list[Pot]:
    """Divide lo aportado en bote principal y side pots.

    `contributions` es lo que cada asiento puso en toda la mano. Hay un bote
    por cada nivel de aportación de los jugadores no retirados; las fichas de
    los retirados se quedan en los botes, pero ellos no pueden ganarlos.
    """
    levels = sorted({c for seat, c in contributions.items() if seat not in folded and c > 0})
    pots: list[Pot] = []
    previous = 0
    for level in levels:
        amount = sum(min(c, level) - min(c, previous) for c in contributions.values())
        eligible = tuple(
            sorted(seat for seat, c in contributions.items() if seat not in folded and c >= level)
        )
        pots.append(Pot(amount, eligible))
        previous = level

    # Fichas de retirados por encima del nivel más alto: van al último bote.
    leftover = sum(max(0, c - previous) for c in contributions.values())
    if leftover:
        if not pots:
            raise ValueError("Hay fichas en el bote pero ningún jugador puede ganarlas")
        pots[-1] = Pot(pots[-1].amount + leftover, pots[-1].eligible)
    return pots


def award_pots(
    pots: Sequence[Pot],
    hand_values: Mapping[int, HandValue],
    odd_chip_order: Sequence[int],
) -> list[PotAward]:
    """Reparte cada bote entre las mejores manos de sus jugadores elegibles.

    En un empate el bote se divide a partes iguales. Las fichas indivisibles
    se dan de una en una siguiendo `odd_chip_order`, que lista los asientos
    empezando por el primero a la izquierda del botón.
    """
    awards: list[PotAward] = []
    for pot in pots:
        best = max(hand_values[seat] for seat in pot.eligible)
        winners = [
            seat for seat in odd_chip_order if seat in pot.eligible and hand_values[seat] == best
        ]
        share, remainder = divmod(pot.amount, len(winners))
        payouts = {seat: share for seat in winners}
        for seat in winners[:remainder]:
            payouts[seat] += 1
        awards.append(PotAward(pot.amount, pot.eligible, tuple(winners), payouts))
    return awards
