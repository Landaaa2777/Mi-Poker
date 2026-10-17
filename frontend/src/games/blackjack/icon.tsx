// Ícono del blackjack para el menú: dos cartas con el 21 delante. Dibujado por código.

export function BlackjackIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <rect x="9" y="12" width="28" height="40" rx="4" fill="none" stroke="currentColor" strokeWidth="3" opacity="0.6" transform="rotate(-10 23 32)" />
      <rect x="25" y="9" width="30" height="42" rx="4" fill="currentColor" opacity="0.18" stroke="currentColor" strokeWidth="3" transform="rotate(6 40 30)" />
      <text
        x="40"
        y="37"
        textAnchor="middle"
        fontSize="20"
        fontWeight="900"
        fill="currentColor"
        transform="rotate(6 40 30)"
        fontFamily="ui-rounded, 'Segoe UI', system-ui, sans-serif"
      >
        21
      </text>
    </svg>
  );
}
