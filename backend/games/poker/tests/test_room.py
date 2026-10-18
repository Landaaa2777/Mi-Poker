"""La mesa de poker de una sala: varias personas, 30 segundos por decisión y el saldo de cada una."""

import asyncio
import json

import pytest

from core.room import ROOM_LEVEL
from core.session import SessionError
from core.testing import room_context, until
from games.poker.protocol import RoomConfig
from games.poker.room import PokerRoom


def play(coroutine):
    return asyncio.run(coroutine)


def act(room, user_id, action, amount=0):
    room.handle(user_id, json.dumps({"type": "action", "action": action, "amount": amount}))


def to_act(room):
    """El id de la persona a la que le toca, o None si le toca a un bot o no hay mano."""
    hand = room.game.hand
    if hand is None or hand.is_complete or hand.to_act is None:
        return None
    person = room.person_at.get(hand.to_act.seat)
    return person.user_id if person else None


def accounts(room):
    return [person.account for person in room.context.people]


def chips_on_table(room):
    game = room.game
    return sum(player.stack for player in game.players) + (game.hand.pot if game.hand_in_progress else 0)


def test_each_person_sees_only_their_own_cards():
    async def scenario():
        room = PokerRoom(room_context(RoomConfig(bots=1), ("Ana", "Luis", "Eva")))
        for user_id, seat in room.seat_of.items():
            state = room.state(user_id)
            assert state["human_seat"] == seat and state["viewer_seat"] == seat
            assert len(state["hole_cards"]) == 2
            for entry in state["seats"]:
                assert entry["is_human"] == (entry["seat"] == seat)  # "soy yo"
                assert entry["person"] == (entry["seat"] in (0, 1, 2))
                if entry["seat"] != seat:
                    assert entry["hole_cards"] is None  # las de los demás, nunca
            assert "player_name" not in state["config"]
        assert [player.name for player in room.game.players][:3] == ["Ana", "Luis", "Eva"]
        assert room.state(1)["seats"][3]["level"] == "Medio"
        room.close()

    play(scenario())


def test_only_whoever_has_the_turn_can_act():
    async def scenario():
        room = PokerRoom(room_context(RoomConfig()))
        waiting = to_act(room)
        other = 2 if waiting == 1 else 1
        with pytest.raises(SessionError, match="No es tu turno"):
            act(room, other, "call")
        with pytest.raises(SessionError):
            act(room, waiting, "raise", 1)  # subir menos del mínimo
        with pytest.raises(SessionError, match="Ya no estás"):
            act(room, 99, "call")
        with pytest.raises(Exception):
            room.handle(waiting, json.dumps({"type": "new_game"}))  # en una sala no se reparte a mano
        act(room, waiting, "call")
        assert to_act(room) == other
        room.close()

    play(scenario())


def test_when_time_runs_out_the_server_checks_or_folds():
    async def scenario():
        room = PokerRoom(room_context(RoomConfig(), turn_seconds=0.05))
        room.start()
        # Nadie juega: antes del flop la ciega pequeña no puede pasar, así que se retira.
        await until(lambda: room.game.hand_number >= 3)
        room.close()
        for account in accounts(room):
            assert len(account.hands) >= 2 and account.hands[0].difficulty == ROOM_LEVEL
        # Las fichas no salen de la mesa: lo que pierde una persona lo gana la otra.
        assert sum(account.balance() for account in accounts(room)) == 20_000

    play(scenario())


def test_people_play_their_hands_and_the_next_one_is_dealt():
    async def scenario():
        room = PokerRoom(room_context(RoomConfig(), ("Ana", "Luis", "Eva")))
        room.start()
        while room.game.hand_number == 1:
            await until(lambda: to_act(room) is not None or room.game.hand_number > 1)
            if room.game.hand_number > 1:
                break
            user_id = to_act(room)
            legal = room.game.hand.legal_actions()
            act(room, user_id, "check" if legal.can_check else "call")
            assert chips_on_table(room) == 3 * 1000
        await until(lambda: room.game.hand_in_progress)
        room.close()
        # La primera mano se jugó hasta el final y cada saldo se puso al día.
        assert all(len(account.hands) == 1 for account in accounts(room))
        assert sum(account.balance() for account in accounts(room)) == 3 * 10_000

    play(scenario())


def test_whoever_leaves_folds_and_takes_their_chips():
    async def scenario():
        room = PokerRoom(room_context(RoomConfig(), ("Ana", "Luis", "Eva")))
        room.start()
        await until(lambda: to_act(room) is not None)
        leaving = to_act(room)
        seat = room.seat_of[leaving]
        room.abandon(leaving)
        await until(lambda: room.game.players[seat].folded or not room.game.hand_in_progress)
        # Se retira en cuanto le toca, sin esperar su tiempo.
        assert room.game.players[seat].folded
        assert room.state(leaving)["seats"][seat]["gone"]
        with pytest.raises(SessionError):
            act(room, leaving, "call")
        # Los demás terminan la mano; al acabar, deja la mesa con sus fichas.
        while room.game.hand_number == 1:
            await until(lambda: to_act(room) is not None or room.game.hand_number > 1)
            if room.game.hand_number > 1:
                break
            legal = room.game.hand.legal_actions()
            act(room, to_act(room), "check" if legal.can_check else "call")
        await until(lambda: room.game.hand_in_progress)
        room.close()
        assert room.game.players[seat].stack == 0 and room.seated_chips(leaving) == 0
        # Lo que perdió en esa mano se descontó de su saldo; nada más.
        account = room.person_at[seat].account
        assert account.balance() == 10_000 + account.hands[0].chips_delta <= 10_000

    play(scenario())


def test_the_game_ends_when_only_one_player_has_chips():
    async def scenario():
        # Fichas justas para la ciega grande: la partida se acaba en pocas manos.
        options = RoomConfig(starting_stack=10, small_blind=5, big_blind=10)
        room = PokerRoom(room_context(options, turn_seconds=0.02))
        room.start()
        await until(lambda: room.finished)
        state = room.state(1)
        assert state["game_over"] and state["winner_seat"] in (0, 1)
        assert room.seated_chips(1) == room.seated_chips(2) == 0
        winner = room.person_at[state["winner_seat"]].account
        assert winner.hands[-1].game_won and winner.balance() == 10_010
        assert sum(account.balance() for account in accounts(room)) == 20_000

    play(scenario())


def test_seated_chips_follow_the_hand():
    async def scenario():
        room = PokerRoom(room_context(RoomConfig(starting_stack=2000)))
        # En plena mano, las fichas sentadas incluyen las ciegas ya puestas.
        assert room.seated_chips(1) == room.seated_chips(2) == 2000
        room.close()

    play(scenario())
