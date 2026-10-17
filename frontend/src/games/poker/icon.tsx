// Ícono del poker para el menú: dos cartas abiertas en abanico, con una pica y
// una ficha delante. Dibujado por código.

interface Props {
  className?: string;
}

const SPADE =
  "M12 2.5c7 5.5 10 8.5 10 12 0 2.8-2.1 4.5-4.5 4.5-1.7 0-3.3-.8-4.3-2.2.3 2.2 1.1 3.8 2.3 4.7h-7c1.2-.9 2-2.5 2.3-4.7C9.8 18.2 8.2 19 6.5 19 4.1 19 2 17.3 2 14.5c0-3.5 3-6.5 10-12z";

export function PokerIcon({ className = "" }: Props) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <rect x="12" y="10" width="26" height="38" rx="4" fill="none" stroke="currentColor" strokeWidth="3" opacity="0.6" transform="rotate(-14 25 29)" />
      <rect x="24" y="8" width="26" height="38" rx="4" fill="currentColor" opacity="0.18" stroke="currentColor" strokeWidth="3" transform="rotate(8 37 27)" />
      <path d={SPADE} fill="currentColor" transform="translate(28 15) scale(0.75) rotate(8 12 12)" />
      <circle cx="46" cy="48" r="10" fill="none" stroke="currentColor" strokeWidth="3" />
      <circle cx="46" cy="48" r="6" fill="none" stroke="currentColor" strokeWidth="2.6" strokeDasharray="3.4 2.9" />
    </svg>
  );
}
