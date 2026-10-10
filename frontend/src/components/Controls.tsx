import { useEffect, useState } from "react";
import type { ActionName, GameState } from "../types";

interface Props {
  state: GameState;
  disabled: boolean; // ya se envió una intención y el servidor aún no ha contestado
  onAction: (action: ActionName, amount?: number) => void;
}

const BIG =
  "flex h-16 flex-col items-center justify-center px-2 text-base uppercase leading-tight tracking-wide sm:text-lg";

/** Botones de acción. Solo envían la intención; el servidor decide si es legal. */
export function Controls({ state, disabled, onAction }: Props) {
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

  const shortcuts = [
    { label: "Mín", value: minRaise },
    { label: "½ bote", value: potFraction(0.5) },
    { label: "Bote", value: potFraction(1) },
    { label: "Máx", value: maxRaise },
  ];
  // Varios atajos pueden dar el mismo monto: se marca solo el primero.
  const active = shortcuts.findIndex((shortcut) => shortcut.value === amount);
  const raiseVerb = amount === maxRaise ? "All-in" : opening ? "Apostar" : "Subir a";

  return (
    <div className="flex h-full flex-col justify-end gap-3">
      {legal.can_raise && (
        <>
          <div className="grid grid-cols-4 overflow-hidden rounded-full border border-amber-400/40 bg-black/50 text-xs font-extrabold uppercase tracking-wide sm:text-sm">
            {shortcuts.map((shortcut, index) => (
              <button
                key={shortcut.label}
                className={`border-l border-amber-400/25 py-2 first:border-l-0 ${index === active ? "bg-gradient-to-b from-amber-200 to-amber-500 text-stone-900" : "text-amber-100 hover:bg-white/10"}`}
                onClick={() => setAmount(shortcut.value)}
              >
                {shortcut.label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <input
              type="number"
              min={minRaise}
              max={maxRaise}
              step={1}
              value={amount}
              onChange={(event) => setAmount(Number(event.target.value))}
              className={`w-24 rounded-md bg-white px-2 py-1.5 text-center text-lg font-bold text-stone-900 outline-none ring-2 ${valid ? "ring-amber-400/60 focus:ring-amber-300" : "ring-rose-500"}`}
              aria-label={`Monto: mínimo ${minRaise}, máximo ${maxRaise}`}
            />
            <input
              type="range"
              min={minRaise}
              max={maxRaise}
              step={1}
              value={valid ? amount : minRaise}
              onChange={(event) => setAmount(Number(event.target.value))}
              className="h-2 flex-1"
              aria-label="Monto de la subida"
            />
          </div>
        </>
      )}

      <div className={`grid gap-2.5 pb-1 ${legal.can_raise ? "grid-cols-3" : "grid-cols-2"}`}>
        <button className={`${BIG} btn-red`} disabled={disabled} onClick={() => onAction("fold")}>
          Retirarse
        </button>
        {legal.can_check ? (
          <button
            className={`${BIG} btn-green`}
            disabled={disabled}
            onClick={() => onAction("check")}
          >
            Pasar
          </button>
        ) : (
          <button
            className={`${BIG} btn-green`}
            disabled={disabled}
            onClick={() => onAction("call")}
          >
            <span>Igualar {legal.call_amount}</span>
            {callsAllIn && <span className="text-xs font-bold normal-case">(all-in)</span>}
          </button>
        )}
        {legal.can_raise && (
          <button
            className={`${BIG} btn-gold`}
            disabled={disabled || !valid}
            onClick={() => onAction("raise", amount)}
          >
            <span>{raiseVerb}</span>
            <span className="tabular-nums">{valid ? amount : "—"}</span>
          </button>
        )}
      </div>
    </div>
  );
}
