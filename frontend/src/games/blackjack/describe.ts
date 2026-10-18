// Textos del blackjack: el registro de la ronda y las etiquetas de la mesa.

import type { LogLine } from "../../shared/components/EventLog";
import { cardLabel } from "../../shared/format";
import { handTotal, type Frame, type HandFrame } from "./timeline";
import type { ActionName, HandResult } from "./types";

export const ACTION_LABEL: Record<ActionName, string> = {
  hit: "Pedir",
  stand: "Plantarse",
  double: "Doblar",
  split: "Dividir",
  surrender: "Rendirse",
};

/** Lo que hizo alguien, para enseñarlo junto a su asiento. */
export const DONE_LABEL: Record<string, string> = {
  hit: "Pide",
  stand: "Se planta",
  double: "Dobla",
  split: "Divide",
  surrender: "Se rinde",
  insurance: "Seguro",
};

/** "17", o "7/17" si es blando (el As puede contar 1 u 11). */
export function totalLabel(total: number, soft: boolean): string {
  return soft && total < 21 ? `${total - 10}/${total}` : String(total);
}

/** Lo que gana (o pierde) una mano ya pagada, en positivo o negativo. */
export function handProfit(hand: Pick<HandFrame, "bet" | "payout" | "result">): number {
  return hand.result === null ? 0 : hand.payout - hand.bet;
}

const RESULT_LABEL: Record<HandResult, string> = {
  win: "Gana",
  blackjack: "¡Blackjack!",
  push: "Empate",
  lose: "Pierde",
  surrender: "Rendido",
};

export function resultLabel(result: HandResult): string {
  return RESULT_LABEL[result];
}

/**
 * Una línea del registro de la ronda: el suceso número `index` de `frame.events`.
 * Solo se mira lo que había pasado hasta ese momento. `me` es mi asiento: lo
 * mío se cuenta en segunda persona.
 */
export function describeEvent(index: number, frame: Frame, me: number): string | null {
  const event = frame.events[index];
  const before = frame.events.slice(0, index);
  const seat = event.seat === null ? null : frame.seats[event.seat];
  const mine = event.seat === me;
  const name = seat?.name ?? "";
  // Verbo según quién: "Brisa pide" o "Pides".
  const does = (theirs: string, yours: string) => (mine ? yours : `${name} ${theirs}`);
  // Tras dividir, cada línea dice de qué mano habla.
  const split = before.some((earlier) => earlier.kind === "split" && earlier.seat === event.seat);
  const handNote = split ? ` (mano ${(event.hand ?? 0) + 1})` : "";
  const card = event.card ? cardLabel(event.card) : "";

  switch (event.kind) {
    case "shuffle":
      return "— Se baraja el zapato —";
    case "bet":
      return `${does("apuesta", "Apuestas")} ${event.amount}`;
    case "card":
      return `${does("recibe", "Recibes")} ${card}${handNote}`;
    case "dealer_card":
      return before.some((earlier) => earlier.kind === "dealer_card")
        ? `El crupier saca ${card}`
        : `El crupier enseña ${card}`;
    case "hole_card":
      return "El crupier deja una carta tapada";
    case "insurance":
      return event.amount > 0
        ? `${does("se asegura", "Te aseguras")} por ${event.amount}`
        : does("no se asegura", "No te aseguras");
    case "peek":
      return event.result === "blackjack"
        ? "El crupier mira su carta tapada: ¡tiene blackjack!"
        : "El crupier mira su carta tapada: no tiene blackjack";
    case "insurance_paid":
      return event.amount > 0
        ? `${does("cobra", "Cobras")} ${event.amount} del seguro`
        : does("pierde el seguro", "Pierdes el seguro");
    case "action": {
      const verbs: Record<string, [string, string]> = {
        hit: ["pide carta", "Pides carta"],
        stand: ["se planta", "Te plantas"],
        double: ["dobla la apuesta", "Doblas la apuesta"],
        split: ["divide su pareja", "Divides tu pareja"],
        surrender: ["se rinde", "Te rindes"],
      };
      const [theirs, yours] = verbs[event.action] ?? [event.action, event.action];
      return does(theirs, yours) + handNote;
    }
    case "split":
      return null; // ya lo cuenta la jugada "divide"
    case "reveal": {
      // Lo que suma el crupier en ese momento: su carta vista y la que destapa.
      const cards = [...before, event]
        .filter((seen) => (seen.kind === "dealer_card" || seen.kind === "reveal") && seen.card)
        .map((seen) => seen.card!);
      return `El crupier destapa ${card}: ${handTotal(cards).total}`;
    }
    case "settle": {
      const hand = seat?.hands[event.hand ?? 0];
      const profit = hand ? handProfit(hand) : 0;
      switch (event.result as HandResult) {
        case "blackjack":
          return `¡Blackjack! ${does("cobra", "Cobras")} ${profit}${handNote}`;
        case "win":
          return `${does("gana", "Ganas")} ${profit}${handNote}`;
        case "push":
          return does("empata y recupera su apuesta", "Empatas y recuperas tu apuesta") + handNote;
        case "surrender":
          return `${does("recupera", "Recuperas")} ${event.amount}${handNote}`;
        default:
          return `${does("pierde", "Pierdes")} ${-profit}${handNote}`;
      }
    }
  }
}


/** Las líneas del registro de la ronda que se ve ahora en la mesa. */
export function logLines(frame: Frame, me: number): LogLine[] {
  return frame.events.flatMap((event, index) => {
    const text = describeEvent(index, frame, me);
    if (text === null) return [];
    const tone = event.kind === "settle" ? "highlight" : event.seat === me ? "mine" : "others";
    return [{ text, tone } as const];
  });
}
