"""Juega una mano por consola con jugadores que actúan al azar.

Sirve para ver el motor funcionando. Muestra las cartas de todos porque es una
demostración; en el juego real cada jugador solo ve las suyas.

    python scripts/demo_hand.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from games.poker.engine import (  # noqa: E402
    CATEGORY_NAMES,
    Action,
    ActionType,
    Game,
    GameConfig,
    Hand,
    LegalActions,
)

STREET_NAMES = {"flop": "FLOP", "turn": "TURN", "river": "RIVER"}


def random_action(legal: LegalActions) -> Action:
    roll = random.random()
    if legal.can_raise and roll < 0.25:
        span = legal.max_raise_to - legal.min_raise_to
        return Action(ActionType.RAISE, legal.min_raise_to + int(span * random.random() ** 4))
    if legal.call_amount > 0 and roll < 0.45:
        return Action(ActionType.FOLD)
    return Action(ActionType.CALL)


def show(cards) -> str:
    return " ".join(str(card) for card in cards)


def describe(event, names: dict[int, str]) -> str:
    name = names.get(event.seat, "")
    suffix = " (all-in)" if event.all_in else ""
    if event.kind == "small_blind":
        return f"  {name} pone la ciega pequeña: {event.amount}{suffix}"
    if event.kind == "big_blind":
        return f"  {name} pone la ciega grande: {event.amount}{suffix}"
    if event.kind == "board":
        return f"\n--- {STREET_NAMES[event.action]}: {show(event.cards)} ---"
    if event.kind == "refund":
        return f"  Se devuelven {event.amount} fichas no igualadas a {name}"
    if event.kind == "show":
        return f"  {name} muestra {show(event.cards)}"
    if event.kind == "win":
        return f"  {name} gana {event.amount}"
    if event.action == "fold":
        return f"  {name} se retira"
    if event.action == "check":
        return f"  {name} pasa"
    if event.action == "call":
        return f"  {name} iguala {event.amount}{suffix}"
    return f"  {name} sube a {event.amount}{suffix}"


def print_result(hand: Hand, names: dict[int, str]) -> None:
    result = hand.result
    if not result.showdown:
        print("\nTodos los demás se retiraron: no hay showdown.")
        return
    print(f"\n--- SHOWDOWN (mesa: {show(result.board)}) ---")
    for seat, value in result.hand_values.items():
        print(f"  {names[seat]}: {show(result.shown_hands[seat])} -> {CATEGORY_NAMES[value[0]]}")
    for index, award in enumerate(result.awards):
        label = "Bote principal" if index == 0 else f"Bote lateral {index}"
        winners = ", ".join(f"{names[seat]} +{amount}" for seat, amount in award.payouts.items())
        print(f"  {label} ({award.amount}): {winners}")


def main() -> None:
    print("Solo para entretenimiento. Sin dinero real.\n")
    game = Game(GameConfig(("Ana", "Beto", "Caro", "Dani"), 1000, 5, 10))
    names = {p.seat: p.name for p in game.players}
    chips_before = game.total_chips

    hand = game.start_hand()
    print(f"Mano {hand.number} | botón: {names[game.button_seat]} | blinds 5/10")
    for player in game.players:
        print(f"  {player.name}: {show(player.hole_cards)}")
    print("\n--- PREFLOP ---")

    printed = 0
    while True:
        for event in hand.events[printed:]:
            print(describe(event, names))
        printed = len(hand.events)
        if hand.is_complete:
            break
        hand.act(hand.to_act.seat, random_action(hand.legal_actions()))

    print_result(hand, names)

    print("\nFichas al terminar:")
    for player in game.players:
        print(f"  {player.name}: {player.stack}")
    print(f"Total de fichas: {game.total_chips} (al empezar: {chips_before})")


if __name__ == "__main__":
    main()
