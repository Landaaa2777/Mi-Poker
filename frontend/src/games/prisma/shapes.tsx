// Los cuatro palos de Prisma: cada uno con su nombre, su color y una FORMA
// distinta, para que se reconozcan también sin distinguir colores (daltonismo).
// Todos se dibujan en una caja de 24 × 24.

export type PrismaColor = "panal" | "halo" | "cumbre" | "astro";

export interface SuitInfo {
  name: string; // como se dice en pantalla
  shape: string; // la forma, en palabras, para lectores de pantalla
  color: string; // variable CSS del token de color
}

export const SUITS: Record<PrismaColor, SuitInfo> = {
  panal: { name: "Panal", shape: "hexágono", color: "var(--color-panal)" },
  halo: { name: "Halo", shape: "anillo", color: "var(--color-halo)" },
  cumbre: { name: "Cumbre", shape: "triángulo", color: "var(--color-cumbre)" },
  astro: { name: "Astro", shape: "estrella", color: "var(--color-astro)" },
};

export const SUIT_ORDER: PrismaColor[] = ["panal", "halo", "cumbre", "astro"];

// Trazos de cada forma. El anillo se rellena con la regla "evenodd" (círculo menos círculo).
const PATHS: Record<PrismaColor, string> = {
  panal: "M12 1.6 21 6.8v10.4L12 22.4 3 17.2V6.8z",
  halo: "M12 2a10 10 0 1 0 0 20 10 10 0 1 0 0-20zm0 5.2a4.8 4.8 0 1 1 0 9.6 4.8 4.8 0 1 1 0-9.6z",
  cumbre: "M12 2.2 22.4 20.6H1.6z",
  astro: "M12 .8c.9 6.4 3.9 9.6 10.4 11.2-6.5 1.6-9.5 4.8-10.4 11.2C11.1 16.8 8.1 13.6 1.6 12 8.1 10.4 11.1 7.2 12 .8z",
};

/** La forma de un palo, como trazo SVG (va dentro de un <svg viewBox="0 0 24 24">). */
export function SuitPath({ suit, fill = "currentColor" }: { suit: PrismaColor; fill?: string }) {
  return <path d={PATHS[suit]} fill={fill} fillRule="evenodd" />;
}

/** El símbolo de un palo suelto, con su color. */
export function SuitSymbol({ suit, className = "" }: { suit: PrismaColor; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} role="img" aria-label={`${SUITS[suit].name} (${SUITS[suit].shape})`}>
      <SuitPath suit={suit} fill={SUITS[suit].color} />
    </svg>
  );
}
