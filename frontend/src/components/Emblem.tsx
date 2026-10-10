// Identidad visual propia de mi-poker: una ficha con una pica en el centro.

interface Props {
  className?: string;
}

/** Emblema: ficha con muescas y una pica. Toma el color del texto que lo rodea. */
export function Emblem({ className = "" }: Props) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <circle cx="32" cy="32" r="30" fill="none" stroke="currentColor" strokeWidth="3" />
      <circle
        cx="32"
        cy="32"
        r="24.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="5"
        strokeDasharray="7.7 11.54"
        opacity="0.55"
      />
      <path
        fill="currentColor"
        transform="translate(18 17) scale(1.17)"
        d="M12 2.5c7 5.5 10 8.5 10 12 0 2.8-2.1 4.5-4.5 4.5-1.7 0-3.3-.8-4.3-2.2.3 2.2 1.1 3.8 2.3 4.7h-7c1.2-.9 2-2.5 2.3-4.7C9.8 18.2 8.2 19 6.5 19 4.1 19 2 17.3 2 14.5c0-3.5 3-6.5 10-12z"
      />
    </svg>
  );
}

/** Emblema con el nombre del juego al lado. */
export function Wordmark({ className = "" }: Props) {
  return (
    <span className={`inline-flex items-center gap-2 font-black tracking-tight ${className}`}>
      <Emblem className="h-[1.25em] w-[1.25em] text-amber-300" />
      <span className="gold-text">mi-poker</span>
    </span>
  );
}
