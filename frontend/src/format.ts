import type { GameState, HandEvent } from "./types";

const SUITS: Record<string, string> = { s: "♠", h: "♥", d: "♦", c: "♣" };
const STREETS: Record<string, string> = {
  preflop: "Preflop",
  flop: "Flop",
  turn: "Turn",
  river: "River",
  complete: "Mano terminada",
};

export function cardLabel(card: string): string {
  const rank = card[0] === "T" ? "10" : card[0];
  return rank + SUITS[card[1]];
}

export function isRed(card: string): boolean {
  return card[1] === "h" || card[1] === "d";
}

export function streetName(phase: string | null): string {
  return phase ? (STREETS[phase] ?? phase) : "";
}

/** Una línea del registro de la mano, en español. */
export function describeEvent(event: HandEvent, state: GameState): string {
  const name = state.seats.find((seat) => seat.seat === event.seat)?.name ?? "";
  const allIn = event.all_in ? " (all-in)" : "";
  const cards = event.cards.map(cardLabel).join(" ");
  switch (event.kind) {
    case "small_blind":
      return `${name} pone la ciega pequeña: ${event.amount}${allIn}`;
    case "big_blind":
      return `${name} pone la ciega grande: ${event.amount}${allIn}`;
    case "board":
      return `— ${streetName(event.action)}: ${cards} —`;
    case "refund":
      return `Se devuelven ${event.amount} fichas no igualadas a ${name}`;
    case "show":
      return `${name} muestra ${cards}`;
    case "win":
      return `${name} gana ${event.amount}`;
    case "action":
      if (event.action === "fold") return `${name} se retira`;
      if (event.action === "check") return `${name} pasa`;
      if (event.action === "call") return `${name} iguala ${event.amount}${allIn}`;
      return `${name} sube a ${event.amount}${allIn}`;
  }
}
