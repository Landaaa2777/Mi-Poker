// Textos comunes a todos los juegos: cantidades de fichas y cartas de la baraja clásica.

const RANKS: Record<string, string> = { T: "10" };
const SUIT_SYMBOLS: Record<string, string> = { s: "♠", h: "♥", d: "♦", c: "♣" };

/** Una cantidad de fichas con punto de millar: "1.000", "10.000". */
export function formatChips(chips: number): string {
  return Math.trunc(chips)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/** El valor de una carta como se lee: "A", "10", "7". La carta llega como "Td" o "As". */
export function cardRank(card: string): string {
  return RANKS[card[0]] ?? card[0];
}

/** Carta como texto corto, para los registros: "A♠", "10♥". */
export function cardLabel(card: string): string {
  return cardRank(card) + SUIT_SYMBOLS[card[1]];
}
