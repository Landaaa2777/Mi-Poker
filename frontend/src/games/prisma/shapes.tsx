// Los palos de Prisma: cada uno con su nombre, su color y una FORMA distinta,
// para que se reconozcan también sin distinguir colores (daltonismo). Los
// cuatro de siempre son los de la cara de luz; en Doble cara, la cara de
// sombra tiene otros cuatro, en tonos profundos. Todos se dibujan en una caja
// de 24 × 24.

export type LightColor = "panal" | "halo" | "cumbre" | "astro";
export type DarkColor = "brasa" | "ambar" | "jade" | "indigo";
export type PrismaColor = LightColor | DarkColor;

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
  brasa: { name: "Brasa", shape: "rombo", color: "var(--color-brasa)" },
  ambar: { name: "Ámbar", shape: "luna", color: "var(--color-ambar)" },
  jade: { name: "Jade", shape: "hoja", color: "var(--color-jade)" },
  indigo: { name: "Índigo", shape: "gota", color: "var(--color-indigo)" },
};

/** Los palos de la cara de luz (los de siempre), en su orden. */
export const SUIT_ORDER: LightColor[] = ["panal", "halo", "cumbre", "astro"];
/** Los palos de la cara de sombra (Doble cara). */
export const DARK_ORDER: DarkColor[] = ["brasa", "ambar", "jade", "indigo"];

const DARK = new Set<PrismaColor>(DARK_ORDER);

/** ¿Es un palo de la cara de sombra? */
export const isDark = (suit: PrismaColor) => DARK.has(suit);

// Trazos de cada forma. Se rellenan con la regla "evenodd": así el anillo es un
// círculo menos otro y la hoja lleva su nervio en hueco.
const PATHS: Record<PrismaColor, string> = {
  panal: "M12 1.6 21 6.8v10.4L12 22.4 3 17.2V6.8z",
  halo: "M12 2a10 10 0 1 0 0 20 10 10 0 1 0 0-20zm0 5.2a4.8 4.8 0 1 1 0 9.6 4.8 4.8 0 1 1 0-9.6z",
  cumbre: "M12 2.2 22.4 20.6H1.6z",
  astro: "M12 .8c.9 6.4 3.9 9.6 10.4 11.2-6.5 1.6-9.5 4.8-10.4 11.2C11.1 16.8 8.1 13.6 1.6 12 8.1 10.4 11.1 7.2 12 .8z",
  // Rombo alto.
  brasa: "M12 1.2 20.2 12 12 22.8 3.8 12z",
  // Luna creciente: un círculo mordido por otro.
  ambar: "M11.41 2.02A10 10 0 1 0 21.58 14.86 8.2 8.2 0 0 1 11.41 2.02z",
  // Hoja en diagonal, con su nervio.
  jade: "M3.4 20.6C3.4 9.4 9.6 3.4 20.6 3.4c0 11.2-6.2 17.2-17.2 17.2zM6.2 18.9l11.6-11.6-.9-.9L5.3 18z",
  // Gota.
  indigo: "M12 1.6c-1.4 2.2-7.6 9.3-7.6 13.5a7.6 7.6 0 0 0 15.2 0C19.6 10.9 13.4 3.8 12 1.6z",
};

/** La forma de un palo, como trazo SVG (va dentro de un <svg viewBox="0 0 24 24">). */
export function SuitPath({ suit, fill = "currentColor" }: { suit: PrismaColor; fill?: string }) {
  // Con `style`, el color puede ser una variable CSS (los tokens de diseño).
  return <path d={PATHS[suit]} fillRule="evenodd" style={{ fill }} />;
}

/** El símbolo de un palo suelto, con su color. */
export function SuitSymbol({ suit, className = "" }: { suit: PrismaColor; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} role="img" aria-label={`${SUITS[suit].name} (${SUITS[suit].shape})`}>
      <SuitPath suit={suit} fill={SUITS[suit].color} />
    </svg>
  );
}
