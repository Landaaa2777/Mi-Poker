import { useEffect, useRef } from "react";
import { describeEvent } from "../describe";
import type { Frame } from "../timeline";

/** Registro de la ronda: lo que ha pasado hasta lo que se ve ahora en la mesa. */
export function RoundLog({ frame, me }: { frame: Frame; me: number }) {
  const list = useRef<HTMLOListElement>(null);
  const lines = frame.events
    .map((event, index) => ({ event, text: describeEvent(index, frame, me) }))
    .filter((line): line is { event: (typeof frame.events)[number]; text: string } => line.text !== null);

  // La última línea siempre a la vista, moviendo solo la lista (no la página).
  useEffect(() => {
    if (list.current) list.current.scrollTop = list.current.scrollHeight;
  }, [lines.length]);

  return (
    <section className="panel flex min-h-48 flex-col overflow-hidden">
      <h2 className="border-b border-amber-400/20 px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] text-amber-200/85">
        Registro
      </h2>
      <ol ref={list} className="quiet-scroll max-h-56 flex-1 space-y-0.5 overflow-y-auto px-4 py-2 text-sm">
        {lines.map(({ event, text }, index) => (
          <li
            key={index}
            className={
              event.kind === "settle"
                ? "font-semibold text-amber-200"
                : event.seat === me
                  ? "text-stone-100"
                  : "text-stone-300"
            }
          >
            {text}
          </li>
        ))}
      </ol>
    </section>
  );
}
