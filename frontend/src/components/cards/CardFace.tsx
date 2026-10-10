// La cara de una carta. La baraja es la clásica inglesa, con las figuras de
// siempre; los dibujos están en `src/assets/cards/` (ver su LEEME.md).

import { cardRank } from "../../format";
import { SuitShape, suitColor } from "./suits";

// Un SVG por carta, con nombres como "KH.svg" o "TS.svg". Vite resuelve la
// lista al compilar: si faltara algún archivo, esa carta usa la cara sencilla.
const files = import.meta.glob<string>("../../assets/cards/*.svg", {
  eager: true,
  query: "?url",
  import: "default",
});

const FACES = new Map(
  Object.entries(files).map(([path, url]) => [path.split("/").pop()!.replace(".svg", ""), url]),
);

function faceUrl(card: string): string | undefined {
  return FACES.get(card[0] + card[1].toUpperCase());
}

/** Descarga ya todas las caras, para que ninguna tarde en verse al repartirla. */
export function preloadFaces(): void {
  for (const url of FACES.values()) new Image().src = url;
}

/** Cara sencilla para cartas pequeñas: solo el valor y el palo, bien grandes. */
export function CompactFace({ card }: { card: string }) {
  return (
    <span
      className="compact-face flex h-full w-full flex-col items-center font-bold leading-none"
      style={{ color: suitColor(card[1]) }}
    >
      <span>{cardRank(card)}</span>
      <svg viewBox="0 0 24 24" className="h-[0.95em] w-[0.95em]" fill="currentColor" aria-hidden>
        <SuitShape suit={card[1]} />
      </svg>
    </span>
  );
}

/** Cara completa: el dibujo clásico de la carta, que llena todo su tamaño. */
export function CardFace({ card }: { card: string }) {
  const url = faceUrl(card);
  if (!url) return <CompactFace card={card} />;
  return <img src={url} alt="" draggable={false} className="block h-full w-full select-none" />;
}
