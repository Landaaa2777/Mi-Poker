"""La mesa de poker de una sala: varias personas (y quizá bots) con el saldo de cada cuenta.

Usa el mismo motor que la partida contra bots. Lo que cambia:

- Cada persona lleva a la mesa las fichas iniciales desde su saldo, y lo que
  gana o pierde en cada mano cambia su saldo al terminarla.
- Las manos se reparten solas, con una pausa entre una y otra.
- 30 segundos por decisión; si se acaban, se pasa si se puede y, si no, se
  retira.
- Quien se va de la sala se retira de la mano en cuanto le toca (pierde lo
  apostado) y deja la mesa al terminarla, llevándose sus fichas.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

from pydantic import TypeAdapter

from accounts import HandOutcome
from core.room import ROOM_LEVEL, RoomContext, RoomTable
from core.session import SessionError
from games.poker.bots import PERSONALITIES, Bot, create_bot
from games.poker.engine import (
    CATEGORY_NAMES,
    Action,
    ActionType,
    Game,
    GameConfig,
    IllegalActionError,
    player_view,
)

from .protocol import NOTICE, PlayerAction

# En una sala solo se juega la mano: empezar, repartir y terminar lo lleva la sala.
ROOM_MESSAGE = TypeAdapter(PlayerAction)


class PokerRoom(RoomTable):
    def __init__(self, context: RoomContext) -> None:
        super().__init__(context)
        options = self.options
        people = [person.name for person in context.people]
        taken = {name.casefold() for name in people}
        free = [p for p in PERSONALITIES if p.name.casefold() not in taken]
        personalities = random.sample(free, options.bots)
        names = (*people, *(p.name for p in personalities))
        self.game = Game(
            GameConfig(names, options.starting_stack, options.small_blind, options.big_blind)
        )
        self.bots: dict[int, Bot] = {
            seat: create_bot(options.difficulty, personality, simulations=context.simulations)
            for seat, personality in enumerate(personalities, start=len(people))
        }
        self.stack_before: dict[int, int] = {}  # fichas de cada persona al empezar la mano
        self.cashed_out: set[int] = set()  # se fueron y ya no tienen fichas en la mesa
        self._observed_hand = 0
        self._deal()

    # --- Intenciones de las personas ---

    def handle(self, user_id: int, text: str) -> None:
        message = ROOM_MESSAGE.validate_json(text)
        seat = self.seat(user_id)
        hand = self.game.hand
        if hand is None or hand.is_complete:
            raise SessionError("No hay ninguna mano en curso")
        if hand.to_act is None or hand.to_act.seat != seat:
            raise SessionError("No es tu turno")
        try:
            hand.act(seat, Action(message.action, message.amount))
        except IllegalActionError as error:
            raise SessionError(str(error)) from error
        self.timer.stop()  # la siguiente decisión tiene su tiempo entero
        self._after_action()
        self.wake()

    # --- Estado ---

    def state(self, user_id: int) -> dict[str, Any] | None:
        """Lo que ve una persona: la mesa pública y sus cartas, nunca las de las demás."""
        game = self.game
        seat = self.seat_of.get(user_id)
        view = player_view(game, seat)
        state = view.to_dict()
        for entry in state["seats"]:
            number = entry["seat"]
            bot = self.bots.get(number)
            entry["is_human"] = number == seat  # "soy yo": la mesa lo pinta abajo
            entry["person"] = number in self.person_at
            entry["gone"] = number in self.gone
            entry["style"] = bot.personality.style if bot else ""
            entry["level"] = bot.level_name if bot else ""
        if view.result is not None:
            state["result"]["hand_names"] = {
                str(number): CATEGORY_NAMES[value[0]]
                for number, value in view.result.hand_values.items()
            }
            del state["result"]["hand_values"]
        me = game.players[seat] if seat is not None else None
        person = self.person_at.get(seat) if seat is not None else None
        winner = game.winner
        state.update(
            notice=NOTICE,
            config=self.options.model_dump(exclude={"player_name"}),
            hand_in_progress=game.hand_in_progress,
            human_seat=seat,
            human_out=me is not None and not game.hand_in_progress and me.stack == 0,
            game_over=self.finished,
            winner_seat=winner.seat if winner else None,
            balance=person.account.balance() if person and person.account else None,
            timer=self.timer.describe(),
            next_hand_in=self.pause_left(),
        )
        return state

    def seated_chips(self, user_id: int) -> int:
        """Fichas de la persona en la mesa: las de su stack más lo apostado en la mano en curso."""
        seat = self.seat_of.get(user_id)
        if seat is None or seat in self.cashed_out or self.finished:
            return 0
        if self.game.hand_in_progress and seat in self.stack_before:
            return self.stack_before[seat]  # stack más lo que lleva apostado
        return self.game.players[seat].stack

    # --- El bucle de la partida ---

    async def _step(self) -> None:
        game = self.game
        hand = game.hand
        if game.hand_in_progress:
            assert hand is not None and hand.to_act is not None
            seat = hand.to_act.seat
            if seat in self.bots:
                await self._bot_plays(seat)
            elif seat in self.gone:
                self._act(seat, ActionType.FOLD)  # se fue: se retira en cuanto le toca
                await self._notify()
            elif self._rivals_gone(seat):
                # Los demás de la mano se han ido y se retirarán en cuanto les toque:
                # su decisión ya no importa, así que no se le hace esperar.
                self._act(seat, ActionType.CHECK if hand.legal_actions().can_check else ActionType.CALL)
                await self._notify()
            elif await self._wait_for(seat):
                # Se acabó su tiempo: lo más prudente, pasar si se puede y si no retirarse.
                if hand.to_act is not None and hand.to_act.seat == seat:
                    prudent = ActionType.CHECK if hand.legal_actions().can_check else ActionType.FOLD
                    self._act(seat, prudent)
                    await self._notify()
            return
        # La mano ha terminado.
        if not self._over():
            await self._pause()
        self._cash_out()
        if self._over():
            self.finished = True
            return
        self._deal()
        await self._notify()

    def _on_abandon(self, seat: int) -> None:
        if not self.game.hand_in_progress:
            self._cash_out()  # entre manos se va ya, con sus fichas

    # --- Interno ---

    def _over(self) -> bool:
        """Queda un solo jugador con fichas, o ya no queda ninguna persona que pueda jugar.

        Quien se ha ido ya no cuenta, aunque sus fichas sigan en la mesa hasta que
        termine la mano.
        """
        remaining = [p for p in self.game.players if p.stack > 0 and p.seat not in self.gone]
        return len(remaining) < 2 or not any(p.seat in self.person_at for p in remaining)

    def _rivals_gone(self, seat: int) -> bool:
        """¿Se han ido todos los que siguen en la mano, salvo `seat`?"""
        rivals = [p.seat for p in self.game.players if p.live and p.seat != seat]
        return bool(rivals) and all(rival in self.gone for rival in rivals)

    def _cash_out(self) -> None:
        """Quien se fue deja la mesa con sus fichas: su saldo ya las cuenta, así que no cambia."""
        for seat in self.gone - self.cashed_out:
            self.game.players[seat].stack = 0
            self.cashed_out.add(seat)

    def _deal(self) -> None:
        self.stack_before = {
            seat: self.game.players[seat].stack
            for seat in self.person_at
            if self.game.players[seat].stack > 0
        }
        self.game.start_hand()
        self._after_action()

    def _act(self, seat: int, action_type: ActionType) -> None:
        hand = self.game.hand
        assert hand is not None
        hand.act(seat, Action(action_type))
        self._after_action()

    def _after_action(self) -> None:
        """Al terminar la mano: los bots la repasan y el saldo de cada persona se pone al día."""
        game = self.game
        if game.hand_in_progress or self._observed_hand == game.hand_number:
            return
        self._observed_hand = game.hand_number
        for seat, bot in self.bots.items():
            bot.observe(player_view(game, seat))
        for seat in self.stack_before:
            account = self.person_at[seat].account
            if account is not None:
                account.hand_finished(self._outcome(seat))

    def _outcome(self, seat: int) -> HandOutcome:
        """Cómo le fue a una persona en la mano que acaba de terminar."""
        game = self.game
        assert game.hand is not None and game.hand.result is not None
        result = game.hand.result
        shown = result.hand_values.get(seat)
        winner = game.winner
        return HandOutcome(
            difficulty=ROOM_LEVEL,
            chips_won=result.payouts.get(seat, 0),
            chips_delta=game.players[seat].stack - self.stack_before[seat],
            best_hand=int(shown[0]) if shown else None,
            first_hand=game.hand_number == 1,
            game_won=winner is not None and winner.seat == seat,
        )

    async def _bot_plays(self, seat: int) -> None:
        game = self.game
        hand = game.hand
        view = player_view(game, seat)
        # El bot piensa en otro hilo mientras corre su tiempo de espera.
        action, _ = await asyncio.gather(
            asyncio.to_thread(self.bots[seat].decide, view),
            asyncio.sleep(random.uniform(*self.context.bot_delay)),
        )
        if game.hand is not hand or hand is None or hand.to_act is None or hand.to_act.seat != seat:
            return
        hand.act(seat, action)
        self._after_action()
        await self._notify()
