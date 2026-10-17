// Fichas dibujadas con SVG propio.

const STACK_LEVELS = [17, 13, 9]; // de abajo arriba

/** Un montoncito de fichas visto de lado: lo que un jugador ha puesto en el bote. */
export function ChipStack({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={`shrink-0 ${className}`} aria-hidden>
      {STACK_LEVELS.map((y) => (
        <g key={y}>
          <path d={`M3 ${y}v3c0 2.2 4 4 9 4s9-1.8 9-4v-3z`} fill="#9f1239" />
          <ellipse cx="12" cy={y} rx="9" ry="4" fill="#f43f5e" stroke="#9f1239" strokeWidth="0.6" />
        </g>
      ))}
      <ellipse
        cx="12"
        cy={STACK_LEVELS[2]}
        rx="6"
        ry="2.5"
        fill="none"
        stroke="#fff1f2"
        strokeWidth="1.2"
        strokeDasharray="2.4 2.4"
      />
    </svg>
  );
}
