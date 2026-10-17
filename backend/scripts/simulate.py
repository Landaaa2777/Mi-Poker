"""Simula miles de manos bot contra bot y muestra los resultados por nivel.

    python scripts/simulate.py                 mesa con un bot de cada nivel
    python scripts/simulate.py --hands 200000  más manos, resultado más estable
    python scripts/simulate.py --duels         además, duelos mano a mano

Las fichas son virtuales. Solo para entretenimiento. Sin dinero real.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from games.poker.bots import LEVELS  # noqa: E402
from games.poker.bots.simulation import BotResult, run_match  # noqa: E402

LEVEL_NAMES = {level: bot.level_name for level, bot in LEVELS.items()}


def _run_chunk(job: tuple) -> list[BotResult]:
    levels, hands, seed, simulations, personalities = job
    return run_match(levels, hands, seed, simulations, personalities)


def simulate(
    pool: ProcessPoolExecutor,
    levels: tuple[str, ...],
    hands: int,
    seed: int,
    simulations: int,
    personalities: bool,
    workers: int,
) -> list[BotResult]:
    """Reparte las manos entre varios procesos y suma los resultados."""
    chunk = max(200, -(-hands // workers) // 200 * 200)
    jobs = [
        (levels, min(chunk, hands - start), seed + 7919 * index, simulations, personalities)
        for index, start in enumerate(range(0, hands, chunk))
    ]
    totals = [BotResult(level) for level in levels]
    for results in pool.map(_run_chunk, jobs):
        for total, result in zip(totals, results):
            total.add(result)
    return totals


def print_table(title: str, results: list[BotResult]) -> None:
    print(f"\n{title}")
    print(f"  {'Nivel':<10}{'Manos':>9}{'bb/100':>10}{'± error':>10}")
    for result in sorted(results, key=lambda r: r.bb_per_100, reverse=True):
        name = LEVEL_NAMES[result.level]
        print(f"  {name:<10}{result.hands:>9}{result.bb_per_100:>+10.1f}{result.margin:>10.1f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulación bot contra bot por nivel.")
    parser.add_argument("--hands", type=int, default=60000, help="manos por mesa (60000)")
    parser.add_argument("--simulations", type=int, default=200, help="Monte Carlo por decisión (200)")
    parser.add_argument("--seed", type=int, default=2026, help="semilla, para repetir el resultado")
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 1, help="procesos en paralelo")
    parser.add_argument("--duels", action="store_true", help="añade duelos mano a mano entre niveles")
    parser.add_argument("--neutral", action="store_true", help="bots sin personalidad")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    print("Solo para entretenimiento. Sin dinero real.")
    print(f"{args.hands} manos por mesa, {args.simulations} simulaciones Monte Carlo por decisión.")
    started = time.perf_counter()
    levels = tuple(LEVELS)
    options = (args.simulations, not args.neutral, args.workers)

    with ProcessPoolExecutor(args.workers) as pool:
        table = simulate(pool, levels, args.hands, args.seed, *options)
        print_table("Mesa de 4: un bot de cada nivel", table)

        ordered = [r.level for r in sorted(table, key=lambda r: r.bb_per_100)]
        if ordered == list(levels):
            print("\n  Orden correcto: Experto > Difícil > Medio > Fácil.")
        else:
            print("\n  ATENCIÓN: el orden no es Experto > Difícil > Medio > Fácil.")

        if args.duels:
            for index, (weaker, stronger) in enumerate(combinations(levels, 2)):
                duel = simulate(pool, (weaker, stronger), args.hands, args.seed + index + 1, *options)
                print_table(f"Duelo: {LEVEL_NAMES[stronger]} contra {LEVEL_NAMES[weaker]}", duel)

    print(f"\nTiempo: {time.perf_counter() - started:.0f} s")


if __name__ == "__main__":
    main()
