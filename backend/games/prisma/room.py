"""La mesa de Prisma de una sala: varias personas (y quizá bots), sin fichas.

Usa el mismo motor que la partida contra bots. Lo que cambia:

- Cada persona ve solo su mano; de las demás, cuántas cartas tienen.
- Cualquiera puede pillar a quien se quedó con una carta sin decir "¡Última!",
  hasta que actúe el siguiente: las personas con su botón y los bots al ir a
  jugar, cada uno con la probabilidad de su nivel.
- 30 segundos por decisión: si se acaban, roba y pasa (y si tenía que elegir,
  acepta el +4 o elige el color del que más cartas tiene).
- Jugando a puntos, la ronda siguiente empieza sola tras una pausa.
- Quien se va de la sala deja su sitio a un bot, que sigue con sus cartas.
"""

from __future__ import annotations

import asyncio
import random
from collections import Counter
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from core.bots import pick_names
from core.room import RoomContext, RoomTable
from core.session import SessionError
from games.prisma.bots import PrismaBot, create_bot
from games.prisma.bots.simulation import apply
from games.prisma.engine import IllegalMove, Phase, PrismaGame, PrismaRules, table_view
from games.prisma.engine.cards import Color

from .protocol import ChooseColor, Play


class RoomSimple(BaseModel):
    """Intenciones sin más datos. Empezar y seguir con otra ronda lo lleva la sala."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["draw", "pass", "challenge", "accept", "last", "catch"]


ROOM_MESSAGE = TypeAdapter(Annotated[Play | ChooseColor | RoomSimple, Field(discriminator="type")])


class PrismaRoom(RoomTable):
    def __init__(self, context: RoomContext) -> None:
        super().__init__(context)
        options = self.options
        people = [person.name for person in context.people]
        names = [*people, *pick_names(options.bots, taken=people)]
        rules = PrismaRules(
            challenge=options.challenge,
            stack_draw2=options.stack_draw2,
            stack_draw4=options.stack_draw4,
            scoring=options.scoring,
            target=options.target,
        )
        self.game = PrismaGame(names, rules)
        self.bots: dict[int, PrismaBot] = {
            seat: create_bot(options.difficulty, name)
            for seat, name in enumerate(names)
            if seat >= len(people)
        }
        self._rng = random.Random()  # solo para el orden en que los bots se fijan en el "¡Última!"
        self.game.start_round()

    # --- Intenciones de las personas ---

    def handle(self, user_id: int, text: str) -> None:
        message = ROOM_MESSAGE.validate_json(text)
        seat = self.seat(user_id)
        game = self.game
        try:
            if isinstance(message, Play):
                self._before_move(seat)
                game.play(seat, message.card, message.color, declare=message.declare)
            elif isinstance(message, ChooseColor):
                game.choose_color(seat, message.color)
            elif message.type == "draw":
                self._before_move(seat)
                game.draw(seat)
            elif message.type == "pass":
                game.pass_turn(seat)
            elif message.type == "challenge":
                game.challenge(seat)
            elif message.type == "accept":
                game.accept(seat)
            elif message.type == "last":
                game.declare_last(seat)
            else:
                game.catch(seat)
        except IllegalMove as error:
            raise SessionError(str(error)) from error
        if message.type not in ("last", "catch"):
            self.timer.stop()  # la siguiente decisión tiene su tiempo entero
        self.wake()

    # --- Estado ---

    def state(self, user_id: int) -> dict[str, Any] | None:
        """Lo que ve una persona: su mano y cuántas cartas tienen los demás, nunca cuáles."""
        seat = self.seat_of.get(user_id)
        state = table_view(self.game, seat).to_dict()
        for player in state["players"]:
            number = player["seat"]
            bot = self.bots.get(number)
            player["is_human"] = number == seat  # "soy yo"
            player["person"] = number in self.person_at and number not in self.gone
            player["gone"] = number in self.gone  # se fue: ahora juega un bot en su sitio
            player["level"] = bot.level_name if bot else ""
        state.update(
            config=self.options.model_dump(exclude={"player_name"}),
            human_seat=seat,
            game_over=self.finished,
            timer=self.timer.describe(),
            next_round_in=self.pause_left(),
        )
        return state

    def seated_chips(self, user_id: int) -> int:
        return 0  # Prisma no usa fichas

    # --- El bucle de la partida ---

    async def _step(self) -> None:
        game = self.game
        if not any(seat not in self.gone for seat in self.person_at):
            self.finished = True  # solo quedan bots: no hay partida que seguir
            return
        if game.phase == Phase.ROUND_OVER:
            if game.game_over:
                self.finished = True
                return
            await self._pause()  # jugando a puntos: otra ronda tras ver cómo acabó esta
            game.next_round()
            await self._notify()
            return
        seat = game.turn
        if seat in self.bots:
            await self._bot_plays(seat)
        elif await self._wait_for(seat):
            if game.turn == seat and game.phase != Phase.ROUND_OVER:
                self._resolve_last_call()
                self._play_for(seat)
                await self._notify()

    def _on_abandon(self, seat: int) -> None:
        """Un bot ocupa su sitio y sigue con sus cartas."""
        game = self.game
        name = pick_names(1, taken=[player.name for player in game.players])[0]
        game.players[seat].name = name
        self.bots[seat] = create_bot(self.options.difficulty, name)

    # --- Interno ---

    def _play_for(self, seat: int) -> None:
        """Se acabó su tiempo: lo más prudente, robar y pasar."""
        game = self.game
        if game.phase == Phase.CHOOSE_COLOR:
            game.choose_color(seat, self._favorite_color(seat))
        elif game.phase == Phase.CHALLENGE:
            game.accept(seat)
        elif game.drawn is not None:
            game.pass_turn(seat)
        else:
            game.draw(seat)
            if game.phase == Phase.PLAYING and game.turn == seat and game.drawn is not None:
                game.pass_turn(seat)  # la robada se podía jugar, pero se la queda

    def _favorite_color(self, seat: int) -> Color:
        """El color del que más cartas tiene (sin contar comodines)."""
        counts = Counter(card.color for card in self.game.players[seat].hand if not card.is_wild)
        if not counts:
            return random.choice(list(Color))
        return counts.most_common(1)[0][0]

    def _before_move(self, seat: int) -> None:
        """Antes de jugar o robar: si alguien se quedó con una carta sin avisar, los bots aún pueden pillarle."""
        game = self.game
        if game.phase == Phase.PLAYING and game.turn == seat and game.vulnerable not in (None, seat):
            self._resolve_last_call()

    def _resolve_last_call(self) -> None:
        """Antes de que actúe el siguiente: un bot despistado puede darse cuenta, o le pillan."""
        game = self.game
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

    async def _bot_plays(self, seat: int) -> None:
        game = self.game
        # El bot piensa: mientras, las personas pueden decir "¡Última!" o pillar a alguien.
        await asyncio.sleep(random.uniform(*self.context.bot_delay))
        if game.turn != seat or game.phase == Phase.ROUND_OVER or seat not in self.bots:
            return
        self._resolve_last_call()
        apply(game, seat, self.bots[seat])
        await self._notify()
