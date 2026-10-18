"""Una partida de Prisma en memoria: un humano contra bots, con el servidor como autoridad.

Prisma no usa fichas: se juega por ganar la ronda (o por puntos). Lo único
delicado es el aviso de "¡Última!": quien se queda con una carta sin decirlo
puede ser pillado hasta que actúa el siguiente jugador. Los bots, antes de
jugar, se toman su tiempo de pensar: ese rato es el que tiene el humano para
decir "¡Última!" (o para pillar a un bot despistado).
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

from core.bots import BOT_DELAY, pick_names
from core.session import Listener, SessionError
from games.prisma.bots import PrismaBot, create_bot
from games.prisma.bots.simulation import apply
from games.prisma.engine import IllegalMove, Phase, PrismaGame, PrismaRules, table_view

from .protocol import CLIENT_MESSAGE, ChooseColor, NewGame, Play, PrismaConfig, options

HUMAN_SEAT = 0


class PrismaSession:
    """Estado de la partida de Prisma de un jugador."""

    def __init__(self, bot_delay: tuple[float, float] = BOT_DELAY, player_name: str | None = None) -> None:
        self.bot_delay = bot_delay
        self.player_name = player_name  # con cuenta, el nombre en la mesa es el suyo
        self.config: PrismaConfig | None = None
        self.game: PrismaGame | None = None
        self.bots: dict[int, PrismaBot] = {}
        self.listener: Listener | None = None
        self._runner: asyncio.Task | None = None
        self._rng = random.Random()  # solo para el orden en que los bots se fijan en el "¡Última!"

    # --- Intenciones del cliente ---

    def handle(self, text: str) -> None:
        """Valida un mensaje del cliente (texto JSON) y hace lo que pide."""
        message = CLIENT_MESSAGE.validate_json(text)
        if isinstance(message, NewGame):
            config = message.config
            if self.player_name is not None:
                config = config.model_copy(update={"player_name": self.player_name})
            self.new_game(config)
            return
        if message.type == "restart":
            if self.config is None:
                raise SessionError("Todavía no hay ninguna partida que reiniciar")
            self.new_game(self.config)
            return
        game = self._require_game()
        try:
            if isinstance(message, Play):
                self._before_my_move()
                game.play(HUMAN_SEAT, message.card, message.color, declare=message.declare)
            elif isinstance(message, ChooseColor):
                game.choose_color(HUMAN_SEAT, message.color)
            elif message.type == "draw":
                self._before_my_move()
                game.draw(HUMAN_SEAT)
            elif message.type == "pass":
                game.pass_turn(HUMAN_SEAT)
            elif message.type == "challenge":
                game.challenge(HUMAN_SEAT)
            elif message.type == "accept":
                game.accept(HUMAN_SEAT)
            elif message.type == "last":
                game.declare_last(HUMAN_SEAT)
            elif message.type == "catch":
                game.catch(HUMAN_SEAT)
            else:  # next_round
                game.next_round()
        except IllegalMove as error:
            raise SessionError(str(error)) from error
        self._start_runner()

    def new_game(self, config: PrismaConfig) -> None:
        self._stop_runner()
        names = [config.player_name, *pick_names(config.bots, taken=[config.player_name])]
        rules = PrismaRules(
            challenge=config.challenge,
            stack_draw2=config.stack_draw2,
            stack_draw4=config.stack_draw4,
            scoring=config.scoring,
            target=config.target,
        )
        self.config = config
        self.game = PrismaGame(names, rules)
        self.bots = {seat: create_bot(config.difficulty, name) for seat, name in enumerate(names) if seat != HUMAN_SEAT}
        self.game.start_round()
        self._start_runner()

    # --- Estado ---

    def options(self) -> dict[str, Any]:
        return options()

    @property
    def in_progress(self) -> bool:
        return self.game is not None and not self.game.game_over

    def seated_chips(self) -> int:
        return 0  # Prisma no usa fichas

    def close(self) -> None:
        self._stop_runner()

    def state(self) -> dict[str, Any] | None:
        """Lo que ve el humano: su mano y cuántas cartas tienen los demás, nunca cuáles."""
        game = self.game
        if game is None or self.config is None:
            return None
        state = table_view(game, HUMAN_SEAT).to_dict()
        for player in state["players"]:
            bot = self.bots.get(player["seat"])
            player["is_human"] = bot is None
            player["level"] = bot.level_name if bot else ""
        state.update(config=self.config.model_dump(), human_seat=HUMAN_SEAT)
        return state

    # --- Interno ---

    def _require_game(self) -> PrismaGame:
        if self.game is None:
            raise SessionError("Primero hay que empezar una partida")
        return self.game

    def _before_my_move(self) -> None:
        """Si un bot se quedó con una carta sin avisar, los demás bots aún pueden pillarle."""
        game = self._require_game()
        if game.vulnerable is not None and game.vulnerable != HUMAN_SEAT:
            self._resolve_last_call()

    def _resolve_last_call(self) -> None:
        """Antes de que actúe el siguiente: el despistado puede darse cuenta, o le pillan."""
        game = self.game
        assert game is not None
        vulnerable = game.vulnerable
        if vulnerable is None:
            return
        bot = self.bots.get(vulnerable)
        if bot is not None and bot.says_last(table_view(game, vulnerable)):
            game.declare_last(vulnerable)
            return
        others = [seat for seat in self.bots if seat != vulnerable]
        self._rng.shuffle(others)
        for seat in others:
            if self.bots[seat].catches(table_view(game, seat)):
                game.catch(seat)
                return

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
        while game.phase != Phase.ROUND_OVER and game.turn != HUMAN_SEAT:
            seat = game.turn
            # El bot piensa: mientras, el humano puede decir "¡Última!" o pillar a alguien.
            await asyncio.sleep(random.uniform(*self.bot_delay))
            if self.game is not game or game.turn != seat or game.phase == Phase.ROUND_OVER:
                return  # la partida cambió mientras el bot pensaba
            self._resolve_last_call()
            apply(game, seat, self.bots[seat])
            await self._notify()

    async def _notify(self) -> None:
        if self.listener is not None:
            await self.listener()
