// Las cartas de Prisma, dibujadas por código en SVG con un diseño propio:
// marco claro, campo del color del palo con una banda diagonal, la forma del
// palo de fondo y el número en tipografía recta. Las acciones llevan símbolos
// propios (dos barras, una espiral, "+2", un disco a medias…) y los comodines,
// los cuatro palos. Las cartas de la cara de sombra (Doble cara) son negras:
// marco oscuro y sus propios palos. El reverso es oscuro, con un prisma que
// abre la luz en los cuatro colores.

import { useId } from "react";
import { DARK_ORDER, isDark, SUIT_ORDER, SUITS, SuitPath } from "./shapes";
import type { Card, Face, Kind } from "./types";

export const KIND_NAMES: Record<Exclude<Kind, "number">, string> = {
  pausa: "Pausa",
  remolino: "Remolino",
  carga: "Carga +2",
  camaleon: "Camaleón",
  camaleon4: "Camaleón +4",
  carga1: "Carga +1",
  carga5: "Carga +5",
  eclipse: "Eclipse",
  pausa_total: "Pausa total",
  camaleon2: "Camaleón +2",
  sabueso: "Camaleón Sabueso",
  carga4: "Carga +4",
  barrido: "Barrido",
  camaleon_remolino4: "Camaleón Remolino +4",
  camaleon6: "Camaleón +6",
  camaleon10: "Camaleón +10",
  ruleta: "Camaleón Ruleta",
};

/** El nombre de una carta, para leerlo: "Panal 7", "Halo Pausa", "Camaleón +4". */
export function cardName(card: Card | Face): string {
  if (card.kind === "number" || card.color !== null) {
    const detail = card.kind === "number" ? String(card.number) : KIND_NAMES[card.kind];
    return card.color ? `${SUITS[card.color].name} ${detail}` : detail;
  }
  return KIND_NAMES[card.kind];
}

const INK = "#fffaf0";
const SHADOW = "rgb(0 0 0 / 0.38)";
const PAPER = "#fdfaf3"; // marco de las cartas de la cara de luz
const NIGHT = "var(--color-prisma-night)"; // marco de las de la cara de sombra

// Lo que suman o hacen robar, para escribirlo en la carta.
const PLUS: Partial<Record<Kind, string>> = {
  carga: "+2",
  carga1: "+1",
  carga4: "+4",
  carga5: "+5",
  camaleon2: "+2",
  camaleon4: "+4",
  camaleon6: "+6",
  camaleon10: "+10",
  camaleon_remolino4: "+4",
};

// Los comodines que, en vez de los cuatro palos en cuadro, llevan un símbolo.
const SPECIAL_WILDS = new Set<Kind>(["sabueso", "ruleta", "camaleon_remolino4"]);

/**
 * El símbolo de una acción, centrado en (`x`, `y`) con tamaño `size`, en la caja
 * de 100 × 140 de la carta. Sirve igual para el centro (grande) y las esquinas.
 */
function Glyph({ kind, x, y, size, stroke = true, field }: { kind: Kind; x: number; y: number; size: number; stroke?: boolean; field?: string }) {
  const s = size / 40;
  const outline = stroke ? { stroke: SHADOW, strokeWidth: 1.5, paintOrder: "stroke" as const } : {};
  switch (kind) {
    case "pausa":
      // Dos barras gruesas: el siguiente se queda quieto.
      return (
        <g fill={INK} {...outline}>
          <rect x={x - size * 0.36} y={y - size * 0.48} width={size * 0.26} height={size * 0.96} rx={size * 0.1} />
          <rect x={x + size * 0.1} y={y - size * 0.48} width={size * 0.26} height={size * 0.96} rx={size * 0.1} />
        </g>
      );
    case "pausa_total":
      // Las dos barras dentro de un anillo: se quedan quietos todos.
      return (
        <g {...outline}>
          <circle cx={x} cy={y} r={size * 0.56} fill="none" stroke={INK} strokeWidth={size * 0.1} />
          <rect x={x - size * 0.24} y={y - size * 0.3} width={size * 0.16} height={size * 0.6} rx={size * 0.06} fill={INK} />
          <rect x={x + size * 0.08} y={y - size * 0.3} width={size * 0.16} height={size * 0.6} rx={size * 0.06} fill={INK} />
        </g>
      );
    case "remolino":
    case "camaleon_remolino4":
      // Una espiral que gira: el juego cambia de sentido.
      return (
        <path
          d="M50 70 m0 -4 a4 4 0 1 1 -4 4 a8 8 0 0 1 8 -8 a12 12 0 0 1 12 12 a16 16 0 0 1 -16 16 a20 20 0 0 1 -20 -20 a24 24 0 0 1 24 -24"
          transform={`translate(${x - 50 * s} ${y - 70 * s}) scale(${s})`}
          fill="none"
          stroke={INK}
          strokeWidth={5.6} /* con la escala, un trazo proporcional al tamaño */
          strokeLinecap="round"
        />
      );
    case "eclipse":
      // Un disco mitad luz y mitad sombra: la mesa da la vuelta.
      return (
        <g {...outline}>
          <circle cx={x} cy={y} r={size * 0.5} fill={field ?? SHADOW} stroke={INK} strokeWidth={size * 0.09} />
          <path d={`M${x} ${y - size * 0.5} a${size * 0.5} ${size * 0.5} 0 0 1 0 ${size} z`} fill={INK} />
          <circle cx={x} cy={y} r={size * 0.16} fill={INK} />
          <path d={`M${x} ${y - size * 0.16} a${size * 0.16} ${size * 0.16} 0 0 1 0 ${size * 0.32} z`} fill={field ?? "#000"} />
        </g>
      );
    case "barrido":
      // Tres trazos que barren hacia un lado: se va todo el color.
      return (
        <g fill="none" stroke={INK} strokeWidth={size * 0.13} strokeLinecap="round">
          {[-0.34, 0, 0.34].map((dy, index) => (
            <path
              key={dy}
              d={`M${x - size * (0.5 - index * 0.12)} ${y + size * dy + size * 0.12} Q${x} ${y + size * dy - size * 0.16} ${x + size * 0.52} ${y + size * dy}`}
            />
          ))}
        </g>
      );
    case "sabueso":
      // Una huella: el siguiente rastrea el mazo hasta dar con el color.
      return (
        <g fill={INK} {...outline}>
          <ellipse cx={x} cy={y + size * 0.14} rx={size * 0.3} ry={size * 0.25} />
          {[
            [-0.34, -0.2],
            [-0.12, -0.42],
            [0.12, -0.42],
            [0.34, -0.2],
          ].map(([dx, dy]) => (
            <ellipse key={`${dx}${dy}`} cx={x + size * dx} cy={y + size * dy} rx={size * 0.1} ry={size * 0.13} />
          ))}
        </g>
      );
    case "ruleta":
      // Una rueda con los cuatro colores: sale lo que salga.
      return (
        <g>
          <circle cx={x} cy={y} r={size * 0.56} fill="none" stroke={INK} strokeWidth={size * 0.08} />
          {Array.from({ length: 8 }, (_, index) => {
            const from = (index * Math.PI) / 4;
            const to = ((index + 1) * Math.PI) / 4;
            const r = size * 0.48;
            return (
              <path
                key={index}
                d={`M${x} ${y} L${x + r * Math.cos(from)} ${y + r * Math.sin(from)} A${r} ${r} 0 0 1 ${x + r * Math.cos(to)} ${y + r * Math.sin(to)} z`}
                style={{ fill: SUITS[SUIT_ORDER[index % 4]].color }}
              />
            );
          })}
          <circle cx={x} cy={y} r={size * 0.12} fill={INK} />
        </g>
      );
    default: {
      // Las cargas: "+2", "+5"…
      const text = PLUS[kind] ?? "";
      return (
        <text
          x={x}
          y={y + size * 0.2}
          textAnchor="middle"
          fontSize={size * (text.length > 2 ? 0.5 : 0.62)}
          fontWeight={900}
          fill={INK}
          {...outline}
          style={{ fontFamily: "var(--font-numbers)" }}
        >
          {text}
        </text>
      );
    }
  }
}

/** Lo que va en las esquinas: el número o un símbolo pequeño. */
function Corner({ card, flip }: { card: Card | Face; flip?: boolean }) {
  const label = card.kind === "number" ? String(card.number) : (PLUS[card.kind] ?? "");
  const underline = card.kind === "number" && (card.number === 6 || card.number === 9);
  return (
    <g transform={flip ? "rotate(180 50 70)" : undefined}>
      {label ? (
        <text
          x={14}
          y={25}
          textAnchor="middle"
          fontSize={label.length > 2 ? 12.5 : 17}
          fontWeight={900}
          fill={INK}
          style={{ fontFamily: "var(--font-numbers)" }}
        >
          {label}
        </text>
      ) : (
        card.kind !== "camaleon" && <Glyph kind={card.kind} x={14} y={19} size={12} stroke={false} />
      )}
      {underline && <rect x={8} y={28} width={12} height={2.2} rx={1} fill={INK} />}
      {card.color && (
        <g transform="translate(8.5 31) scale(0.46)">
          <SuitPath suit={card.color} fill={INK} />
        </g>
      )}
    </g>
  );
}

/** Cara de una carta de color (número o acción). */
function ColorFace({ card }: { card: Card | Face }) {
  const suit = card.color!;
  const pattern = useId();
  return (
    <>
      <rect x={6} y={6} width={88} height={128} rx={7} style={{ fill: SUITS[suit].color }} />
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
      <path d="M6 104 L94 30 L94 54 L6 128 Z" fill="#fff" opacity={isDark(suit) ? 0.1 : 0.16} />
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
        <Glyph kind={card.kind} x={50} y={70} size={44} field={SUITS[suit].color} />
      )}
      <Corner card={card} />
      <Corner card={card} flip />
    </>
  );
}

/** Cara de un comodín: los cuatro palos de su cara, cada uno con su forma y su color. */
function WildFace({ card, dark }: { card: Card | Face; dark: boolean }) {
  const suits = dark ? DARK_ORDER : SUIT_ORDER;
  const plus = PLUS[card.kind];
  const special = SPECIAL_WILDS.has(card.kind);
  const spots = [
    [30, 42],
    [52, 42],
    [30, 66],
    [52, 66],
  ];
  return (
    <>
      <rect x={6} y={6} width={88} height={128} rx={7} style={{ fill: dark ? "#07050a" : "var(--color-prisma-back)" }} />
      <path d="M6 104 L94 30 L94 54 L6 128 Z" fill="#fff" opacity={0.07} />
      {special ? (
        <>
          <Glyph kind={card.kind} x={50} y={62} size={46} />
          {/* Los cuatro palos, en fila, debajo del símbolo. */}
          {suits.map((suit, index) => (
            <g key={suit} transform={`translate(${26 + index * 13} 92) scale(0.46)`}>
              <SuitPath suit={suit} fill={SUITS[suit].color} />
            </g>
          ))}
        </>
      ) : (
        suits.map((suit, index) => (
          <g key={suit} transform={`translate(${spots[index][0] - 2} ${spots[index][1] - 2}) scale(0.95)`}>
            <SuitPath suit={suit} fill={SUITS[suit].color} />
          </g>
        ))
      )}
      {plus && (
        <text
          x={50}
          y={special ? 124 : 118}
          textAnchor="middle"
          fontSize={plus.length > 2 ? 19 : 22}
          fontWeight={900}
          fill={INK}
          style={{ fontFamily: "var(--font-numbers)" }}
        >
          {plus}
        </text>
      )}
      <Corner card={card} />
      <Corner card={card} flip />
    </>
  );
}

/**
 * Dibujo completo de la cara de una carta (caja de 100 × 140). `dark` dice si es
 * de la cara de sombra cuando el palo no lo dice (los comodines de Doble cara).
 */
export function CardFaceArt({ card, dark = false }: { card: Card | Face; dark?: boolean }) {
  const night = card.color !== null ? isDark(card.color) : card.kind === "sabueso" || dark;
  return (
    <svg viewBox="0 0 100 140" className="block h-full w-full" role="img" aria-label={cardName(card)}>
      <rect x={0} y={0} width={100} height={140} rx={10} style={{ fill: night ? NIGHT : PAPER }} />
      {night && <rect x={2.5} y={2.5} width={95} height={135} rx={8.5} fill="none" stroke="#d6b25e" strokeOpacity={0.45} strokeWidth={1} />}
      {card.color === null ? <WildFace card={card} dark={night} /> : <ColorFace card={card} />}
    </svg>
  );
}

/** El reverso: un prisma que abre un rayo de luz en los cuatro colores de los palos. */
export function CardBackArt() {
  const rays = SUIT_ORDER.map((suit) => SUITS[suit].color);
  return (
    <svg viewBox="0 0 100 140" className="block h-full w-full" aria-hidden>
      <rect x={0} y={0} width={100} height={140} rx={10} fill={PAPER} />
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
          style={{ stroke: color }}
          strokeWidth={3}
          strokeLinecap="round"
        />
      ))}
    </svg>
  );
}
