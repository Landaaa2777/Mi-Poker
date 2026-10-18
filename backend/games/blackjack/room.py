"""La mesa de blackjack de una sala: varias personas contra el crupier, con el saldo de cada cuenta.

Usa el mismo motor que la partida contra bots. Lo que cambia:

- Cada persona lleva a la mesa las fichas iniciales desde su saldo, y lo que
  gana o pierde en cada ronda cambia su saldo al terminarla.
- Para empezar una ronda, apuestan todas las personas. La mesa espera sin prisa
  a la primera apuesta; desde ella, las demás tienen 30 segundos, y quien no
  apuesta a tiempo no juega esa ronda.
- 30 segundos por decisión: si se acaban, la mano se planta (y el seguro se
  rechaza).
- Quien se va de la sala deja su ronda jugándose sola (se planta) y, al
  terminarla, deja la mesa llevándose sus fichas.
"""

from __future__ import annotations

import asyncio
import random
from typing import Annotated, Any

from pydantic import Field, TypeAdapter

from core.bots import pick_names
from core.room import RoomContext, RoomTable
from core.session import SessionError
from games.blackjack.bots import BlackjackBot, create_bot
from games.blackjack.engine import Action, BlackjackGame, IllegalActionError, Phase, Rules, table_view

from .protocol import Bet, Insurance, PlayerAction

# En una sala se apuesta y se juega: sentarse y empezar lo lleva la sala.
ROOM_MESSAGE = TypeAdapter(Annotated[Bet | PlayerAction | Insurance, Field(discriminator="type")])


class BlackjackRoom(RoomTable):
    def __init__(self, context: RoomContext) -> None:
        super().__init__(context)
        options = self.options
        people = [person.name for person in context.people]
        names = [*people, *pick_names(options.bots, taken=people)]
        rules = Rules(
            min_bet=options.min_bet,
            max_bet=options.max_bet,
            dealer_hits_soft_17=options.dealer_hits_soft_17,
            surrender=options.surrender,
        )
        self.game = BlackjackGame(names, options.starting_stack, rules)
        self.bots: dict[int, BlackjackBot] = {
            seat: create_bot(options.difficulty, name)
            for seat, name in enumerate(names)
            if seat >= len(people)
        }
        self.bets: dict[int, int] = {}  # lo que ha apostado cada persona para la próxima ronda
        self.stack_before: dict[int, int] = {}  # fichas de cada persona al empezar la ronda
        self.cashed_out: set[int] = set()  # se fueron y ya no tienen fichas en la mesa
        self._recorded_round = 0

    # --- Intenciones de las personas ---

    def handle(self, user_id: int, text: str) -> None:
        message = ROOM_MESSAGE.validate_json(text)
        seat = self.seat(user_id)
        game = self.game
        try:
            if isinstance(message, Bet):
                if game.round_in_progress:
                    raise SessionError("La ronda actual todavía no ha terminado")
                if seat in self.bets:
                    raise SessionError("Ya has apostado: falta que apuesten los demás")
                problem = game.rules.check_bet(message.amount, game.seats[seat].stack)
                if problem:
                    raise SessionError(problem)
                self.bets[seat] = message.amount
            elif isinstance(message, Insurance):
                game.insure(seat, message.take)
            else:
                game.act(seat, message.action)
                self.timer.stop()  # la siguiente decisión tiene su tiempo entero
        except IllegalActionError as error:
            raise SessionError(str(error)) from error
        self._after_change()
        self.wake()

    # --- Estado ---

    def state(self, user_id: int) -> dict[str, Any] | None:
        """Lo que ve una persona: la carta del crupier tapada hasta que se destapa."""
        game = self.game
        seat = self.seat_of.get(user_id)
        state = table_view(game, seat).to_dict()
        for entry in state["seats"]:
            number = entry["seat"]
            bot = self.bots.get(number)
            entry["is_human"] = number == seat  # "soy yo"
            entry["person"] = number in self.person_at
            entry["gone"] = number in self.gone
            entry["level"] = bot.level_name if bot else ""
            entry["bet_ready"] = number in self.bets  # ya ha apostado para la próxima ronda
        person = self.person_at.get(seat) if seat is not None else None
        out = seat is None or seat in self.gone or not game.can_bet(seat)
        state.update(
            config=self.options.model_dump(exclude={"player_name"}),
            human_seat=seat,
            round_in_progress=game.round_in_progress,
            human_out=not game.round_in_progress and out,
            my_bet=self.bets.get(seat) if seat is not None else None,
            game_over=self.finished,
            balance=person.account.balance() if person and person.account else None,
            timer=self.timer.describe(),
        )
        return state

    def seated_chips(self, user_id: int) -> int:
        """Fichas de la persona en la mesa: su stack más lo que tiene apostado."""
        seat = self.seat_of.get(user_id)
        if seat is None or seat in self.cashed_out or self.finished:
            return 0
        place = self.game.seats[seat]
        return place.stack + (place.at_stake if self.game.round_in_progress else 0)

    # --- El bucle de la partida ---

    async def _step(self) -> None:
        phase = self.game.phase
        if phase in (Phase.BETTING, Phase.COMPLETE):
            await self._betting()
        elif phase == Phase.INSURANCE:
            await self._insurance()
        else:
            await self._playing()

    async def _betting(self) -> None:
        self._cash_out()
        game = self.game
        players = [seat for seat in self.person_at if seat not in self.gone and game.can_bet(seat)]
        if not players:
            self.finished = True  # ya no queda ninguna persona que pueda apostar
            return
        if any(seat not in self.bets for seat in players):
            if not self.bets:
                await self._idle()  # nadie ha apostado: se espera sin prisa a la primera apuesta
                return
            if not await self._wait_for(None):
                return  # alguien ha apostado (o se ha ido): se vuelve a mirar
            # Se acabó el tiempo: quien no ha apostado no juega esta ronda.
        self._deal_round()
        await self._notify()

    async def _insurance(self) -> None:
        game = self.game
        for seat in self.person_at:
            if seat in self.gone and game.seats[seat].insurance_pending:
                game.insure(seat, False)  # se fue: sin seguro
        pending = [seat for seat in self.person_at if game.seats[seat].insurance_pending]
        if pending and await self._wait_for(None):
            for seat in pending:
                if game.phase == Phase.INSURANCE and game.seats[seat].insurance_pending:
                    game.insure(seat, False)  # se acabó el tiempo: sin seguro
        self._after_change()
        await self._notify()

    async def _playing(self) -> None:
        game = self.game
        if game.to_act is None:
            return
        seat = game.to_act[0]
        if seat in self.bots:
            await self._bot_plays(seat)
        elif seat in self.gone:
            game.act(seat, Action.STAND)  # se fue: su ronda se juega sola
            self._after_change()
            await self._notify()
        elif await self._wait_for(seat):
            if game.to_act is not None and game.to_act[0] == seat:
                game.act(seat, Action.STAND)  # se acabó su tiempo: se planta
                self._after_change()
                await self._notify()

    def _on_abandon(self, seat: int) -> None:
        self.bets.pop(seat, None)
        if not self.game.round_in_progress:
            self._cash_out()

    # --- Interno ---

    def _deal_round(self) -> None:
        game = self.game
        bets = dict(self.bets)
        for seat, bot in self.bots.items():
            if game.can_bet(seat):
                amount = bot.bet(table_view(game, seat))
                if amount:
                    bets[seat] = amount
        self.bets = {}
        self.stack_before = {seat: game.seats[seat].stack for seat in bets if seat in self.person_at}
        game.start_round(bets)
        # Los bots deciden el seguro en el momento: solo quedan pendientes las personas.
        for seat, bot in self.bots.items():
            if game.phase == Phase.INSURANCE and game.seats[seat].insurance_pending:
                game.insure(seat, bot.insure(table_view(game, seat)))
        self._after_change()

    def _cash_out(self) -> None:
        """Quien se fue deja la mesa con sus fichas: su saldo ya las cuenta, así que no cambia."""
        for seat in self.gone - self.cashed_out:
            self.game.seats[seat].stack = 0
            self.cashed_out.add(seat)

    def _after_change(self) -> None:
        """Al terminar una ronda, lo ganado o perdido por cada persona se apunta en su saldo."""
        game = self.game
        if game.phase != Phase.COMPLETE or self._recorded_round == game.round_number:
            return
        self._recorded_round = game.round_number
        for seat, before in self.stack_before.items():
            account = self.person_at[seat].account
            if account is not None:
                account.add_chips(game.seats[seat].stack - before)

    async def _bot_plays(self, seat: int) -> None:
        game = self.game
        view = table_view(game, seat)
        # El bot piensa en otro hilo mientras corre su tiempo de espera.
        action, _ = await asyncio.gather(
            asyncio.to_thread(self.bots[seat].decide, view),
            asyncio.sleep(random.uniform(*self.context.bot_delay)),
        )
        if game.to_act is None or game.to_act[0] != seat:
            return
        game.act(seat, action)
        self._after_change()
        await self._notify()
