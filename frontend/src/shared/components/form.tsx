// Piezas comunes de los formularios de la plataforma: los campos de las
// pantallas de inicio, los botones de elegir y los avisos del saldo.

import type { ReactNode } from "react";
import { formatChips } from "../format";

export const INPUT =
  "w-full rounded-lg border border-amber-400/30 bg-black/45 px-3 py-2 outline-none focus:border-amber-300";
export const CHOICE = "rounded-lg border px-3 py-2 text-sm font-semibold";
export const CHOSEN =
  "border-amber-100 bg-gradient-to-b from-amber-200 to-amber-500 text-stone-900 shadow-[0_0_14px_rgb(245_197_66/0.45)]";
export const NOT_CHOSEN = "border-amber-400/25 bg-white/5 text-amber-50 hover:bg-white/10";
export const CARD_CHOSEN =
  "border-amber-300 bg-amber-400/15 shadow-[0_0_16px_rgb(245_197_66/0.35)]";

/** Un campo con su etiqueta en mayúsculas pequeñas. */
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-xs font-bold uppercase tracking-[0.16em] text-amber-200/75">
        {label}
      </div>
      {children}
    </div>
  );
}

interface RefillProps {
  refillBelow: number;
  startingBalance: number;
  refilling: boolean;
  problem: string | null;
  onRefill: () => void;
}

/** Aviso de recarga gratis, cuando a la cuenta le quedan muy pocas fichas. */
export function RefillOffer({ refillBelow, startingBalance, refilling, problem, onRefill }: RefillProps) {
  return (
    <div className="rounded-xl border border-amber-400/45 bg-amber-400/10 p-3">
      <p className="text-sm text-amber-100">
        Te quedan menos de {formatChips(refillBelow)} fichas. Puedes recibir{" "}
        {formatChips(startingBalance)} fichas virtuales gratis para seguir jugando.
      </p>
      <button
        type="button"
        disabled={refilling}
        className="btn-green mt-2.5 h-11 px-5 text-sm uppercase tracking-wide"
        onClick={onRefill}
      >
        Recibir {formatChips(startingBalance)} fichas
      </button>
      {problem && (
        <p role="alert" className="mt-2 text-sm font-semibold text-amber-300">
          {problem}
        </p>
      )}
    </div>
  );
}
