"""Ayudantes compartidos por los tests del motor."""

from __future__ import annotations

import random

from poker_engine import Action, ActionType, Deck, Game, GameConfig, LegalActions, parse_cards

FOLD = Action(ActionType.FOLD)
CHECK = Action(ActionType.CHECK)
CALL = Action(ActionType.CALL)
ALL_IN = Action(ActionType.ALL_IN)


def raise_to(amount: int) -> Action:
    return Action(ActionType.RAISE, amount)


def make_game(stacks: list[int], button: int = 0, sb: int = 50, bb: int = 100) -> Game:
    """Mesa con un stack distinto por asiento y el botón en un asiento fijo."""
    names = tuple(f"P{seat}" for seat in range(len(stacks)))
    game = Game(GameConfig(names, max(stacks), sb, bb), button_seat=button)
    for player, stack in zip(game.players, stacks):
        player.stack = stack
    return game


def stacked_deck(holes: dict[int, str], board: str, button: int) -> Deck:
    """Mazo preparado para que cada asiento reciba las cartas indicadas.

    Reproduce el orden de reparto del motor: una carta a cada jugador
    empezando a la izquierda del botón, dos vueltas, y luego la mesa.
    """
    seats = sorted(holes)
    order = [s for s in seats if s > button] + [s for s in seats if s <= button]
    cards = {seat: parse_cards(text) for seat, text in holes.items()}
    first_round = [cards[seat][0] for seat in order]
    second_round = [cards[seat][1] for seat in order]
    return Deck(first_round + second_round + parse_cards(board))


def random_action(legal: LegalActions, rng: random.Random) -> Action:
    """Una acción legal cualquiera, con subidas de tamaños muy variados."""
    roll = rng.random()
    if legal.can_raise and roll < 0.30:
        if rng.random() < 0.2:
            return ALL_IN
        span = legal.max_raise_to - legal.min_raise_to
        return raise_to(legal.min_raise_to + int(span * rng.random() ** 3))
    if legal.call_amount > 0 and roll < 0.45:
        return FOLD
    return CALL
