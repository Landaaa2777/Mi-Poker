"""La mesa de blackjack de una sala: varias personas contra el crupier, con el saldo de cada una."""

import asyncio
import json

import pytest

from core.session import SessionError
from core.testing import room_context, until
from games.blackjack.engine import Phase
from games.blackjack.protocol import RoomConfig
from games.blackjack.room import BlackjackRoom


def play(coroutine):
    return asyncio.run(coroutine)


def bet(room, user_id, amount=10):
    room.handle(user_id, json.dumps({"type": "bet", "amount": amount}))


def act(room, user_id, action):
    room.handle(user_id, json.dumps({"type": "action", "action": action}))


def balances(room):
    return [person.account.balance() for person in room.context.people]


def test_the_round_starts_when_everyone_has_bet():
    async def scenario():
        room = BlackjackRoom(room_context(RoomConfig(bots=1)))
        room.start()
        await asyncio.sleep(0.05)
        assert room.game.round_number == 0 and not room.timer.running  # sin prisa hasta la primera apuesta
        bet(room, 1, 20)
        room.wake()
        await until(lambda: room.timer.running)
        state = room.state(2)
        assert state["timer"]["seat"] is None  # la cuenta atrás es para quien falta por apostar
        assert [entry["bet_ready"] for entry in state["seats"]] == [True, False, False]
        assert state["my_bet"] is None and room.state(1)["my_bet"] == 20
        with pytest.raises(SessionError, match="Ya has apostado"):
            bet(room, 1, 20)
        bet(room, 2, 30)
        room.wake()
        await until(lambda: room.game.round_number == 1)
        hands = [seat.hands[0].bet if seat.hands else 0 for seat in room.game.seats]
        assert hands[:2] == [20, 30] and hands[2] > 0  # y el bot apuesta a la vez
        room.close()

    play(scenario())


def test_whoever_does_not_bet_in_time_sits_out_the_round():
    async def scenario():
        room = BlackjackRoom(room_context(RoomConfig(), turn_seconds=0.05))
        room.start()
        bet(room, 1, 50)
        room.wake()
        await until(lambda: room.game.round_number == 1)
        assert room.game.seats[0].hands and not room.game.seats[1].hands
        room.close()

    play(scenario())


def test_when_time_runs_out_the_hand_stands():
    async def scenario():
        room = BlackjackRoom(room_context(RoomConfig(), turn_seconds=0.05))
        room.start()
        bet(room, 1, 100)
        bet(room, 2, 100)
        room.wake()
        await until(lambda: room.game.phase == Phase.COMPLETE)
        room.close()
        for seat in room.game.seats:
            assert all(len(hand.cards) == 2 or hand.status == "blackjack" for hand in seat.hands)
        # Cada saldo cambió en lo que ganó o perdió esa persona.
        for person, balance in zip(room.context.people, balances(room)):
            assert balance == 10_000 + room.game.seats[room.seat_of[person.user_id]].stack - 1000

    play(scenario())


def test_only_whoever_has_the_turn_can_play():
    async def scenario():
        room = BlackjackRoom(room_context(RoomConfig()))
        room.start()
        bet(room, 1)
        bet(room, 2)
        room.wake()
        await until(lambda: room.game.phase != Phase.BETTING)
        if room.game.phase == Phase.PLAYING:
            turn = room.game.to_act[0]
            other = 2 if turn == 0 else 1
            with pytest.raises(SessionError, match="No es tu turno"):
                act(room, other, "stand")
        with pytest.raises(SessionError):
            bet(room, 1)  # con la ronda en juego no se apuesta
        room.close()

    play(scenario())


def test_whoever_leaves_stands_and_takes_their_chips():
    async def scenario():
        room = BlackjackRoom(room_context(RoomConfig(), ("Ana", "Luis", "Eva")))
        room.start()
        for user_id in (1, 2, 3):
            bet(room, user_id, 100)
        room.wake()
        await until(lambda: room.game.phase != Phase.BETTING)
        room.abandon(2)
        # Las demás personas juegan: se plantan siempre que les toca.
        while room.game.phase != Phase.COMPLETE:
            await until(
                lambda: room.game.phase == Phase.COMPLETE
                or (room.game.to_act is not None and room.game.to_act[0] in (0, 2))
                or room.game.phase == Phase.INSURANCE
            )
            if room.game.phase == Phase.INSURANCE:
                for user_id, seat in ((1, 0), (3, 2)):
                    if room.game.seats[seat].insurance_pending:
                        room.handle(user_id, json.dumps({"type": "insurance", "take": False}))
                room.wake()
                await until(lambda: room.game.phase != Phase.INSURANCE)
            elif room.game.phase == Phase.PLAYING:
                act(room, 1 if room.game.to_act[0] == 0 else 3, "stand")
                room.wake()
        await until(lambda: room.seated_chips(2) == 0)
        room.close()
        seat = room.game.seats[1]
        assert seat.stack == 0 and all(len(hand.cards) == 2 or hand.status == "blackjack" for hand in seat.hands)
        assert room.state(1)["seats"][1]["gone"]

    play(scenario())


def test_the_game_ends_when_nobody_can_bet():
    async def scenario():
        room = BlackjackRoom(room_context(RoomConfig()))
        room.start()
        room.abandon(1)
        room.abandon(2)
        await until(lambda: room.finished)
        assert room.state(1)["game_over"]

    play(scenario())
