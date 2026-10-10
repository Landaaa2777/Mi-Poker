"""Una partida en memoria: un humano contra bots, con el servidor como autoridad."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any

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


class SessionError(Exception):
    """La intención del cliente no se puede cumplir; el mensaje es para mostrarlo."""


class GameSession:
    """Estado de la partida de un invitado. Las fichas solo existen aquí, en memoria."""

    def __init__(
        self,
        bot_delay: tuple[float, float] = BOT_DELAY,
        simulations: int | None = None,
    ) -> None:
        self.bot_delay = bot_delay
        self.simulations = simulations
        self.config: TableConfig | None = None
        self.game: Game | None = None
        self.bots: dict[int, Bot] = {}
        self.listener: Listener | None = None  # se llama cada vez que cambia el estado
        self._runner: asyncio.Task | None = None
        self._observed_hand = 0

    # --- Intenciones del cliente ---

    def new_game(self, config: TableConfig) -> None:
        self._stop_runner()
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
        """Vuelve a empezar con la misma configuración y fichas virtuales nuevas, gratis."""
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
        )
        return state

    # --- Interno ---

    def _require_game(self) -> Game:
        if self.game is None:
            raise SessionError("Primero hay que empezar una partida")
        return self.game

    def _deal(self) -> None:
        assert self.game is not None
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
