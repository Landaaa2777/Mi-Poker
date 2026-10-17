import { useEffect, useState } from "react";
import { hasPage } from "../games";
import { useAccount } from "../shared/AccountContext";
import { Emblem } from "../shared/components/Emblem";
import { GameCard } from "./GameCard";
import {
  cardState,
  fetchGames,
  fetchMyPartidas,
  menuOrder,
  type GameEntry,
  type PartidaInfo,
} from "./hub";

/** Menú principal: una tarjeta por juego del registro del servidor. */
export function HubPage() {
  const { identity, refresh } = useAccount();
  const [games, setGames] = useState<GameEntry[] | null>(null);
  const [partidas, setPartidas] = useState<PartidaInfo[]>([]);
  const [problem, setProblem] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  // Al volver al menú, el saldo puede haber cambiado en alguna mesa.
  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    let closed = false;
    setProblem(null);
    Promise.all([fetchGames(), fetchMyPartidas()]).then(
      ([registry, mine]) => {
        if (closed) return;
        setGames(registry);
        setPartidas(mine);
      },
      () => {
        if (!closed) setProblem("No se pudo conectar con el servidor.");
      },
    );
    return () => {
      closed = true;
    };
  }, [attempt, identity]);

  return (
    <>
      <section className="felt rim relative overflow-hidden rounded-[1.6rem] px-5 py-6 sm:px-8 sm:py-8">
        <div className="flex items-center gap-4 sm:gap-6">
          <Emblem className="h-16 w-16 shrink-0 text-amber-300 drop-shadow-[0_4px_10px_rgb(0_0_0/0.5)] sm:h-20 sm:w-20" />
          <div>
            <h1 className="gold-text font-display text-3xl font-black tracking-tight sm:text-4xl">
              Elige tu mesa
            </h1>
            <p className="mt-1 text-sm text-emerald-50/85 sm:text-base">
              Juegos de cartas contra bots, con fichas virtuales.
            </p>
          </div>
        </div>
      </section>

      {problem && (
        <p role="alert" className="flex flex-wrap items-center gap-3 rounded-lg bg-rose-800 px-3 py-2 text-sm">
          {problem}
          <button className="btn-dark h-8 px-3 text-xs" onClick={() => setAttempt((n) => n + 1)}>
            Reintentar
          </button>
        </p>
      )}
      {!games && !problem && <p className="panel px-3 py-2 text-sm">Cargando juegos…</p>}

      {games && (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Juegos">
          {menuOrder(games, hasPage).map((game) => (
            <li key={game.id}>
              <GameCard game={game} state={cardState(game, partidas, hasPage(game.id))} />
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
