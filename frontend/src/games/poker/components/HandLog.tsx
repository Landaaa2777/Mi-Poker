import { useEffect, useRef } from "react";
import { describeEvent, isOpeningBet } from "../format";
import type { Frame } from "../timeline/frame";

const LINE_STYLE: Record<string, string> = {
  board: "text-emerald-300",
  win: "font-bold text-amber-300",
  show: "text-stone-50",
};

/** Registro de la mano: solo lo que ya se ha visto en la mesa. */
export function HandLog({ frame }: { frame: Frame }) {
  const list = useRef<HTMLOListElement>(null);
  useEffect(() => {
    if (list.current) list.current.scrollTop = list.current.scrollHeight;
  }, [frame.events.length]);

  // Tus jugadas se cuentan en segunda persona: sin nombre.
  const name = (seat: number | null) => {
    const actor = frame.seats.find((candidate) => candidate.seat === seat);
    return actor === undefined || actor.isHuman ? null : actor.name;
  };

  return (
    <section className="panel flex h-48 flex-col overflow-hidden lg:order-1">
      <h2 className="self-start rounded-br-lg border-b border-r border-amber-400/30 bg-black/40 px-4 py-1.5 text-xs font-extrabold uppercase tracking-[0.18em]">
        <span className="gold-text">Registro</span>
      </h2>
      <ol
        ref={list}
        data-zone="log"
        className="quiet-scroll min-h-0 flex-1 space-y-0.5 overflow-y-auto px-4 py-2 text-sm text-stone-300"
      >
        {frame.events.map((event, index) => (
          <li key={index} className={LINE_STYLE[event.kind] ?? ""}>
            {describeEvent(event, name(event.seat), isOpeningBet(frame.events, index))}
          </li>
        ))}
      </ol>
    </section>
  );
}
