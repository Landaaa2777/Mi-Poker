"""Una mesa de blackjack: rondas, turnos, crupier y pagos. Python puro.

Cómo van las fichas: cada asiento tiene su `stack`. Al apostar (o doblar,
dividir o asegurarse) las fichas salen del stack y quedan en la mesa; al pagar
vuelven, con lo ganado, o se las queda la banca. `house` lleva la cuenta de la
banca, así se puede comprobar que nunca se crea ni se pierde ninguna ficha:

    suma de stacks + fichas en la mesa + banca = siempre lo mismo

Una ronda:
1. Cada jugador apuesta (`start_round`) y se reparten dos cartas a cada uno y
   dos al crupier, una de ellas tapada.
2. Si el crupier enseña un As, cada jugador decide si se asegura (`insure`).
3. Si enseña un As o un 10, mira si tiene blackjack. Si lo tiene, la ronda
   acaba ahí.
4. Cada jugador juega sus manos por turno (`act`): pedir, plantarse, doblar,
   dividir o rendirse.
5. El crupier destapa su carta y pide hasta 17. Se paga cada mano.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from core.cards import Card

from .hand import ACE, card_value, hand_total, is_blackjack
from .rules import Rules
from .shoe import Shoe

MIN_SEATS = 1
MAX_SEATS = 5  # el humano y hasta 4 bots


class Phase(StrEnum):
    BETTING = "betting"  # todavía no ha empezado ninguna ronda
    INSURANCE = "insurance"  # el crupier enseña un As: cada uno decide si se asegura
    PLAYING = "playing"  # turnos de los jugadores
    COMPLETE = "complete"  # ronda terminada y pagada; la siguiente empieza con otra apuesta


class Action(StrEnum):
    HIT = "hit"  # pedir carta
    STAND = "stand"  # plantarse
    DOUBLE = "double"  # doblar: duplica la apuesta y recibe una sola carta más
    SPLIT = "split"  # dividir una pareja en dos manos
    SURRENDER = "surrender"  # rendirse: recupera la mitad de la apuesta


class HandStatus(StrEnum):
    PLAYING = "playing"  # le quedan decisiones
    STOOD = "stood"  # terminada sin pasarse: espera al crupier
    BUST = "bust"  # se pasó de 21
    BLACKJACK = "blackjack"  # blackjack natural
    SURRENDERED = "surrendered"


class Result(StrEnum):
    WIN = "win"  # cobra 1 a 1
    BLACKJACK = "blackjack"  # cobra 3 a 2
    PUSH = "push"  # empate: recupera la apuesta
    LOSE = "lose"
    SURRENDER = "surrender"  # recupera la mitad


class IllegalActionError(ValueError):
    """La acción no está permitida ahora; el mensaje dice por qué."""


@dataclass
class PlayerHand:
    cards: list[Card]
    bet: int
    from_split: bool = False  # nació al dividir: su 21 no es blackjack
    doubled: bool = False
    status: HandStatus = HandStatus.PLAYING
    result: Result | None = None
    payout: int = 0  # lo que se le devuelve al pagar, apuesta incluida

    @property
    def total(self) -> int:
        return hand_total(self.cards)[0]

    @property
    def soft(self) -> bool:
        return hand_total(self.cards)[1]

    @property
    def split_aces(self) -> bool:
        """¿Es una de las manos de unos ases divididos? Esas reciben una sola carta."""
        return self.from_split and self.cards[0].rank == ACE


@dataclass
class Seat:
    seat: int
    name: str
    stack: int
    hands: list[PlayerHand] = field(default_factory=list)  # vacío si no juega esta ronda
    insurance: int = 0  # fichas puestas en el seguro
    insurance_pending: bool = False  # todavía tiene que decidir si se asegura

    @property
    def at_stake(self) -> int:
        """Fichas suyas que están ahora en la mesa: apuestas sin pagar y seguro."""
        return sum(hand.bet for hand in self.hands if hand.result is None) + self.insurance


@dataclass(frozen=True)
class Event:
    """Algo que pasa en la ronda. El registro de eventos solo crece."""

    kind: str
    seat: int | None = None  # None = el crupier o la mesa
    hand: int | None = None  # qué mano del asiento (0 salvo tras dividir)
    card: Card | None = None  # None también para la carta tapada del crupier
    amount: int = 0
    action: str = ""
    result: str = ""


class BlackjackGame:
    """La mesa: asientos, crupier, zapato y la ronda en curso."""

    def __init__(
        self,
        names: Sequence[str],
        starting_stack: int,
        rules: Rules | None = None,
        shoe: Shoe | None = None,
    ) -> None:
        if not MIN_SEATS <= len(names) <= MAX_SEATS:
            raise ValueError(f"La mesa admite de {MIN_SEATS} a {MAX_SEATS} jugadores")
        self.rules = rules or Rules()
        if starting_stack < self.rules.min_bet:
            raise ValueError("Las fichas iniciales deben cubrir al menos la apuesta mínima")
        self.shoe = shoe or Shoe(self.rules.decks, self.rules.penetration)
        self.seats = [Seat(index, name, starting_stack) for index, name in enumerate(names)]
        self.dealer: list[Card] = []
        self.hole_revealed = False
        self.phase = Phase.BETTING
        self.round_number = 0
        self.events: list[Event] = []  # los de la ronda en curso (o la última)
        self.house = 0  # lo que ha ganado la banca (negativo si ha perdido)
        self.to_act: tuple[int, int] | None = None  # (asiento, mano) que tiene el turno

    # --- Consultas ---

    @property
    def round_in_progress(self) -> bool:
        return self.phase in (Phase.INSURANCE, Phase.PLAYING)

    def can_bet(self, seat: int) -> bool:
        """¿Tiene fichas para la apuesta mínima?"""
        return self.seats[seat].stack >= self.rules.min_bet

    def total_chips(self) -> int:
        """Stacks más fichas en la mesa más la banca: tiene que ser constante."""
        return sum(seat.stack + seat.at_stake for seat in self.seats) + self.house

    def legal_actions(self, seat: int) -> list[Action]:
        """Lo que puede hacer `seat` ahora mismo (vacío si no es su turno)."""
        if self.phase != Phase.PLAYING or self.to_act is None or self.to_act[0] != seat:
            return []
        return [
            action
            for action in Action
            if self._illegal_reason(self.seats[seat], self.to_act[1], action) is None
        ]

    # --- Una ronda ---

    def start_round(self, bets: Mapping[int, int]) -> None:
        """Empieza una ronda con las apuestas de cada asiento que juega."""
        if self.round_in_progress:
            raise IllegalActionError("La ronda actual todavía no ha terminado")
        if not bets:
            raise IllegalActionError("Hace falta al menos una apuesta")
        for seat_index, bet in bets.items():
            if not 0 <= seat_index < len(self.seats):
                raise IllegalActionError("Ese asiento no existe")
            problem = self.rules.check_bet(bet, self.seats[seat_index].stack)
            if problem:
                raise IllegalActionError(problem)

        self.round_number += 1
        self.events = []
        self.dealer = []
        self.hole_revealed = False
        if self.shoe.cut_reached:
            # Salió la carta de corte en la ronda anterior: se rebaraja todo.
            self.shoe.reshuffle()
            self.events.append(Event("shuffle"))
        for seat in self.seats:
            seat.hands = []
            seat.insurance = 0
            seat.insurance_pending = False
        playing = [self.seats[index] for index in sorted(bets)]
        for seat in playing:
            bet = bets[seat.seat]
            seat.stack -= bet
            seat.hands = [PlayerHand([], bet)]
            self.events.append(Event("bet", seat.seat, 0, amount=bet))

        # Reparto: una carta a cada jugador, una al crupier (vista), otra a cada
        # jugador y la segunda del crupier, tapada.
        for seat in playing:
            self._deal_to(seat, 0)
        self._deal_dealer()
        for seat in playing:
            self._deal_to(seat, 0)
        self._deal_dealer(hidden=True)

        for seat in playing:
            if is_blackjack(seat.hands[0].cards):
                seat.hands[0].status = HandStatus.BLACKJACK

        up = self.dealer[0]
        if up.rank == ACE:
            self.phase = Phase.INSURANCE
            for seat in playing:
                seat.insurance_pending = seat.stack >= self._insurance_cost(seat)
            if not any(seat.insurance_pending for seat in self.seats):
                self._peek()
        elif card_value(up) == 10:
            self._peek()
        else:
            self._start_turns()

    def insure(self, seat_index: int, take: bool) -> None:
        """Decide si `seat_index` se asegura contra el blackjack del crupier."""
        seat = self.seats[seat_index]
        if self.phase != Phase.INSURANCE or not seat.insurance_pending:
            raise IllegalActionError("Ahora no se puede pedir seguro")
        seat.insurance_pending = False
        if take:
            cost = self._insurance_cost(seat)
            seat.stack -= cost
            seat.insurance = cost
        self.events.append(Event("insurance", seat_index, 0, amount=seat.insurance))
        if not any(other.insurance_pending for other in self.seats):
            self._peek()

    def act(self, seat_index: int, action: Action | str) -> None:
        """Una decisión del jugador que tiene el turno, sobre su mano en juego."""
        try:
            action = Action(action)
        except ValueError:
            raise IllegalActionError(f"Acción desconocida: {action!r}") from None
        if self.phase != Phase.PLAYING or self.to_act is None:
            raise IllegalActionError("Ahora no es momento de jugar")
        if self.to_act[0] != seat_index:
            raise IllegalActionError("No es tu turno")
        seat = self.seats[seat_index]
        index = self.to_act[1]
        problem = self._illegal_reason(seat, index, action)
        if problem:
            raise IllegalActionError(problem)

        hand = seat.hands[index]
        self.events.append(Event("action", seat_index, index, action=action.value))
        if action == Action.HIT:
            self._deal_to(seat, index)
            self._settle_hand_status(hand)
        elif action == Action.STAND:
            hand.status = HandStatus.STOOD
        elif action == Action.DOUBLE:
            seat.stack -= hand.bet
            hand.bet *= 2
            hand.doubled = True
            self._deal_to(seat, index)
            hand.status = HandStatus.BUST if hand.total > 21 else HandStatus.STOOD
        elif action == Action.SPLIT:
            self._split(seat, index)
        else:  # rendirse
            hand.status = HandStatus.SURRENDERED
        self._advance()

    # --- Interno ---

    def _insurance_cost(self, seat: Seat) -> int:
        return seat.hands[0].bet // 2

    def _illegal_reason(self, seat: Seat, index: int, action: Action) -> str | None:
        """Por qué no se puede hacer `action` con esa mano, o None si se puede."""
        hand = seat.hands[index]
        two_cards = len(hand.cards) == 2
        if action in (Action.HIT, Action.STAND):
            return None
        if action == Action.DOUBLE:
            if not two_cards:
                return "Solo se puede doblar con las dos primeras cartas"
            if hand.from_split and not self.rules.double_after_split:
                return "En esta mesa no se puede doblar después de dividir"
            if seat.stack < hand.bet:
                return "No tienes fichas suficientes para doblar"
            return None
        if action == Action.SPLIT:
            if not two_cards or card_value(hand.cards[0]) != card_value(hand.cards[1]):
                return "Solo se puede dividir una pareja"
            if len(seat.hands) >= self.rules.max_hands:
                return f"Como mucho se juegan {self.rules.max_hands} manos"
            if hand.split_aces and not self.rules.resplit_aces:
                return "Los ases divididos no se vuelven a dividir"
            if seat.stack < hand.bet:
                return "No tienes fichas suficientes para dividir"
            return None
        # Rendirse: solo con la mano de salida, antes de hacer nada con ella.
        if not self.rules.surrender:
            return "En esta mesa no está permitido rendirse"
        if len(seat.hands) != 1 or hand.from_split or not two_cards:
            return "Solo te puedes rendir con tus dos primeras cartas"
        return None

    def _in_play(self) -> list[Card]:
        """Todas las cartas que hay ahora sobre la mesa."""
        cards = list(self.dealer)
        for seat in self.seats:
            for hand in seat.hands:
                cards.extend(hand.cards)
        return cards

    def _draw(self) -> Card:
        return self.shoe.deal(self._in_play())

    def _deal_to(self, seat: Seat, index: int) -> None:
        card = self._draw()
        seat.hands[index].cards.append(card)
        self.events.append(Event("card", seat.seat, index, card))

    def _deal_dealer(self, hidden: bool = False) -> None:
        card = self._draw()
        self.dealer.append(card)
        # La carta tapada no viaja en el registro hasta que se destapa.
        self.events.append(Event("hole_card" if hidden else "dealer_card", card=None if hidden else card))

    def _settle_hand_status(self, hand: PlayerHand) -> None:
        """Tras recibir una carta: pasarse acaba la mano, y con 21 se planta sola."""
        if hand.total > 21:
            hand.status = HandStatus.BUST
        elif hand.total == 21:
            hand.status = HandStatus.STOOD

    def _split(self, seat: Seat, index: int) -> None:
        hand = seat.hands[index]
        seat.stack -= hand.bet
        second = PlayerHand([hand.cards.pop()], hand.bet, from_split=True)
        hand.from_split = True
        seat.hands.insert(index + 1, second)
        self.events.append(Event("split", seat.seat, index, amount=hand.bet))
        # La primera mano recibe ya su segunda carta; la otra, cuando le toque.
        self._deal_to(seat, index)
        if hand.split_aces:
            hand.status = HandStatus.STOOD  # los ases divididos reciben una sola carta
        else:
            self._settle_hand_status(hand)

    def _peek(self) -> None:
        """El crupier mira si tiene blackjack (enseña un As o un 10)."""
        dealer_blackjack = is_blackjack(self.dealer)
        self.events.append(Event("peek", result="blackjack" if dealer_blackjack else ""))
        # El seguro se cobra o se pierde ahora: paga 2 a 1 si el crupier tiene blackjack.
        for seat in self.seats:
            if seat.insurance:
                paid = seat.insurance * 3 if dealer_blackjack else 0
                seat.stack += paid
                self.house += seat.insurance - paid
                self.events.append(Event("insurance_paid", seat.seat, 0, amount=paid))
                seat.insurance = 0
        if dealer_blackjack:
            self._reveal()
            self._settle()
        else:
            self._start_turns()

    def _start_turns(self) -> None:
        self.phase = Phase.PLAYING
        self._advance()

    def _advance(self) -> None:
        """Pasa el turno a la siguiente mano con decisiones pendientes; si no queda ninguna, juega el crupier."""
        for seat in self.seats:
            for index, hand in enumerate(seat.hands):
                if hand.status != HandStatus.PLAYING:
                    continue
                if len(hand.cards) == 1:
                    # Segunda mano de una división: recibe ahora su segunda carta.
                    self._deal_to(seat, index)
                    if hand.split_aces:
                        hand.status = HandStatus.STOOD
                    else:
                        self._settle_hand_status(hand)
                    if hand.status != HandStatus.PLAYING:
                        continue
                self.to_act = (seat.seat, index)
                return
        self.to_act = None
        self._play_dealer()

    def _reveal(self) -> None:
        self.hole_revealed = True
        self.events.append(Event("reveal", card=self.dealer[1]))

    def _play_dealer(self) -> None:
        self._reveal()
        # Solo pide cartas si queda alguna mano con la que compararse.
        waiting = any(
            hand.status == HandStatus.STOOD for seat in self.seats for hand in seat.hands
        )
        while waiting:
            total, soft = hand_total(self.dealer)
            hits_soft_17 = total == 17 and soft and self.rules.dealer_hits_soft_17
            if total >= 17 and not hits_soft_17:
                break
            card = self._draw()
            self.dealer.append(card)
            self.events.append(Event("dealer_card", card=card))
        self._settle()

    def _settle(self) -> None:
        """Paga cada mano y cierra la ronda."""
        dealer_total = hand_total(self.dealer)[0]
        dealer_blackjack = is_blackjack(self.dealer)
        for seat in self.seats:
            for index, hand in enumerate(seat.hands):
                result, payout = self._result(hand, dealer_total, dealer_blackjack)
                hand.result, hand.payout = result, payout
                seat.stack += payout
                self.house += hand.bet - payout
                self.events.append(
                    Event("settle", seat.seat, index, amount=payout, result=result.value)
                )
            seat.insurance_pending = False
        self.to_act = None
        self.phase = Phase.COMPLETE

    def _result(self, hand: PlayerHand, dealer_total: int, dealer_blackjack: bool) -> tuple[Result, int]:
        bet = hand.bet
        if hand.status == HandStatus.SURRENDERED:
            return Result.SURRENDER, bet // 2
        if hand.status == HandStatus.BUST:
            return Result.LOSE, 0
        natural = is_blackjack(hand.cards, hand.from_split)
        if dealer_blackjack:
            return (Result.PUSH, bet) if natural else (Result.LOSE, 0)
        if natural:
            return Result.BLACKJACK, bet + bet * 3 // 2
        if dealer_total > 21 or hand.total > dealer_total:
            return Result.WIN, 2 * bet
        if hand.total == dealer_total:
            return Result.PUSH, bet
        return Result.LOSE, 0
