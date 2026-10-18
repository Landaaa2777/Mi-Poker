"""La mesa de Prisma de una sala: varias personas, cada una con su mano y 30 segundos por decisión."""

import asyncio
import json

import pytest

from core.session import SessionError
from core.testing import room_context, until
from games.prisma.engine import Phase
from games.prisma.protocol import RoomConfig
from games.prisma.room import PrismaRoom


def play(coroutine):
    return asyncio.run(coroutine)


def send(room, user_id, message):
    room.handle(user_id, json.dumps(message))


def person_to_act(room):
    person = room.person_at.get(room.game.turn)
    return person.user_id if person and room.game.turn not in room.gone else None


def test_each_person_sees_only_their_own_hand():
    async def scenario():
        room = PrismaRoom(room_context(RoomConfig(bots=1), ("Ana", "Luis", "Eva")))
        for user_id, seat in room.seat_of.items():
            state = room.state(user_id)
            assert state["human_seat"] == seat
            assert [card["id"] for card in state["hand"]] == [card.id for card in room.game.players[seat].hand]
            for player in state["players"]:
                assert player["is_human"] == (player["seat"] == seat)
                assert player["person"] == (player["seat"] < 3)
                assert "hand" not in player  # de los demás, solo cuántas cartas tienen
        room.close()

    play(scenario())


def test_only_whoever_has_the_turn_can_play():
    async def scenario():
        room = PrismaRoom(room_context(RoomConfig()))
        if room.game.phase == Phase.CHOOSE_COLOR:
            send(room, person_to_act(room), {"type": "color", "color": "halo"})
        turn = person_to_act(room)
        other = 2 if turn == 1 else 1
        with pytest.raises(SessionError):
            send(room, other, {"type": "draw"})
        with pytest.raises(SessionError, match="pillar"):
            send(room, other, {"type": "catch"})  # nadie se ha olvidado de avisar
        with pytest.raises(Exception):
            send(room, turn, {"type": "next_round"})  # las rondas las lleva la sala
        send(room, turn, {"type": "draw"})
        room.close()

    play(scenario())


def test_when_time_runs_out_the_server_draws_and_passes():
    async def scenario():
        room = PrismaRoom(room_context(RoomConfig(), turn_seconds=0.05))
        room.start()
        await until(lambda: room.game.phase == Phase.PLAYING)
        first = room.game.turn
        cards = len(room.game.players[first].hand)
        await until(lambda: room.game.turn != first or room.game.phase != Phase.PLAYING)
        # Robó (al menos una carta) y pasó el turno sin jugar.
        assert len(room.game.players[first].hand) > cards
        assert room.game.total_cards() == 108
        room.close()

    play(scenario())


def test_a_bot_takes_the_seat_of_whoever_leaves():
    async def scenario():
        room = PrismaRoom(room_context(RoomConfig(), ("Ana", "Luis", "Eva"), turn_seconds=0.05))
        room.start()
        cards = len(room.game.players[1].hand)
        room.abandon(2)  # Luis se va
        player = room.state(1)["players"][1]
        assert player["gone"] and not player["person"] and player["name"] != "Luis"
        assert player["level"] == "Medio" and len(room.game.players[1].hand) == cards  # sigue con sus cartas
        with pytest.raises(SessionError, match="Ya no estás"):
            send(room, 2, {"type": "draw"})
        # Si se van todas las personas, la partida se acaba.
        room.abandon(1)
        room.abandon(3)
        await until(lambda: room.finished)
        assert room.state(1)["game_over"]

    play(scenario())


def test_without_scoring_one_round_is_the_whole_game():
    async def scenario():
        room = PrismaRoom(room_context(RoomConfig(bots=2), turn_seconds=0.01))
        room.start()
        await until(lambda: room.finished, timeout=60)
        assert room.game.phase == Phase.ROUND_OVER and room.game.winner is not None
        assert room.game.total_cards() == 108

    play(scenario())


def test_playing_for_points_the_next_round_starts_by_itself():
    async def scenario():
        room = PrismaRoom(room_context(RoomConfig(bots=2, scoring=True, target=2000), turn_seconds=0.01))
        room.start()
        await until(lambda: room.game.round_number >= 2, timeout=60)
        room.close()
        assert not room.finished

    play(scenario())
