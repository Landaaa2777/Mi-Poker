// Piezas comunes de los formularios de la plataforma: los campos de las
// pantallas de inicio, los botones de elegir y los avisos del saldo.

import type { ReactNode } from "react";
import { DAILY_CHIPS } from "../account";
import { describeArrival, formatChips } from "../format";
import { useNow } from "../useClock";

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

interface DailyChipsProps {
  nextAt: number | null; // cuándo llegan las próximas fichas diarias (segundos desde 1970)
  outOfChips: string | null; // si no quedan fichas para sentarse, el motivo: el aviso se destaca
}

/** Cuándo llegan las próximas fichas diarias. Destacado, con el motivo, si no quedan fichas. */
export function DailyChipsNote({ nextAt, outOfChips }: DailyChipsProps) {
  const now = useNow();
  const text =
    nextAt === null
      ? `Cada día que entras, al día siguiente te llegan ${formatChips(DAILY_CHIPS)} fichas.`
      : `Tus próximas ${formatChips(DAILY_CHIPS)} fichas llegan ${describeArrival(nextAt, now)}.`;
  if (!outOfChips) return <p className="text-sm text-emerald-50/75">{text}</p>;
  return (
    <div className="rounded-xl border border-amber-400/45 bg-amber-400/10 p-3 text-sm">
      <p className="font-semibold text-amber-300">{outOfChips}</p>
      <p className="mt-1 text-amber-100">{text}</p>
    </div>
  );
}
