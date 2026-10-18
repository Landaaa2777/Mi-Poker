// Textos comunes a todos los juegos: cantidades de fichas, cartas de la baraja
// clásica y cuándo llega algo.

const RANKS: Record<string, string> = { T: "10" };
const SUIT_SYMBOLS: Record<string, string> = { s: "♠", h: "♥", d: "♦", c: "♣" };

/** Una cantidad de fichas con punto de millar: "1.000", "10.000". */
export function formatChips(chips: number): string {
  return Math.trunc(chips)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

const CLOCK = new Intl.DateTimeFormat("es", { hour: "2-digit", minute: "2-digit" });
const DAY_AND_MONTH = new Intl.DateTimeFormat("es", { day: "numeric", month: "long" });

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/**
 * Cuándo llega algo, en palabras: "mañana a las 20:15 (dentro de 23 h 59 min)".
 * `at` y `now` van en segundos desde 1970; el día y la hora, en la zona del navegador.
 */
export function describeArrival(at: number, now: number): string {
  const left = Math.round(at - now);
  if (left < 60) return "en un momento";
  const when = new Date(at * 1000);
  const today = new Date(now * 1000);
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  const day = sameDay(when, today)
    ? "hoy"
    : sameDay(when, tomorrow)
      ? "mañana"
      : `el ${DAY_AND_MONTH.format(when)}`;
  const hours = Math.floor(left / 3600);
  const minutes = Math.floor((left % 3600) / 60);
  const wait = hours === 0 ? `${minutes} min` : minutes === 0 ? `${hours} h` : `${hours} h ${minutes} min`;
  return `${day} a las ${CLOCK.format(when)} (dentro de ${wait})`;
}

/** El valor de una carta como se lee: "A", "10", "7". La carta llega como "Td" o "As". */
export function cardRank(card: string): string {
  return RANKS[card[0]] ?? card[0];
}

/** Carta como texto corto, para los registros: "A♠", "10♥". */
export function cardLabel(card: string): string {
  return cardRank(card) + SUIT_SYMBOLS[card[1]];
}
