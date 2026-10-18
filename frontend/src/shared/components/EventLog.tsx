import { useEffect, useRef } from "react";

export interface LogLine {
  text: string;
  tone?: "mine" | "others" | "highlight" | "note"; // cómo se destaca
}

const TONES: Record<NonNullable<LogLine["tone"]>, string> = {
  mine: "text-stone-100",
  others: "text-stone-300",
  highlight: "font-semibold text-amber-200",
  note: "text-emerald-200/80",
};

/** Registro de lo que ha pasado en la mano o ronda, con la última línea siempre a la vista. */
export function EventLog({ lines }: { lines: LogLine[] }) {
  const list = useRef<HTMLOListElement>(null);

  // Se mueve solo la lista, nunca la página.
  useEffect(() => {
    if (list.current) list.current.scrollTop = list.current.scrollHeight;
  }, [lines.length]);

  return (
    <section className="panel flex min-h-48 flex-col overflow-hidden">
      <h2 className="border-b border-amber-400/20 px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] text-amber-200/85">
        Registro
      </h2>
      <ol ref={list} className="quiet-scroll max-h-56 flex-1 space-y-0.5 overflow-y-auto px-4 py-2 text-sm">
        {lines.map((line, index) => (
          <li key={index} className={TONES[line.tone ?? "others"]}>
            {line.text}
          </li>
        ))}
      </ol>
    </section>
  );
}
