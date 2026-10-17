// Íconos del menú para lo que todavía no tiene página propia ("Próximamente").
// Los de cada juego viven con su juego (games/<juego>/icon.tsx). Todos son SVG
// dibujados por código, con diseño propio.

export interface IconProps {
  className?: string;
}

/** Minijuegos: un dado con una chispa. */
export function MinigamesIcon({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <rect x="10" y="16" width="34" height="34" rx="8" fill="none" stroke="currentColor" strokeWidth="3.5" transform="rotate(-10 27 33)" />
      {[
        [20, 26],
        [27, 33],
        [34, 40],
        [34, 26],
        [20, 40],
      ].map(([x, y]) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r="3" fill="currentColor" transform="rotate(-10 27 33)" />
      ))}
      <path d="M50 8l2.6 6.4L59 17l-6.4 2.6L50 26l-2.6-6.4L41 17l6.4-2.6z" fill="currentColor" />
    </svg>
  );
}

/** Salas con amigos: dos personas, una delante de otra. */
export function RoomsIcon({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <circle cx="40" cy="20" r="8" fill="currentColor" opacity="0.55" />
      <path d="M26 50c0-9 6-15 14-15s14 6 14 15z" fill="currentColor" opacity="0.55" />
      <circle cx="25" cy="25" r="9" fill="currentColor" />
      <path d="M9 56c0-10 7-17 16-17s16 7 16 17z" fill="currentColor" />
    </svg>
  );
}

/** Para un juego que todavía no tiene ícono: el dorso de una carta. */
export function GenericGameIcon({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <rect x="16" y="8" width="32" height="48" rx="5" fill="none" stroke="currentColor" strokeWidth="3.5" />
      <path d="M32 18l8 14-8 14-8-14z" fill="currentColor" />
    </svg>
  );
}

export const COMING_SOON_ICONS: Record<string, (props: IconProps) => React.JSX.Element> = {
  minijuegos: MinigamesIcon,
  salas: RoomsIcon,
};
