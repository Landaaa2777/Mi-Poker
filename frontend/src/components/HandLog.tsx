import { useEffect, useRef } from "react";
import { describeEvent } from "../format";
import type { GameState } from "../types";

/** Registro de la mano en curso. Solo contiene sucesos públicos. */
export function HandLog({ state }: { state: GameState }) {
  const end = useRef<HTMLLIElement>(null);
  useEffect(() => {
    const list = end.current?.parentElement;
    if (list) list.scrollTop = list.scrollHeight;
  }, [state.events.length]);

  return (
    <section className="rounded-lg bg-slate-800 p-4">
      <h2 className="mb-2 text-sm font-semibold text-slate-300">Registro de la mano</h2>
      <ol className="max-h-64 space-y-0.5 overflow-y-auto text-sm">
        {state.events.map((event, index) => (
          <li key={index} className={event.kind === "board" ? "text-sky-300" : ""}>
            {describeEvent(event, state)}
          </li>
        ))}
        <li ref={end} />
      </ol>
    </section>
  );
}
