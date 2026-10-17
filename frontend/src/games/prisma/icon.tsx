// Ícono de Prisma para el menú: sus cuatro palos, cada uno con su forma y su color.

import { SUIT_ORDER, SUITS, SuitPath } from "./shapes";

const SPOTS = [
  [6, 6],
  [34, 6],
  [6, 34],
  [34, 34],
];

export function PrismaIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      {SUIT_ORDER.map((suit, index) => (
        <g key={suit} transform={`translate(${SPOTS[index][0]} ${SPOTS[index][1]})`}>
          <SuitPath suit={suit} fill={SUITS[suit].color} />
        </g>
      ))}
    </svg>
  );
}
