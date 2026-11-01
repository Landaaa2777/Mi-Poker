"""Simula miles de partidas de Prisma entre bots y muestra cuántas gana cada nivel.

    python scripts/simulate_prisma.py                 4000 partidas a cuatro
    python scripts/simulate_prisma.py --games 20000   más partidas, resultado más estable
    python scripts/simulate_prisma.py --duels         además, duelos de dos en dos
    python scripts/simulate_prisma.py --modo sin_tregua   en otro modo (clasico, doble_cara, sin_tregua)

En cada partida juega un bot de cada nivel, rotando los asientos. Solo para
entretenimiento.
"""

from __future__ import annotations

import argparse
import sys
import time
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.bots import LEVEL_NAMES  # noqa: E402
from games.prisma.bots.simulation import run_tournament  # noqa: E402
from games.prisma.engine import Mode, PrismaRules  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulación de Prisma por nivel.")
    parser.add_argument("--games", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--duels", action="store_true", help="también duelos de dos en dos")
    parser.add_argument("--modo", choices=[mode.value for mode in Mode], default=Mode.CLASICO.value)
    args = parser.parse_args()
    rules = PrismaRules(mode=Mode(args.modo))

    start = time.time()
    levels = list(LEVEL_NAMES)
    results = run_tournament(levels, args.games, args.seed, rules)
    print(f"{args.games} partidas a cuatro (un bot de cada nivel), modo {args.modo}. Partidas ganadas:\n")
    for level, result in results.items():
        print(f"  {LEVEL_NAMES[level]:<10}{100 * result.win_rate:>6.1f} %  ± {100 * result.margin:.1f}")
    rates = [results[level].win_rate for level in levels]
    if rates != sorted(rates):
        print("\n  ATENCIÓN: el orden no es Experto > Difícil > Medio > Fácil.")
    if args.duels:
        print("\nDuelos (partidas ganadas por el primero):")
        for weaker, stronger in combinations(levels, 2):
            duel = run_tournament([stronger, weaker], args.games // 2, args.seed, rules)
            print(f"  {LEVEL_NAMES[stronger]} contra {LEVEL_NAMES[weaker]}: {100 * duel[stronger].win_rate:.1f} %")
    print(f"\nTiempo: {time.time() - start:.0f} s")


if __name__ == "__main__":
    main()
