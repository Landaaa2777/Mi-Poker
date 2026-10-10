"""Una mano completa: blinds, calles, showdown y pago."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from .actions import Action, IllegalActionError
from .betting import BettingRound, LegalActions
from .cards import Card
from .deck import Deck
from .evaluator import HandValue, evaluate
from .player import Player
from .pots import PotAward, award_pots, build_pots


class Phase(StrEnum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    COMPLETE = "complete"


_NEXT_STREET = {
    Phase.PREFLOP: (Phase.FLOP, 3),
    Phase.FLOP: (Phase.TURN, 1),
    Phase.TURN: (Phase.RIVER, 1),
}


@dataclass(frozen=True, slots=True)
class HandEvent:
    """Suceso público de la mano. Nunca lleva cartas ocultas.

    `kind` es uno de: small_blind, big_blind, action, board, refund, show, win.
    En `action`, `amount` son las fichas pagadas (call) o la apuesta total (raise).
    """

    kind: str
    seat: int | None = None
    amount: int = 0
    action: str = ""
    cards: tuple[Card, ...] = ()
    all_in: bool = False


@dataclass(frozen=True, slots=True)
class HandResult:
    showdown: bool
    board: tuple[Card, ...]
    awards: tuple[PotAward, ...]
    payouts: dict[int, int]  # asiento -> total ganado
    shown_hands: dict[int, tuple[Card, ...]]  # solo manos que llegaron al showdown
    hand_values: dict[int, HandValue]


class Hand:
    """Máquina de estados de una mano. Se crea ya repartida y lista para jugar."""

    def __init__(
        self,
        players: Sequence[Player],
        button_seat: int,
        small_blind: int,
        big_blind: int,
        deck: Deck | None = None,
        number: int = 1,
    ) -> None:
        for player in players:
            player.reset_for_hand()
        seated = sorted((p for p in players if p.in_hand), key=lambda p: p.seat)
        if len(seated) < 2:
            raise ValueError("Se necesitan al menos 2 jugadores con fichas")
        if all(p.seat != button_seat for p in seated):
            raise ValueError("El botón debe estar en un jugador con fichas")

        self.number = number
        self.button_seat = button_seat
        self.small_blind = small_blind
        self.big_blind = big_blind
        # Orden de turno: empieza a la izquierda del botón; el botón es el último.
        self.order = [p for p in seated if p.seat > button_seat] + [
            p for p in seated if p.seat <= button_seat
        ]
        self.board: list[Card] = []
        self.events: list[HandEvent] = []
        self.result: HandResult | None = None
        self.phase = Phase.PREFLOP
        self._deck = deck if deck is not None else Deck()

        if len(self.order) == 2:
            # Mano a mano: el botón pone la ciega pequeña y habla primero preflop.
            sb_player, bb_player = self.order[1], self.order[0]
            first_index = 1
        else:
            sb_player, bb_player = self.order[0], self.order[1]
            first_index = 2 % len(self.order)
        self.small_blind_seat = sb_player.seat
        self.big_blind_seat = bb_player.seat

        for _ in range(2):
            for player in self.order:
                player.hole_cards.extend(self._deck.deal())

        self._post_blind("small_blind", sb_player, small_blind)
        self._post_blind("big_blind", bb_player, big_blind)

        # Una ciega incompleta no rebaja la apuesta a igualar: sigue siendo la grande.
        self.round = BettingRound(self.order, first_index, big_blind, big_blind)
        self._advance()

    @property
    def is_complete(self) -> bool:
        return self.phase is Phase.COMPLETE

    @property
    def to_act(self) -> Player | None:
        return None if self.is_complete else self.round.to_act

    @property
    def pot(self) -> int:
        """Total de fichas en juego, incluidas las apuestas de la ronda actual."""
        return sum(p.contributed for p in self.order)

    @property
    def current_bet(self) -> int:
        return 0 if self.is_complete else self.round.current_bet

    def legal_actions(self) -> LegalActions:
        if self.is_complete:
            raise IllegalActionError("La mano ya terminó")
        return self.round.legal_actions()

    def act(self, seat: int, action: Action) -> Action:
        """Ejecuta la acción del asiento indicado; rechaza las ilegales."""
        player = self.to_act
        if player is None:
            raise IllegalActionError("La mano ya terminó")
        if player.seat != seat:
            raise IllegalActionError("No es tu turno")
        applied = self.round.apply(action)
        self.events.append(
            HandEvent(
                "action", seat, applied.amount, action=applied.type.value, all_in=player.all_in
            )
        )
        self._advance()
        return applied

    def _post_blind(self, kind: str, player: Player, amount: int) -> None:
        posted = player.commit(amount)
        self.events.append(HandEvent(kind, player.seat, posted, all_in=player.all_in))

    def _advance(self) -> None:
        """Cierra rondas terminadas y avanza hasta la siguiente decisión o el final."""
        while self.round.is_complete:
            self._close_round()
            live = [p for p in self.order if p.live]
            if len(live) == 1:
                self._finish_uncontested(live[0])
                return
            if self.phase is Phase.RIVER:
                self._showdown(live)
                return
            self.phase, count = _NEXT_STREET[self.phase]
            dealt = self._deck.deal(count)
            self.board.extend(dealt)
            self.events.append(HandEvent("board", action=self.phase.value, cards=tuple(dealt)))
            self.round = BettingRound(self.order, 0, 0, self.big_blind)

    def _close_round(self) -> None:
        """Devuelve la parte no igualada de la apuesta más alta y limpia las apuestas."""
        top = max(self.order, key=lambda p: p.bet)
        second = max((p.bet for p in self.order if p is not top), default=0)
        uncalled = top.bet - second
        if uncalled > 0 and top.live:
            top.stack += uncalled
            top.contributed -= uncalled
            self.events.append(HandEvent("refund", top.seat, uncalled))
        for player in self.order:
            player.bet = 0

    def _finish_uncontested(self, winner: Player) -> None:
        total = self.pot
        award = PotAward(total, (winner.seat,), (winner.seat,), {winner.seat: total})
        self._pay([award], showdown=False, shown_hands={}, hand_values={})

    def _showdown(self, live: list[Player]) -> None:
        hand_values = {p.seat: evaluate([*p.hole_cards, *self.board]) for p in live}
        shown_hands = {p.seat: tuple(p.hole_cards) for p in live}
        for seat, cards in shown_hands.items():
            self.events.append(HandEvent("show", seat, cards=cards))
        pots = build_pots(
            {p.seat: p.contributed for p in self.order},
            {p.seat for p in self.order if p.folded},
        )
        awards = award_pots(pots, hand_values, [p.seat for p in self.order])
        self._pay(awards, showdown=True, shown_hands=shown_hands, hand_values=hand_values)

    def _pay(
        self,
        awards: list[PotAward],
        showdown: bool,
        shown_hands: dict[int, tuple[Card, ...]],
        hand_values: dict[int, HandValue],
    ) -> None:
        by_seat = {p.seat: p for p in self.order}
        payouts: dict[int, int] = {}
        for award in awards:
            for seat, amount in award.payouts.items():
                by_seat[seat].stack += amount
                payouts[seat] = payouts.get(seat, 0) + amount
                self.events.append(HandEvent("win", seat, amount))
        self.result = HandResult(
            showdown, tuple(self.board), tuple(awards), payouts, shown_hands, hand_values
        )
        self.phase = Phase.COMPLETE
