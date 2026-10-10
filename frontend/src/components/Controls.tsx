import { useEffect, useState } from "react";
import type { ActionName, GameState } from "../types";

interface Props {
  state: GameState;
  onAction: (action: ActionName, amount?: number) => void;
}

const BUTTON = "rounded px-4 py-2 font-semibold disabled:opacity-40";

/** Botones de acción. Solo envían la intención; el servidor decide si es legal. */
export function Controls({ state, onAction }: Props) {
  const legal = state.legal_actions;
  const [amount, setAmount] = useState(0);

  // Cada vez que cambia la situación, el monto vuelve al raise mínimo.
  const minRaise = legal?.min_raise_to ?? 0;
  const maxRaise = legal?.max_raise_to ?? 0;
  useEffect(() => setAmount(minRaise), [minRaise, maxRaise, state.events.length]);

  if (!legal) return null;

  const me = state.seats.find((seat) => seat.seat === state.viewer_seat)!;
  const opening = state.current_bet === 0;
  const callsAllIn = legal.call_amount >= me.stack;
  const valid = Number.isInteger(amount) && amount >= minRaise && amount <= maxRaise;

  function clamp(value: number) {
    return Math.max(minRaise, Math.min(maxRaise, Math.round(value)));
  }
  // Apuesta total equivalente a una fracción del bote después de igualar.
  function potFraction(fraction: number) {
    return clamp(state.current_bet + fraction * (state.pot + legal!.call_amount));
  }

  return (
    <section className="space-y-3 rounded-lg bg-slate-800 p-4">
      <div className="text-sm text-amber-300">Es tu turno</div>
      <div className="flex flex-wrap gap-2">
        <button className={`${BUTTON} bg-rose-700 hover:bg-rose-600`} onClick={() => onAction("fold")}>
          Retirarse
        </button>
        {legal.can_check ? (
          <button className={`${BUTTON} bg-slate-600 hover:bg-slate-500`} onClick={() => onAction("check")}>
            Pasar
          </button>
        ) : (
          <button className={`${BUTTON} bg-sky-700 hover:bg-sky-600`} onClick={() => onAction("call")}>
            Igualar {legal.call_amount}
            {callsAllIn ? " (all-in)" : ""}
          </button>
        )}
        {legal.can_raise && (
          <button className={`${BUTTON} bg-amber-600 hover:bg-amber-500`} onClick={() => onAction("all_in")}>
            All-in ({maxRaise})
          </button>
        )}
      </div>

      {legal.can_raise && (
        <div className="space-y-2 border-t border-slate-700 pt-3">
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-sm text-slate-300" htmlFor="raise-amount">
              {opening ? "Apostar" : "Subir a"}
            </label>
            <input
              id="raise-amount"
              type="number"
              min={minRaise}
              max={maxRaise}
              step={1}
              value={amount}
              onChange={(event) => setAmount(Number(event.target.value))}
              className="w-28 rounded border border-slate-600 bg-slate-900 px-2 py-1"
            />
            <button
              className={`${BUTTON} bg-emerald-600 hover:bg-emerald-500`}
              disabled={!valid}
              onClick={() => onAction("raise", amount)}
            >
              {opening ? "Apostar" : "Subir"}
            </button>
            <span className="text-xs text-slate-400">
              mínimo {minRaise}, máximo {maxRaise}
            </span>
          </div>
          <input
            type="range"
            min={minRaise}
            max={maxRaise}
            step={1}
            value={valid ? amount : minRaise}
            onChange={(event) => setAmount(Number(event.target.value))}
            className="w-full"
            aria-label="Monto de la subida"
          />
          <div className="flex flex-wrap gap-2 text-sm">
            <button className="rounded bg-slate-700 px-2 py-1 hover:bg-slate-600" onClick={() => setAmount(minRaise)}>
              Mínimo
            </button>
            <button className="rounded bg-slate-700 px-2 py-1 hover:bg-slate-600" onClick={() => setAmount(potFraction(0.5))}>
              ½ bote
            </button>
            <button className="rounded bg-slate-700 px-2 py-1 hover:bg-slate-600" onClick={() => setAmount(potFraction(1))}>
              Bote
            </button>
            <button className="rounded bg-slate-700 px-2 py-1 hover:bg-slate-600" onClick={() => setAmount(maxRaise)}>
              Máximo
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
