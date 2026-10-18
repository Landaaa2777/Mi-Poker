import type { CSSProperties } from "react";
import { PlayingCard } from "../../shared/cards/PlayingCard";
import { CodeTiles } from "./CodeTiles";

interface Props {
  phase: "searching" | "found";
  code: string;
  detail?: string; // "Poker Hold'em · sala de Ana"
}

/**
 * Entrar en una sala: primero "Buscando la sala…" (ondas y un abanico de
 * cartas que se mece) y, al encontrarla, "¡Partida encontrada!" con un
 * destello dorado y las letras del código volteándose una a una. Solo se
 * mueven `transform` y `opacity`; sin animaciones, todo se ve quieto.
 */
export function FoundAnimation({ phase, code, detail }: Props) {
  return (
    <section
      className="felt rim relative flex min-h-[22rem] flex-col items-center justify-center gap-6 overflow-hidden rounded-[1.75rem] px-4 py-10 text-center"
      aria-live="polite"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_45%,rgb(0_0_0/0.4))]" />
      {phase === "searching" ? (
        <>
          <div className="relative flex h-44 w-44 items-center justify-center">
            {[0, 1, 2].map((ring) => (
              <span
                key={ring}
                className="sala-ping absolute inset-0 rounded-full border-2 border-amber-300/55 opacity-0"
                style={{ animationDelay: `${ring * 0.6}s` }}
              />
            ))}
            <div className="relative flex" style={{ "--card-w": "56px" } as CSSProperties}>
              {[-1, 0, 1].map((side) => (
                <span
                  key={side}
                  className="sala-fan"
                  style={
                    {
                      transform: `rotate(${side * 14}deg)`,
                      "--swing": `${side * 14 + 7}deg`,
                      marginLeft: side === -1 ? 0 : -30,
                      animationDelay: `${(side + 1) * 0.18}s`,
                    } as CSSProperties
                  }
                >
                  <PlayingCard card={null} />
                </span>
              ))}
            </div>
          </div>
          <div className="relative flex flex-col items-center gap-4">
            <h1 className="gold-text font-display text-3xl font-black sm:text-4xl">Buscando la sala…</h1>
            <CodeTiles code={code} />
          </div>
        </>
      ) : (
        <>
          <span className="sala-burst pointer-events-none absolute h-72 w-72 rounded-full bg-[radial-gradient(closest-side,rgb(245_197_66/0.55),transparent)] opacity-0" />
          <div className="relative flex flex-col items-center gap-5">
            <CodeTiles code={code} reveal />
            <h1 className="found-title gold-text font-display text-4xl font-black sm:text-5xl">¡Partida encontrada!</h1>
            {detail && <p className="found-title text-emerald-50/85">{detail}</p>}
          </div>
        </>
      )}
    </section>
  );
}
