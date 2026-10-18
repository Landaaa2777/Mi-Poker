"""Simula miles de rondas de blackjack por nivel de bot y muestra cuánto gana o pierde cada uno.

    python scripts/simulate_blackjack.py                  20.000 rondas por nivel
    python scripts/simulate_blackjack.py --rounds 100000  más rondas, resultado más estable
    python scripts/simulate_blackjack.py --h17            el crupier pide con 17 blando

Todos los niveles juegan las mismas rondas (los mismos zapatos), apostando
siempre la mínima. Las fichas son virtuales. Solo para entretenimiento. Sin dinero real.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.bots import LEVEL_NAMES  # noqa: E402
from games.blackjack.bots.simulation import compare, run_levels  # noqa: E402
from games.blackjack.engine import Rules  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulación de blackjack por nivel.")
    parser.add_argument("--rounds", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--h17", action="store_true", help="el crupier pide con 17 blando")
    parser.add_argument("--surrender", action="store_true", help="se permite rendirse")
    args = parser.parse_args()

    rules = Rules(dealer_hits_soft_17=args.h17, surrender=args.surrender)
    start = time.time()
    results = run_levels(list(LEVEL_NAMES), args.rounds, args.seed, rules)
    print(f"{args.rounds} rondas por nivel. Apuestas ganadas cada 100 rondas (negativo: pierde).\n")
    print(f"  {'Nivel':<10}{'resultado':>12}{'margen':>10}")
    for level, result in results.items():
        print(f"  {LEVEL_NAMES[level]:<10}{result.per_100:>+12.2f}{result.margin:>10.2f}")
    print("\nDiferencias jugando las mismas rondas (más precisas):")
    for stronger, weaker in (("medium", "easy"), ("hard", "medium"), ("expert", "hard")):
        difference, margin = compare(stronger, weaker, args.rounds, args.seed, rules)
        print(f"  {LEVEL_NAMES[stronger]} - {LEVEL_NAMES[weaker]}: {difference:+.2f} ± {margin:.2f}")
    print(f"\nTiempo: {time.time() - start:.0f} s")


if __name__ == "__main__":
    main()
