import { useEffect, useId, useRef } from "react";
import { SUIT_ORDER, SUITS, SuitSymbol, type PrismaColor } from "../shapes";

interface Props {
  title: string;
  onPick: (color: PrismaColor) => void;
  onCancel?: () => void; // sin esto no se puede cerrar (hay que elegir)
}

/** Elegir un color: los cuatro palos, cada uno con su forma, su nombre y su color. */
export function ColorPicker({ title, onPick, onCancel }: Props) {
  const titleId = useId();
  const first = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    first.current?.focus();
    if (!onCancel) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onPointerDown={(event) => {
        if (onCancel && event.target === event.currentTarget) onCancel();
      }}
    >
      <div role="dialog" aria-modal="true" aria-labelledby={titleId} className="panel pop-in w-full max-w-sm p-5">
        <h2 id={titleId} className="gold-text text-xl font-black">
          {title}
        </h2>
        <div className="mt-4 grid grid-cols-2 gap-3">
          {SUIT_ORDER.map((suit, index) => (
            <button
              key={suit}
              ref={index === 0 ? first : undefined}
              type="button"
              onClick={() => onPick(suit)}
              className="flex flex-col items-center gap-1.5 rounded-xl border-2 bg-black/40 p-3 font-bold outline-none hover:bg-white/10 focus-visible:ring-4 focus-visible:ring-amber-300"
              style={{ borderColor: SUITS[suit].color }}
            >
              <SuitSymbol suit={suit} className="h-10 w-10" />
              <span style={{ color: SUITS[suit].color }}>{SUITS[suit].name}</span>
              <span className="text-[11px] font-medium text-stone-400">{SUITS[suit].shape}</span>
            </button>
          ))}
        </div>
        {onCancel && (
          <button type="button" className="btn-dark mt-4 h-10 w-full text-sm" onClick={onCancel}>
            Cancelar
          </button>
        )}
      </div>
    </div>
  );
}
