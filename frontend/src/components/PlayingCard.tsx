import { cardLabel, cardRank } from "../format";

interface Props {
  card: string | null; // null = boca abajo
}

/** Palo dibujado como SVG propio, para que se vea igual en cualquier sistema. */
function Suit({ suit }: { suit: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-[0.95em] w-[0.95em]" fill="currentColor" aria-hidden>
      {suit === "h" && (
        <path d="M12 20.5C5 15.5 2 12 2 8.5 2 5.5 4.3 3.5 7 3.5c2 0 3.8 1.1 5 3 1.2-1.9 3-3 5-3 2.7 0 5 2 5 5 0 3.5-3 7-10 12z" />
      )}
      {suit === "d" && <path d="M12 2l8 10-8 10-8-10z" />}
      {suit === "s" && (
        <path d="M12 2.5c7 5.5 10 8.5 10 12 0 2.8-2.1 4.5-4.5 4.5-1.7 0-3.3-.8-4.3-2.2.3 2.2 1.1 3.8 2.3 4.7h-7c1.2-.9 2-2.5 2.3-4.7C9.8 18.2 8.2 19 6.5 19 4.1 19 2 17.3 2 14.5c0-3.5 3-6.5 10-12z" />
      )}
      {suit === "c" && (
        <>
          <circle cx="12" cy="7" r="4.6" />
          <circle cx="6.6" cy="14" r="4.6" />
          <circle cx="17.4" cy="14" r="4.6" />
          <path d="M12 11l-2.6 10.5h5.2z" />
        </>
      )}
    </svg>
  );
}

/**
 * Una carta. Su tamaño lo fija quien la contiene con la variable CSS
 * `--card-w` (el ancho); el alto, las esquinas y la letra salen de ahí.
 */
export function PlayingCard({ card }: Props) {
  if (card === null) {
    return <span className="card card-back inline-block" aria-label="Carta boca abajo" />;
  }
  const red = card[1] === "h" || card[1] === "d";
  return (
    <span
      className={`card card-face inline-flex select-none flex-col items-center bg-white font-bold leading-none ${red ? "text-red-600" : "text-slate-900"}`}
      aria-label={cardLabel(card)}
    >
      <span>{cardRank(card)}</span>
      <Suit suit={card[1]} />
    </span>
  );
}
