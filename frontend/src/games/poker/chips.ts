// Las fichas que se ven en la mesa de poker en cada momento de la mano: las
// apostadas delante de cada jugador en la ronda en curso, las del bote y las
// que ha ganado cada uno. Salen del registro de la mano (`events`), como en
// una mesa de verdad: cada apuesta pone sus fichas encima de las anteriores, y
// al cerrar la ronda todas van al bote.

import { breakdown, colorUp, pile, total, type Denomination } from "../../shared/chips/chips";
import type { Frame } from "./timeline/frame";
import type { HandEvent } from "./types";

export interface TableChips {
  bets: Map<number, Denomination[]>; // delante de cada asiento, en la ronda en curso
  pot: Denomination[]; // en el centro: lo de las rondas ya cerradas
  won: Map<number, Denomination[]>; // lo que ha cobrado cada asiento en esta mano
}

/** Las aportaciones de cada asiento en la ronda abierta y las de las rondas cerradas. */
function contributions(events: readonly HandEvent[]) {
  let current = new Map<number, number[]>();
  let bets = new Map<number, number>(); // apuesta total de cada asiento en la ronda
  const collected: number[] = [];
  const close = () => {
    for (const amounts of current.values()) collected.push(...amounts);
    current = new Map();
    bets = new Map();
  };
  const add = (seat: number | null, amount: number) => {
    if (seat === null || amount <= 0) return;
    current.set(seat, [...(current.get(seat) ?? []), amount]);
    bets.set(seat, (bets.get(seat) ?? 0) + amount);
  };

  for (const event of events) {
    switch (event.kind) {
      case "small_blind":
      case "big_blind":
        add(event.seat, event.amount);
        break;
      case "action":
        if (event.action === "call") add(event.seat, event.amount);
        // En una subida el monto es la apuesta total, no lo que se añade.
        if (event.action === "raise") add(event.seat, event.amount - (bets.get(event.seat ?? -1) ?? 0));
        break;
      case "refund": {
        // Lo que nadie igualó vuelve al jugador: le quedan esas fichas de menos.
        if (event.seat === null) break;
        const left = (bets.get(event.seat) ?? 0) - event.amount;
        current.set(event.seat, left > 0 ? [left] : []);
        bets.set(event.seat, Math.max(0, left));
        break;
      }
      case "board":
      case "show":
      case "win":
        close();
        break;
    }
  }
  return { current, collected, close };
}

/** Las fichas de la mesa tal como está en `frame`. */
export function tableChips(frame: Frame): TableChips {
  const { current, collected, close } = contributions(frame.events);
  const onTable = frame.seats.reduce((sum, seat) => sum + seat.bet, 0);
  // Las apuestas ya se recogieron (empieza a salir el flop, por ejemplo) aunque
  // el registro todavía no lo diga: van al bote.
  if (onTable === 0) close();

  const bets = new Map<number, Denomination[]>();
  const won = new Map<number, Denomination[]>();
  // Todo lo apostado en la mano: quien se lleva el bote entero se lleva esas mismas fichas.
  const everything = colorUp(pile([...collected, ...[...current.values()].flat()], 60));
  for (const seat of frame.seats) {
    const amounts = current.get(seat.seat) ?? [];
    const sum = amounts.reduce((a, b) => a + b, 0);
    // Si las cuentas no cuadran con lo que dice la mesa, mandan las de la mesa.
    if (seat.bet > 0) bets.set(seat.seat, sum === seat.bet ? pile(amounts) : breakdown(seat.bet));
    if (seat.won > 0) won.set(seat.seat, total(everything) === seat.won ? everything : breakdown(seat.won));
  }
  const middle = Math.max(0, frame.pot - onTable);
  // Al llegar al bote, el crupier cambia las fichas pequeñas por otras de más valor.
  const pot = colorUp(pile(collected, 60));
  return { bets, pot: total(pot) === middle ? pot : breakdown(middle), won };
}
