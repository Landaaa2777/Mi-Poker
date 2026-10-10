import type { GameState } from "../types";

interface Props {
  state: GameState;
  disabled: boolean; // ya se envió una intención y el servidor aún no ha contestado
  onNextHand: () => void;
  onRestart: () => void;
  onConfigure: () => void;
}

const BIG =
  "h-14 rounded-xl px-5 text-base font-black uppercase tracking-wide shadow-md transition-colors disabled:opacity-40 sm:text-lg";

/** Resultado de la mano y qué se puede hacer después. */
export function ResultPanel({ state, disabled, onNextHand, onRestart, onConfigure }: Props) {
  const result = state.result;
  if (!result || state.hand_in_progress) return null;

  const name = (seat: number | string) =>
    state.seats.find((candidate) => candidate.seat === Number(seat))?.name ?? "";
  const finished = state.human_out || state.game_over;

  let headline: string | null = null;
  if (state.human_out) headline = "Te quedaste sin fichas.";
  else if (state.game_over) headline = "¡Ganaste la partida! Eliminaste a todos los bots.";

  return (
    <div className="flex h-full flex-col justify-between gap-3">
      <div className="space-y-1.5">
        <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">
          {result.showdown ? "Showdown" : "Todos los demás se retiraron"}
        </h2>
        <ul className="space-y-0.5 text-sm">
          {result.awards.map((award, index) => (
            <li key={index}>
              <span className="text-slate-400">
                {index === 0 ? "Bote principal" : `Bote lateral ${index}`} ({award.amount}):
              </span>{" "}
              {Object.entries(award.payouts)
                .map(([seat, amount]) => {
                  const hand = result.hand_names[seat];
                  return `${name(seat)} +${amount}${hand ? ` (${hand})` : ""}`;
                })
                .join(", ")}
            </li>
          ))}
        </ul>
        {headline && <p className="text-lg font-bold text-amber-300">{headline}</p>}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {finished ? (
          <button
            className={`${BIG} flex-1 bg-emerald-500 text-emerald-950 hover:bg-emerald-400`}
            disabled={disabled}
            onClick={onRestart}
            title="Fichas virtuales nuevas, gratis"
          >
            Reiniciar partida
          </button>
        ) : (
          <button
            className={`${BIG} flex-1 bg-emerald-500 text-emerald-950 hover:bg-emerald-400`}
            disabled={disabled}
            onClick={onNextHand}
          >
            Siguiente mano
          </button>
        )}
        <button
          className="h-14 rounded-xl bg-slate-700 px-4 text-sm font-semibold hover:bg-slate-600"
          onClick={onConfigure}
        >
          Cambiar configuración
        </button>
      </div>
      {finished && (
        <p className="text-xs text-slate-400">Al reiniciar recibes fichas virtuales nuevas, gratis.</p>
      )}
    </div>
  );
}
