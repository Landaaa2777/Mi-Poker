// Las fichas que se ven en la mesa de blackjack: la apuesta de cada mano en
// su círculo (doblar pone otra pila igual al lado), lo que paga el crupier a
// la mano que gana, y el seguro. Lo perdido vuelve a la bandeja del crupier.

import { breakdown, pile, type Denomination } from "../../shared/chips/chips";
import type { Frame, HandFrame, SeatFrame } from "./timeline";

export interface HandChips {
  bet: Denomination[]; // lo apostado que sigue en la mesa
  win: Denomination[]; // lo que ha pagado el crupier
}

export interface SeatChips {
  hands: HandChips[];
  insurance: Denomination[];
}

/** Fichas de una mano según cómo va. */
export function handChips(hand: HandFrame): HandChips {
  // Al doblar se pone otra apuesta igual: dos montones, no uno cambiado.
  const placed = hand.doubled ? pile([hand.bet / 2, hand.bet / 2]) : breakdown(hand.bet);
  switch (hand.result) {
    case null:
    case "push":
      return { bet: placed, win: [] };
    case "win":
    case "blackjack":
      return { bet: placed, win: breakdown(hand.payout - hand.bet) };
    case "surrender":
      return { bet: breakdown(hand.payout), win: [] }; // recupera la mitad
    case "lose":
      return { bet: [], win: [] };
  }
}

/** ¿Ya se sabe que el crupier no tiene blackjack? Entonces el seguro se pierde. */
function insuranceLost(frame: Frame): boolean {
  return frame.events.some((event) => event.kind === "peek" && event.result !== "blackjack");
}

export function seatChips(frame: Frame, seat: SeatFrame): SeatChips {
  return {
    hands: seat.hands.map(handChips),
    insurance: seat.insurance > 0 && !insuranceLost(frame) ? breakdown(seat.insurance) : [],
  };
}
