"""La estrategia básica del blackjack: la mejor jugada sin contar cartas.

Las tablas son las de 6 mazos con doblar después de dividir permitido. Cada fila
dice qué hacer contra cada carta del crupier, de izquierda a derecha:

    2  3  4  5  6  7  8  9  10  As

Códigos de cada casilla:
    H  pedir            S  plantarse         P  dividir
    D  doblar (si no se puede, pedir)        Ds doblar (si no se puede, plantarse)
    Rh rendirse (si no se puede, pedir)      Rs rendirse (si no se puede, plantarse)
    Rp rendirse (si no se puede, dividir)

Ejemplo: con 16 duro contra un 10 del crupier toca "Rh": rendirse si la mesa
lo permite y, si no, pedir carta.
"""

from __future__ import annotations

from collections.abc import Sequence

from core.cards import Card
from games.blackjack.engine import Action, Rules, card_value, hand_total

UPCARDS = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11)  # el As vale 11

# Totales duros (sin As que valga 11).
HARD: dict[int, list[str]] = {
    8: ["H"] * 10,
    9: ["H", "D", "D", "D", "D", "H", "H", "H", "H", "H"],
    10: ["D"] * 8 + ["H", "H"],
    11: ["D"] * 9 + ["H"],
    12: ["H", "H", "S", "S", "S", "H", "H", "H", "H", "H"],
    13: ["S"] * 5 + ["H"] * 5,
    14: ["S"] * 5 + ["H"] * 5,
    15: ["S"] * 5 + ["H", "H", "H", "Rh", "H"],
    16: ["S"] * 5 + ["H", "H", "Rh", "Rh", "Rh"],
    17: ["S"] * 10,
}

# Totales blandos (un As que vale 11): de As-2 (13) a As-9 (20).
SOFT: dict[int, list[str]] = {
    12: ["H"] * 10,  # dos ases que ya no se pueden dividir
    13: ["H", "H", "H", "D", "D", "H", "H", "H", "H", "H"],
    14: ["H", "H", "H", "D", "D", "H", "H", "H", "H", "H"],
    15: ["H", "H", "D", "D", "D", "H", "H", "H", "H", "H"],
    16: ["H", "H", "D", "D", "D", "H", "H", "H", "H", "H"],
    17: ["H", "D", "D", "D", "D", "H", "H", "H", "H", "H"],
    18: ["S", "Ds", "Ds", "Ds", "Ds", "S", "S", "H", "H", "H"],
    19: ["S"] * 10,
    20: ["S"] * 10,
}

# Parejas, por el valor de cada carta. El 5-5 se juega como un 10 duro y el
# 10-10 como un 20: nunca se dividen.
PAIRS: dict[int, list[str]] = {
    2: ["P"] * 6 + ["H"] * 4,
    3: ["P"] * 6 + ["H"] * 4,
    4: ["H", "H", "H", "P", "P", "H", "H", "H", "H", "H"],
    6: ["P"] * 5 + ["H"] * 5,
    7: ["P"] * 6 + ["H"] * 4,
    8: ["P"] * 10,
    9: ["P", "P", "P", "P", "P", "S", "P", "P", "S", "S"],
    11: ["P"] * 10,
}


def _hits_soft_17_changes(rules: Rules) -> dict[tuple[str, int, int], str]:
    """Casillas que cambian cuando el crupier pide con 17 blando."""
    if not rules.dealer_hits_soft_17:
        return {}
    return {
        ("hard", 11, 11): "D",
        ("hard", 15, 11): "Rh",
        ("hard", 17, 11): "Rs",
        ("soft", 18, 2): "Ds",
        ("soft", 19, 6): "Ds",
        ("pair", 8, 11): "Rp",
    }


def strategy_code(cards: Sequence[Card], dealer_up: Card, rules: Rules, can_split: bool) -> str:
    """El código de la tabla para esta mano contra la carta vista del crupier."""
    column = UPCARDS.index(card_value(dealer_up))
    changes = _hits_soft_17_changes(rules)
    up = UPCARDS[column]
    if can_split and len(cards) == 2 and card_value(cards[0]) == card_value(cards[1]):
        pair = card_value(cards[0])
        if pair in PAIRS:
            return changes.get(("pair", pair, up), PAIRS[pair][column])
    total, soft = hand_total(cards)
    if soft and total < 21:
        return changes.get(("soft", total, up), SOFT[max(total, 12)][column])
    row = min(max(total, 8), 17)
    return changes.get(("hard", total, up), HARD[row][column])


def resolve(code: str, legal: Sequence[Action]) -> Action:
    """Convierte un código de la tabla en una acción permitida ahora mismo."""
    wanted = {
        "H": [Action.HIT],
        "S": [Action.STAND],
        "D": [Action.DOUBLE, Action.HIT],
        "Ds": [Action.DOUBLE, Action.STAND],
        "P": [Action.SPLIT, Action.HIT],
        "Rh": [Action.SURRENDER, Action.HIT],
        "Rs": [Action.SURRENDER, Action.STAND],
        "Rp": [Action.SURRENDER, Action.SPLIT, Action.HIT],
    }[code]
    for action in wanted:
        if action in legal:
            return action
    return Action.STAND if Action.STAND in legal else legal[0]


def basic_strategy(
    cards: Sequence[Card], dealer_up: Card, rules: Rules, legal: Sequence[Action]
) -> Action:
    """La jugada de la estrategia básica entre las permitidas (`legal`)."""
    code = strategy_code(cards, dealer_up, rules, Action.SPLIT in legal)
    return resolve(code, legal)
