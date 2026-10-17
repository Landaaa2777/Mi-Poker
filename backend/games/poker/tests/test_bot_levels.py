"""Cada nivel gana al anterior: Experto > Difícil > Medio > Fácil.

Son miles de manos bot contra bot con semilla fija, así que el resultado es
siempre el mismo. La tabla completa por nivel la da `scripts/simulate.py`.
"""

import pytest

from games.poker.bots import LEVELS
from games.poker.bots.simulation import run_match

DUEL_HANDS = 12000
TABLE_HANDS = 8000


@pytest.mark.parametrize(
    ("weaker", "stronger"),
    [("easy", "medium"), ("medium", "hard"), ("hard", "expert")],
)
def test_each_level_beats_the_one_below_heads_up(weaker, stronger):
    loser, winner = run_match([weaker, stronger], DUEL_HANDS, seed=2026, simulations=100)
    assert winner.hands == loser.hands == DUEL_HANDS
    assert winner.won == pytest.approx(-loser.won, abs=1e-6)
    # Gana con claridad: bastante más que el margen de error de la simulación.
    assert winner.bb_per_100 > 2 * winner.margin > 0


def test_mixed_table_pays_the_strongest_and_charges_the_weakest():
    results = {r.level: r for r in run_match(list(LEVELS), TABLE_HANDS, seed=2026, simulations=100)}
    assert sum(r.won for r in results.values()) == pytest.approx(0, abs=1e-6)
    assert results["easy"].bb_per_100 == min(r.bb_per_100 for r in results.values())
    assert results["easy"].bb_per_100 < -2 * results["easy"].margin
    assert results["expert"].bb_per_100 > results["expert"].margin
    for level in ("medium", "hard", "expert"):
        assert results[level].bb_per_100 > 0
