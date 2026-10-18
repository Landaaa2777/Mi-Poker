"""Una partida de blackjack en memoria: un humano y sus bots contra el crupier.

El servidor es la autoridad: baraja, reparte, valida cada jugada y paga. Un
invitado juega con fichas que solo existen aquí. Con cuenta, las fichas de la
mesa salen de su saldo y lo ganado o perdido en cada ronda se apunta en él.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

from core.bots import BOT_DELAY, pick_names
from core.session import Listener, SessionError, TableAccount
from games.blackjack.bots import BlackjackBot, create_bot
from games.blackjack.engine import BlackjackGame, IllegalActionError, Phase, Rules, table_view

from .protocol import (
    CLIENT_MESSAGE,
    Bet,
    BlackjackConfig,
    Insurance,
    NewGame,
    PlayerAction,
    options,
)


class BlackjackSession:
    """Estado de la mesa de blackjack de un jugador."""

    def __init__(
        self,
        bot_delay: tuple[float, float] = BOT_DELAY,
        account: TableAccount | None = None,
        player_name: str | None = None,
    ) -> None:
        self.bot_delay = bot_delay
        self.account = account
        # Con cuenta, el nombre en la mesa es el suyo, diga lo que diga el cliente.
        self.player_name = player_name
        self.config: BlackjackConfig | None = None
        self.game: BlackjackGame | None = None
        self.bots: dict[int, BlackjackBot] = {}
        self.human_seat = 0
        self.listener: Listener | None = None  # se llama cada vez que cambia el estado
        self._runner: asyncio.Task | None = None
        self._stack_before = 0  # fichas del humano al empezar la ronda en curso
        self._recorded_round = 0  # última ronda ya apuntada en el saldo

    # --- Intenciones del cliente ---

    def handle(self, text: str) -> None:
        """Valida un mensaje del cliente (texto JSON) y hace lo que pide."""
        message = CLIENT_MESSAGE.validate_json(text)
        if isinstance(message, NewGame):
            config = message.config
            if self.player_name is not None:
                config = config.model_copy(update={"player_name": self.player_name})
            self.new_game(config)
        elif isinstance(message, Bet):
            self.bet(message.amount)
        elif isinstance(message, PlayerAction):
            self.act(message.action)
        elif isinstance(message, Insurance):
            self.insure(message.take)
        else:
            self.restart()

    def new_game(self, config: BlackjackConfig) -> None:
        at_stake = self._at_stake()
        if self.account is not None:
            # Lo apostado en una ronda a medias se pierde y las fichas sentadas en
            # otras mesas no se pueden traer: nada de eso está disponible.
            available = self.account.balance() - at_stake - self.account.chips_elsewhere()
            if available < config.min_bet:
                raise SessionError("No te quedan fichas para sentarte a una mesa")
            if config.starting_stack > available:
                raise SessionError(
                    f"No tienes fichas suficientes: puedes llevar a la mesa hasta {available}"
                )
        self._stop_runner()
        if self.account is not None and at_stake > 0:
            self.account.add_chips(-at_stake)  # dejar una ronda a medias cuesta lo apostado
        names = [config.player_name, *pick_names(config.bots, taken=[config.player_name])]
        # El humano se sienta en medio de la mesa: unos bots juegan antes y otros después.
        self.human_seat = config.bots // 2
        names.insert(self.human_seat, names.pop(0))
        rules = Rules(
            min_bet=config.min_bet,
            max_bet=config.max_bet,
            dealer_hits_soft_17=config.dealer_hits_soft_17,
            surrender=config.surrender,
        )
        self.config = config
        self.game = BlackjackGame(names, config.starting_stack, rules)
        self.bots = {
            seat: create_bot(config.difficulty, name)
            for seat, name in enumerate(names)
            if seat != self.human_seat
        }
        self._recorded_round = 0

    def restart(self) -> None:
        """Vuelve a empezar con la misma configuración (fichas nuevas de la mesa o del saldo)."""
        if self.config is None:
            raise SessionError("Todavía no hay ninguna partida que reiniciar")
        self.new_game(self.config)

    def bet(self, amount: int) -> None:
        """Apuesta y reparte una ronda; los bots apuestan a la vez."""
        game = self._require_game()
        if game.round_in_progress:
            raise SessionError("La ronda actual todavía no ha terminado")
        bets = {self.human_seat: amount}
        for seat, bot in self.bots.items():
            bot_bet = bot.bet(table_view(game, seat))
            if bot_bet:
                bets[seat] = bot_bet
        self._stack_before = game.seats[self.human_seat].stack
        try:
            game.start_round(bets)
        except IllegalActionError as error:
            raise SessionError(str(error)) from error
        # El seguro lo deciden los bots en el momento en que se ofrece, sin pararse
        # a pensar: así solo queda pendiente la decisión del humano.
        for seat, bot in self.bots.items():
            if game.phase == Phase.INSURANCE and game.seats[seat].insurance_pending:
                game.insure(seat, bot.insure(table_view(game, seat)))
        self._after_change()
        self._start_runner()

    def act(self, action: str) -> None:
        game = self._require_game()
        try:
            game.act(self.human_seat, action)
        except IllegalActionError as error:
            raise SessionError(str(error)) from error
        self._after_change()
        self._start_runner()

    def insure(self, take: bool) -> None:
        game = self._require_game()
        try:
            game.insure(self.human_seat, take)
        except IllegalActionError as error:
            raise SessionError(str(error)) from error
        self._after_change()
        self._start_runner()

    # --- Estado ---

    def options(self) -> dict[str, Any]:
        return options()

    @property
    def human_out(self) -> bool:
        """Sin ronda en juego y sin fichas para la apuesta mínima: toca reiniciar."""
        game = self.game
        return game is not None and not game.round_in_progress and not game.can_bet(self.human_seat)

    @property
    def in_progress(self) -> bool:
        return self.game is not None and not self.human_out

    def seated_chips(self) -> int:
        """Fichas del humano en esta mesa: su stack más lo apostado en la ronda en curso."""
        game = self.game
        if game is None or not self.in_progress:
            return 0
        return game.seats[self.human_seat].stack + self._at_stake()

    def close(self) -> None:
        self._stop_runner()

    def state(self) -> dict[str, Any] | None:
        """Lo que ve el humano: la mesa con la carta del crupier tapada hasta que se destapa."""
        game = self.game
        if game is None or self.config is None:
            return None
        state = table_view(game, self.human_seat).to_dict()
        for seat in state["seats"]:
            bot = self.bots.get(seat["seat"])
            seat["is_human"] = bot is None
            seat["level"] = bot.level_name if bot else ""
        state.update(
            config=self.config.model_dump(),
            human_seat=self.human_seat,
            round_in_progress=game.round_in_progress,
            human_out=self.human_out,
            balance=self.account.balance() if self.account else None,
        )
        return state

    # --- Interno ---

    def _require_game(self) -> BlackjackGame:
        if self.game is None:
            raise SessionError("Primero hay que sentarse a una mesa")
        return self.game

    def _at_stake(self) -> int:
        """Lo que el humano tiene apostado en la ronda en curso; 0 si no hay ninguna."""
        game = self.game
        if game is None or not game.round_in_progress:
            return 0
        return game.seats[self.human_seat].at_stake

    def _after_change(self) -> None:
        """Al terminar una ronda, lo ganado o perdido se apunta en el saldo (una sola vez)."""
        game = self.game
        assert game is not None
        if game.phase != Phase.COMPLETE or self._recorded_round == game.round_number:
            return
        self._recorded_round = game.round_number
        if self.account is not None:
            self.account.add_chips(game.seats[self.human_seat].stack - self._stack_before)

    def _stop_runner(self) -> None:
        if self._runner is not None:
            self._runner.cancel()
            self._runner = None

    def _start_runner(self) -> None:
        if self._runner is None or self._runner.done():
            self._runner = asyncio.get_running_loop().create_task(self._run_bots())

    async def _run_bots(self) -> None:
        """Hace jugar a los bots, uno a uno, hasta que le toque al humano o acabe la ronda."""
        game = self.game
        assert game is not None
        while True:
            if game.phase == Phase.PLAYING and game.to_act is not None:
                seat = game.to_act[0]
                if seat == self.human_seat:
                    return
                view = table_view(game, seat)
                # El bot piensa en otro hilo mientras corre su tiempo de espera.
                action, _ = await asyncio.gather(
                    asyncio.to_thread(self.bots[seat].decide, view),
                    asyncio.sleep(random.uniform(*self.bot_delay)),
                )
                if self.game is not game or game.to_act is None or game.to_act[0] != seat:
                    return
                game.act(seat, action)
            else:
                return
            self._after_change()
            await self._notify()

    async def _notify(self) -> None:
        if self.listener is not None:
            await self.listener()
