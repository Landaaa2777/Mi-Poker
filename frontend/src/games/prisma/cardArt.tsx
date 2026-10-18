// Las cartas de Prisma, dibujadas por código en SVG con un diseño propio:
// marco claro, campo del color del palo con una banda diagonal, la forma del
// palo de fondo y el número en tipografía recta. Las acciones llevan símbolos
// propios (dos barras, una espiral, "+2") y los comodines, los cuatro palos.
// El reverso es oscuro, con un prisma que abre la luz en los cuatro colores.

import { useId } from "react";
import { SUIT_ORDER, SUITS, SuitPath } from "./shapes";
import type { Card } from "./types";

const KIND_NAMES: Record<string, string> = {
  pausa: "Pausa",
  remolino: "Remolino",
  carga: "Carga +2",
  camaleon: "Camaleón",
  camaleon4: "Camaleón +4",
};

/** El nombre de una carta, para leerlo: "Panal 7", "Halo Pausa", "Camaleón +4". */
export function cardName(card: Card): string {
  if (card.color === null) return KIND_NAMES[card.kind];
  const detail = card.kind === "number" ? String(card.number) : KIND_NAMES[card.kind];
  return `${SUITS[card.color].name} ${detail}`;
}

const INK = "#fffaf0";
const SHADOW = "rgb(0 0 0 / 0.38)";

/** Símbolo central de cada acción, en una caja de 100 × 140. */
function ActionSymbol({ kind, size }: { kind: Card["kind"]; size: number }) {
  if (kind === "pausa") {
    // Dos barras gruesas: el siguiente se queda quieto.
    return (
      <g fill={INK} stroke={SHADOW} strokeWidth={1.5} paintOrder="stroke">
        <rect x={50 - size * 0.36} y={70 - size * 0.48} width={size * 0.26} height={size * 0.96} rx={size * 0.1} />
        <rect x={50 + size * 0.1} y={70 - size * 0.48} width={size * 0.26} height={size * 0.96} rx={size * 0.1} />
      </g>
    );
  }
  if (kind === "remolino") {
    // Una espiral que gira: el juego cambia de sentido.
    const s = size / 40;
    return (
      <path
        d="M50 70 m0 -4 a4 4 0 1 1 -4 4 a8 8 0 0 1 8 -8 a12 12 0 0 1 12 12 a16 16 0 0 1 -16 16 a20 20 0 0 1 -20 -20 a24 24 0 0 1 24 -24"
        transform={`translate(${50 - 50 * s} ${70 - 70 * s}) scale(${s})`}
        fill="none"
        stroke={INK}
        strokeWidth={6 / s}
        strokeLinecap="round"
      />
    );
  }
  // Carga +2.
  return (
    <text
      x={50}
      y={70 + size * 0.2}
      textAnchor="middle"
      fontSize={size * 0.62}
      fontWeight={900}
      fill={INK}
      stroke={SHADOW}
      strokeWidth={1.5}
      paintOrder="stroke"
      style={{ fontFamily: "var(--font-numbers)" }}
    >
      +2
    </text>
  );
}

/** Lo que va en las esquinas: el número o un símbolo pequeño. */
function cornerLabel(card: Card): string {
  if (card.kind === "number") return String(card.number);
  if (card.kind === "carga") return "+2";
  if (card.kind === "camaleon4") return "+4";
  return "";
}

function Corner({ card, flip }: { card: Card; flip?: boolean }) {
  const label = cornerLabel(card);
  const underline = card.kind === "number" && (card.number === 6 || card.number === 9);
  return (
    <g transform={flip ? "rotate(180 50 70)" : undefined}>
      {label && (
        <text x={14} y={25} textAnchor="middle" fontSize={17} fontWeight={900} fill={INK} style={{ fontFamily: "var(--font-numbers)" }}>
          {label}
        </text>
      )}
      {underline && <rect x={8} y={28} width={12} height={2.2} rx={1} fill={INK} />}
      {card.kind === "pausa" && (
        <g fill={INK}>
          <rect x={8} y={12} width={4} height={13} rx={1.5} />
          <rect x={15} y={12} width={4} height={13} rx={1.5} />
        </g>
      )}
      {card.kind === "remolino" && (
        <path d="M14 18 m0 -1.5 a1.5 1.5 0 1 1 -1.5 1.5 a3 3 0 0 1 3 -3 a4.5 4.5 0 0 1 4.5 4.5 a6 6 0 0 1 -6 6" fill="none" stroke={INK} strokeWidth={2.2} strokeLinecap="round" />
      )}
      {card.color && (
        <g transform="translate(8.5 31) scale(0.46)">
          <SuitPath suit={card.color} fill={INK} />
        </g>
      )}
    </g>
  );
}

/** Cara de una carta de color (número o acción). */
function ColorFace({ card }: { card: Card }) {
  const suit = card.color!;
  const pattern = useId();
  return (
    <>
      <rect x={6} y={6} width={88} height={128} rx={7} fill={SUITS[suit].color} />
      {/* Textura: la forma del palo repetida, muy suave. */}
      <defs>
        <pattern id={pattern} width={22} height={22} patternUnits="userSpaceOnUse">
          <g transform="translate(5 5) scale(0.5)" opacity={0.13}>
            <SuitPath suit={suit} fill="#000" />
          </g>
        </pattern>
      </defs>
      <rect x={6} y={6} width={88} height={128} rx={7} fill={`url(#${pattern})`} />
      {/* Banda diagonal de luz, como un rayo que atraviesa un prisma. */}
      <path d="M6 104 L94 30 L94 54 L6 128 Z" fill="#fff" opacity={0.16} />
      {/* La forma del palo, grande, detrás del número. */}
      <g transform="translate(18 38) scale(2.66)" opacity={0.3}>
        <SuitPath suit={suit} fill="#fff" />
      </g>
      {card.kind === "number" ? (
        <>
          <text
            x={50}
            y={87}
            textAnchor="middle"
            fontSize={50}
            fontWeight={900}
            fill={INK}
            stroke={SHADOW}
            strokeWidth={2}
            paintOrder="stroke"
            style={{ fontFamily: "var(--font-numbers)" }}
          >
            {card.number}
          </text>
          {(card.number === 6 || card.number === 9) && <rect x={38} y={92} width={24} height={3.5} rx={1.6} fill={INK} />}
        </>
      ) : (
        <ActionSymbol kind={card.kind} size={44} />
      )}
      <Corner card={card} />
      <Corner card={card} flip />
    </>
  );
}

/** Cara de un comodín: los cuatro palos, cada uno con su forma y su color. */
function WildFace({ card }: { card: Card }) {
  const spots = [
    [30, 42],
    [52, 42],
    [30, 66],
    [52, 66],
  ];
  return (
    <>
      <rect x={6} y={6} width={88} height={128} rx={7} style={{ fill: "var(--color-prisma-back)" }} />
      <path d="M6 104 L94 30 L94 54 L6 128 Z" fill="#fff" opacity={0.07} />
      {SUIT_ORDER.map((suit, index) => (
        <g key={suit} transform={`translate(${spots[index][0] - 2} ${spots[index][1] - 2}) scale(0.95)`}>
          <SuitPath suit={suit} fill={SUITS[suit].color} />
        </g>
      ))}
      {card.kind === "camaleon4" && (
        <text
          x={50}
          y={118}
          textAnchor="middle"
          fontSize={22}
          fontWeight={900}
          fill={INK}
          style={{ fontFamily: "var(--font-numbers)" }}
        >
          +4
        </text>
      )}
      <Corner card={card} />
      <Corner card={card} flip />
    </>
  );
}

/** Dibujo completo de la cara de una carta (caja de 100 × 140). */
export function CardFaceArt({ card }: { card: Card }) {
  return (
    <svg viewBox="0 0 100 140" className="block h-full w-full" role="img" aria-label={cardName(card)}>
      <rect x={0} y={0} width={100} height={140} rx={10} fill="#fdfaf3" />
      {card.color === null ? <WildFace card={card} /> : <ColorFace card={card} />}
    </svg>
  );
}

/** El reverso: un prisma que abre un rayo de luz en los cuatro colores de los palos. */
export function CardBackArt() {
  const rays = SUIT_ORDER.map((suit) => SUITS[suit].color);
  return (
    <svg viewBox="0 0 100 140" className="block h-full w-full" aria-hidden>
      <rect x={0} y={0} width={100} height={140} rx={10} fill="#fdfaf3" />
      <rect x={6} y={6} width={88} height={128} rx={7} style={{ fill: "var(--color-prisma-back)" }} />
      <rect x={11} y={11} width={78} height={118} rx={5} fill="none" stroke="#fff" strokeOpacity={0.18} strokeWidth={1.2} />
      {/* El rayo blanco que entra… */}
      <path d="M12 82 L40 74" stroke="#fff" strokeOpacity={0.85} strokeWidth={2.4} strokeLinecap="round" />
      {/* …el prisma… */}
      <path d="M50 46 L66 86 L34 86 Z" fill="#fff" fillOpacity={0.08} stroke="#fff" strokeOpacity={0.7} strokeWidth={2} strokeLinejoin="round" />
      {/* …y los cuatro colores que salen. */}
      {rays.map((color, index) => (
        <path
          key={color}
          d={`M58 ${74 + index * 2} L88 ${70 + index * 7}`}
          stroke={color}
          strokeWidth={3}
          strokeLinecap="round"
        />
      ))}
    </svg>
  );
}
