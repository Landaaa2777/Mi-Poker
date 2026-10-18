// Íconos del menú para lo que todavía no tiene página propia ("Próximamente").
// Los de cada juego viven con su juego (games/<juego>/icon.tsx). Todos son SVG
// dibujados por código, con diseño propio.

export interface IconProps {
  className?: string;
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
  salas: RoomsIcon,
};
