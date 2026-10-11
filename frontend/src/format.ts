import type { HandEvent } from "./types";

const STREETS: Record<string, string> = {
  preflop: "Preflop",
  flop: "Flop",
  turn: "Turn",
  river: "River",
  complete: "Mano terminada",
};

const RANKS: Record<string, string> = { T: "10" };
const SUIT_SYMBOLS: Record<string, string> = { s: "♠", h: "♥", d: "♦", c: "♣" };

/** Una cantidad de fichas con punto de millar: "1.000", "10.000". */
export function formatChips(chips: number): string {
  return Math.trunc(chips)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

export function cardRank(card: string): string {
  return RANKS[card[0]] ?? card[0];
}

/** Carta como texto corto, para el registro: "A♠", "10♥". */
export function cardLabel(card: string): string {
  return cardRank(card) + SUIT_SYMBOLS[card[1]];
}

export function streetName(phase: string | null): string {
  return phase ? (STREETS[phase] ?? phase) : "";
}

/**
 * ¿Es la primera apuesta de su ronda? Entonces se dice "apuesta" y no "sube".
 * Las ciegas cuentan como apuesta, así que preflop siempre se sube.
 */
export function isOpeningBet(events: HandEvent[], index: number): boolean {
  for (let i = index - 1; i >= 0; i--) {
    const earlier = events[i];
    if (earlier.kind === "board") return true;
    if (earlier.kind === "small_blind" || earlier.kind === "big_blind") return false;
    if (earlier.kind === "action" && earlier.action === "raise") return false;
  }
  return true;
}

/** Jugada de un jugador en pocas palabras, para mostrarla junto a su asiento. */
export function actionLabel(event: HandEvent, opening: boolean): string {
  if (event.action === "fold") return "Se retira";
  if (event.action === "check") return "Pasa";
  if (event.all_in) return "All-in";
  if (event.action === "call") return `Iguala ${event.amount}`;
  return opening ? `Apuesta ${event.amount}` : `Sube a ${event.amount}`;
}

/**
 * Una línea del registro de la mano, en español. `name` es quien protagoniza el
 * suceso; sin nombre (`null`) se cuenta en segunda persona, porque eres tú.
 */
export function describeEvent(event: HandEvent, name: string | null, opening: boolean): string {
  const allIn = event.all_in ? " (all-in)" : "";
  const cards = event.cards.map(cardLabel).join(" ");
  // Verbo según quién actúa: "Chispa iguala" o "Igualas".
  const does = (theirs: string, yours: string) => (name === null ? yours : `${name} ${theirs}`);
  switch (event.kind) {
    case "small_blind":
      return `${does("pone", "Pones")} la ciega pequeña: ${event.amount}${allIn}`;
    case "big_blind":
      return `${does("pone", "Pones")} la ciega grande: ${event.amount}${allIn}`;
    case "board":
      return `— ${streetName(event.action)}: ${cards} —`;
    case "refund":
      return name === null
        ? `Recuperas ${event.amount} fichas no igualadas`
        : `Se devuelven ${event.amount} fichas no igualadas a ${name}`;
    case "show":
      return `${does("muestra", "Muestras")} ${cards}`;
    case "win":
      return `${does("gana", "Ganas")} ${event.amount}`;
    case "action":
      if (event.action === "fold") return does("se retira", "Te retiras");
      if (event.action === "check") return does("pasa", "Pasas");
      if (event.action === "call") return `${does("iguala", "Igualas")} ${event.amount}${allIn}`;
      return opening
        ? `${does("apuesta", "Apuestas")} ${event.amount}${allIn}`
        : `${does("sube a", "Subes a")} ${event.amount}${allIn}`;
  }
}
