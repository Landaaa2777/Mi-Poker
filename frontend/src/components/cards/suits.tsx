// Los cuatro palos, para la cara sencilla de las cartas pequeñas. Trazos
// propios sobre una cuadrícula de 24 x 24.

// Los mismos colores que usa la baraja (ver tools/import_cards.mjs).
const RED = "#d5121e";
const BLACK = "#16151a";

export function suitColor(suit: string): string {
  return suit === "h" || suit === "d" ? RED : BLACK;
}

const HEART =
  "M12 20.5C5 15.5 2 12 2 8.5 2 5.5 4.3 3.5 7 3.5c2 0 3.8 1.1 5 3 1.2-1.9 3-3 5-3 2.7 0 5 2 5 5 0 3.5-3 7-10 12z";
const DIAMOND = "M12 2l8 10-8 10-8-10z";
const SPADE =
  "M12 2.5c7 5.5 10 8.5 10 12 0 2.8-2.1 4.5-4.5 4.5-1.7 0-3.3-.8-4.3-2.2.3 2.2 1.1 3.8 2.3 4.7h-7c1.2-.9 2-2.5 2.3-4.7C9.8 18.2 8.2 19 6.5 19 4.1 19 2 17.3 2 14.5c0-3.5 3-6.5 10-12z";

/** El dibujo del palo, tal cual, en su cuadrícula de 24 x 24. */
export function SuitShape({ suit }: { suit: string }) {
  if (suit === "h") return <path d={HEART} />;
  if (suit === "d") return <path d={DIAMOND} />;
  if (suit === "s") return <path d={SPADE} />;
  return (
    <>
      <circle cx="12" cy="7" r="4.6" />
      <circle cx="6.6" cy="14" r="4.6" />
      <circle cx="17.4" cy="14" r="4.6" />
      <path d="M12 11l-2.6 10.5h5.2z" />
    </>
  );
}
