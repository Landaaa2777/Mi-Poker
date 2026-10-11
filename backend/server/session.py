"""Una partida en memoria: un humano contra bots, con el servidor como autoridad."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from accounts import HandOutcome
from bots import PERSONALITIES, Bot, create_bot
from poker_engine import (
    CATEGORY_NAMES,
    Action,
    ActionType,
    Game,
    GameConfig,
    IllegalActionError,
    player_view,
)

from .protocol import NOTICE, TableConfig

HUMAN_SEAT = 0
BOT_DELAY = (0.8, 2.5)  # segundos que un bot "piensa" antes de actuar

Listener = Callable[[], Awaitable[None]]


class TableAccount(Protocol):
    """Lo que una partida necesita de la cuenta del jugador. Un invitado no tiene."""

    def balance(self) -> int:
        """Fichas de la cuenta, contando las que tiene en esta mesa."""
        ...

    def hand_finished(self, outcome: HandOutcome) -> None:
        """Una mano ha terminado: se apuntan sus estadísticas y lo ganado o perdido."""
        ...

    def hand_abandoned(self, chips: int) -> None:
        """El jugador dejó una mano a medias: pierde lo que ya había apostado en ella."""
        ...


class SessionError(Exception):
    """La intención del cliente no se puede cumplir; el mensaje es para mostrarlo."""


class GameSession:
    """Estado de la partida de un jugador, en memoria.

    Un invitado juega con fichas que solo existen aquí. Con cuenta, las fichas
    de la mesa salen de su saldo y lo que pasa en cada mano se apunta en él.
    """

    def __init__(
        self,
        bot_delay: tuple[float, float] = BOT_DELAY,
        simulations: int | None = None,
        account: TableAccount | None = None,
    ) -> None:
        self.bot_delay = bot_delay
        self.simulations = simulations
        self.account = account
        self._stack_before = 0  # fichas del humano al empezar la mano en curso
        self.config: TableConfig | None = None
        self.game: Game | None = None
        self.bots: dict[int, Bot] = {}
        self.listener: Listener | None = None  # se llama cada vez que cambia el estado
        self._runner: asyncio.Task | None = None
        self._observed_hand = 0

    # --- Intenciones del cliente ---

    def new_game(self, config: TableConfig) -> None:
        at_stake = self._at_stake()
        if self.account is not None:
            # El saldo ya cuenta las fichas de la mesa que se deja; lo apostado
            # en una mano a medias se pierde, así que no está disponible.
            available = self.account.balance() - at_stake
            if available < 1:
                raise SessionError("No te quedan fichas para sentarte a una mesa")
            if config.starting_stack > available:
                raise SessionError(
                    f"No tienes fichas suficientes: puedes llevar a la mesa hasta {available}"
                )
        self._stop_runner()
        if self.account is not None and at_stake > 0:
            self.account.hand_abandoned(at_stake)
        # Ningún bot se llama igual que el jugador.
        free = [p for p in PERSONALITIES if p.name.casefold() != config.player_name.casefold()]
        personalities = random.sample(free, config.bots)
        names = (config.player_name, *(p.name for p in personalities))
        self.config = config
        self.game = Game(
            GameConfig(names, config.starting_stack, config.small_blind, config.big_blind)
        )
        self.bots = {
            seat: create_bot(config.difficulty, personality, simulations=self.simulations)
            for seat, personality in enumerate(personalities, start=1)
        }
        self._observed_hand = 0
        self._deal()

    def restart(self) -> None:
        """Vuelve a empezar con la misma configuración.

        Un invitado recibe fichas virtuales nuevas, gratis. Con cuenta, las
        fichas vuelven a salir de su saldo.
        """
        if self.config is None:
            raise SessionError("Todavía no hay ninguna partida que reiniciar")
        self.new_game(self.config)

    def next_hand(self) -> None:
        game = self._require_game()
        if game.hand_in_progress:
            raise SessionError("La mano actual todavía no ha terminado")
        if self.human_out or game.is_over:
            raise SessionError("La partida terminó: reiníciala para seguir jugando")
        self._deal()

    def act(self, action_type: ActionType, amount: int = 0) -> None:
        game = self._require_game()
        hand = game.hand
        if hand is None or hand.is_complete:
            raise SessionError("No hay ninguna mano en curso")
        try:
            hand.act(HUMAN_SEAT, Action(action_type, amount))
        except IllegalActionError as error:
            raise SessionError(str(error)) from error
        self._after_action()
        self._start_runner()

    # --- Estado ---

    @property
    def human_out(self) -> bool:
        game = self.game
        return game is not None and not game.hand_in_progress and game.players[HUMAN_SEAT].stack == 0

    def state(self) -> dict[str, Any] | None:
        """Lo que ve el humano: la mesa pública y sus cartas, nunca las ajenas ni el mazo."""
        game = self.game
        if game is None or self.config is None:
            return None
        view = player_view(game, HUMAN_SEAT)
        state = view.to_dict()
        for seat in state["seats"]:
            bot = self.bots.get(seat["seat"])
            seat["is_human"] = bot is None
            seat["style"] = bot.personality.style if bot else ""
            seat["level"] = bot.level_name if bot else ""
        if view.result is not None:
            state["result"]["hand_names"] = {
                str(seat): CATEGORY_NAMES[value[0]] for seat, value in view.result.hand_values.items()
            }
            del state["result"]["hand_values"]
        winner = game.winner
        state.update(
            notice=NOTICE,
            config=self.config.model_dump(),
            hand_in_progress=game.hand_in_progress,
            human_out=self.human_out,
            game_over=game.is_over,
            winner_seat=winner.seat if winner else None,
            balance=self.account.balance() if self.account else None,
        )
        return state

    # --- Interno ---

    def _require_game(self) -> Game:
        if self.game is None:
            raise SessionError("Primero hay que empezar una partida")
        return self.game

    def _at_stake(self) -> int:
        """Lo que el humano lleva apostado en la mano en curso; 0 si no hay ninguna."""
        game = self.game
        if game is None or not game.hand_in_progress:
            return 0
        return self._stack_before - game.players[HUMAN_SEAT].stack

    def _deal(self) -> None:
        assert self.game is not None
        self._stack_before = self.game.players[HUMAN_SEAT].stack
        self.game.start_hand()
        self._after_action()
        self._start_runner()

    def _after_action(self) -> None:
        """Al terminar la mano, cada bot la repasa con su propia vista de siempre."""
        game = self.game
        assert game is not None
        if game.hand_in_progress or self._observed_hand == game.hand_number:
            return
        self._observed_hand = game.hand_number
        for seat, bot in self.bots.items():
            bot.observe(player_view(game, seat))
        if self.account is not None:
            self.account.hand_finished(self._outcome(game))

    def _outcome(self, game: Game) -> HandOutcome:
        """Cómo le fue al humano en la mano que acaba de terminar."""
        assert game.hand is not None and game.hand.result is not None and self.config is not None
        result = game.hand.result
        shown = result.hand_values.get(HUMAN_SEAT)
        winner = game.winner
        return HandOutcome(
            difficulty=self.config.difficulty,
            chips_won=result.payouts.get(HUMAN_SEAT, 0),
            chips_delta=game.players[HUMAN_SEAT].stack - self._stack_before,
            best_hand=int(shown[0]) if shown else None,
            first_hand=game.hand_number == 1,
            game_won=winner is not None and winner.seat == HUMAN_SEAT,
        )

    def _stop_runner(self) -> None:
        if self._runner is not None:
            self._runner.cancel()
            self._runner = None

    def _start_runner(self) -> None:
        if self._runner is None or self._runner.done():
            self._runner = asyncio.get_running_loop().create_task(self._run_bots())

    async def _run_bots(self) -> None:
        """Hace jugar a los bots, uno a uno, hasta que le toque al humano o acabe la mano."""
        game = self.game
        assert game is not None
        while game.hand_in_progress:
            hand = game.hand
            assert hand is not None and hand.to_act is not None
            seat = hand.to_act.seat
            if seat == HUMAN_SEAT:
                return
            view = player_view(game, seat)
            # El bot piensa en otro hilo mientras corre su tiempo de espera.
            action, _ = await asyncio.gather(
                asyncio.to_thread(self.bots[seat].decide, view),
                asyncio.sleep(random.uniform(*self.bot_delay)),
            )
            if self.game is not game or game.hand is not hand:
                return  # la partida se reinició mientras el bot pensaba
            hand.act(seat, action)
            self._after_action()
            await self._notify()

    async def _notify(self) -> None:
        if self.listener is not None:
            await self.listener()
