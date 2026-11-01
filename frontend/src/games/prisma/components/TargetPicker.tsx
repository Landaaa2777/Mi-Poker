import { useEffect, useId, useRef } from "react";
import { Avatar } from "../../../shared/components/Avatar";
import type { PlayerInfo } from "../types";

interface Props {
  rivals: PlayerInfo[]; // con quién me puedo cambiar la mano (los que siguen en la ronda)
  onPick: (seat: number) => void;
  onCancel: () => void;
}

/** Sin tregua, el 7: elegir con quién cambias la mano. Se ve cuántas cartas tiene cada uno. */
export function TargetPicker({ rivals, onPick, onCancel }: Props) {
  const titleId = useId();
  const first = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    first.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 p-4"
      onPointerDown={(event) => {
        if (event.target === event.currentTarget) onCancel();
      }}
    >
      <div role="dialog" aria-modal="true" aria-labelledby={titleId} className="panel pop-in w-full max-w-sm p-5">
        <h2 id={titleId} className="gold-text text-xl font-black">
          ¿Con quién cambias la mano?
        </h2>
        <p className="mt-1 text-sm text-stone-300">Te quedas con sus cartas y se lleva las tuyas.</p>
        <div className="mt-4 flex flex-col gap-2">
          {rivals.map((rival, index) => (
            <button
              key={rival.seat}
              ref={index === 0 ? first : undefined}
              type="button"
              onClick={() => onPick(rival.seat)}
              className="flex items-center gap-3 rounded-xl border-2 border-amber-400/30 bg-black/40 p-2.5 text-left font-bold outline-none hover:bg-white/10 focus-visible:ring-4 focus-visible:ring-amber-300"
            >
              <Avatar name={rival.name} size={36} ring="ring-white/25" />
              <span className="flex-1 truncate">{rival.name}</span>
              <span className="tabular-nums text-amber-300">
                {rival.count} {rival.count === 1 ? "carta" : "cartas"}
              </span>
            </button>
          ))}
        </div>
        <button type="button" className="btn-dark mt-4 h-10 w-full text-sm" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </div>
  );
}
