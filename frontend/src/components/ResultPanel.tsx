import type { GameState } from "../types";

interface Props {
  state: GameState;
  onNextHand: () => void;
  onRestart: () => void;
  onConfigure: () => void;
}

const BUTTON = "rounded px-4 py-2 font-semibold";

/** Resultado de la mano y qué se puede hacer después. */
export function ResultPanel({ state, onNextHand, onRestart, onConfigure }: Props) {
  const result = state.result;
  if (!result || state.hand_in_progress) return null;

  const name = (seat: number | string) =>
    state.seats.find((candidate) => candidate.seat === Number(seat))?.name ?? "";
  const finished = state.human_out || state.game_over;

  let headline: string | null = null;
  if (state.human_out) headline = "Te quedaste sin fichas.";
  else if (state.game_over) headline = "¡Ganaste la partida! Eliminaste a todos los bots.";

  return (
    <section className="space-y-3 rounded-lg bg-slate-800 p-4">
      <h2 className="font-semibold">
        {result.showdown ? "Showdown" : "Todos los demás se retiraron"}
      </h2>
      <ul className="space-y-1 text-sm">
        {result.awards.map((award, index) => (
          <li key={index}>
            {index === 0 ? "Bote principal" : `Bote lateral ${index}`} ({award.amount}):{" "}
            {Object.entries(award.payouts)
              .map(([seat, amount]) => {
                const hand = result.hand_names[seat];
                return `${name(seat)} +${amount}${hand ? ` (${hand})` : ""}`;
              })
              .join(", ")}
          </li>
        ))}
      </ul>

      {headline && <p className="text-lg font-semibold text-amber-300">{headline}</p>}

      <div className="flex flex-wrap gap-2">
        {finished ? (
          <>
            <button className={`${BUTTON} bg-emerald-600 hover:bg-emerald-500`} onClick={onRestart}>
              Reiniciar partida
            </button>
            <span className="self-center text-sm text-slate-400">
              Fichas virtuales nuevas, gratis.
            </span>
          </>
        ) : (
          <button className={`${BUTTON} bg-emerald-600 hover:bg-emerald-500`} onClick={onNextHand}>
            Siguiente mano
          </button>
        )}
        <button className={`${BUTTON} bg-slate-600 hover:bg-slate-500`} onClick={onConfigure}>
          Cambiar configuración
        </button>
      </div>
    </section>
  );
}
