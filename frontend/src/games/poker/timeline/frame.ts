// Un "frame" es la mesa tal como se dibuja en un momento concreto de la mano.
// El último frame de cada tanda sale tal cual del estado del servidor.

import { actionLabel, isOpeningBet } from "../format";
import type { GameState, HandEvent, Seat, SeatStatus } from "../types";

export interface SeatFrame {
  seat: number;
  name: string;
  isHuman: boolean;
  level: string;
  style: string;
  stack: number;
  bet: number; // apostado en la ronda actual
  status: SeatStatus;
  cards: (string | null)[]; // cartas que tiene delante; null = boca abajo
  action: string | null; // su última jugada en esta ronda
  won: number; // fichas ganadas en esta mano hasta ahora
  handName: string | null; // jugada enseñada en el showdown
}

export interface Frame {
  handNumber: number;
  phase: string; // preflop, flop, turn, river o complete
  buttonSeat: number | null;
  smallBlindSeat: number | null;
  bigBlindSeat: number | null;
  smallBlind: number;
  bigBlind: number;
  board: string[];
  pot: number; // fichas en el centro de la mesa
  actingSeat: number | null; // jugador resaltado
  seats: SeatFrame[];
  events: HandEvent[]; // registro visible hasta este momento
}

/** ¿Recibió cartas en esta mano? Un eliminado en la mano sigue contando. */
export function wasDealtIn(seat: Seat): boolean {
  return seat.status !== "out" || seat.contributed > 0;
}

function blindSeat(events: HandEvent[], kind: HandEvent["kind"]): number | null {
  return events.find((event) => event.kind === kind)?.seat ?? null;
}

/** Última jugada de cada asiento en la ronda de apuestas en curso. */
function roundActions(state: GameState): Map<number, string> {
  const labels = new Map<number, string>();
  if (!state.hand_in_progress) return labels;
  state.events.forEach((event, index) => {
    if (event.kind === "board") labels.clear();
    else if (event.kind === "action" && event.seat !== null) {
      labels.set(event.seat, actionLabel(event, isOpeningBet(state.events, index)));
    }
  });
  return labels;
}

function seatCards(seat: Seat): (string | null)[] {
  if (!wasDealtIn(seat) || seat.status === "folded") return [];
  return seat.hole_cards ?? [null, null];
}

/** La mesa exactamente como la describe el servidor. */
export function frameFromState(state: GameState): Frame {
  const actions = roundActions(state);
  const result = state.result;
  return {
    handNumber: state.hand_number,
    phase: state.phase ?? "preflop",
    buttonSeat: state.button_seat,
    smallBlindSeat: blindSeat(state.events, "small_blind"),
    bigBlindSeat: blindSeat(state.events, "big_blind"),
    smallBlind: state.small_blind,
    bigBlind: state.big_blind,
    board: state.board,
    // Con la mano terminada el bote ya está repartido: en el centro no queda nada.
    pot: state.hand_in_progress ? state.pot : 0,
    actingSeat: state.hand_in_progress ? state.to_act_seat : null,
    seats: state.seats.map((seat) => ({
      seat: seat.seat,
      name: seat.name,
      isHuman: seat.is_human,
      level: seat.level,
      style: seat.style,
      stack: seat.stack,
      bet: seat.bet,
      status: seat.status,
      cards: seatCards(seat),
      action: actions.get(seat.seat) ?? null,
      won: result?.payouts[String(seat.seat)] ?? 0,
      handName: result?.hand_names[String(seat.seat)] ?? null,
    })),
    events: state.events,
  };
}

/** La mesa justo antes de empezar la mano: sin cartas, sin apuestas y sin ciegas. */
export function newHandFrame(state: GameState): Frame {
  const payouts = state.result?.payouts ?? {};
  return {
    handNumber: state.hand_number,
    phase: "preflop",
    buttonSeat: state.button_seat,
    smallBlindSeat: null,
    bigBlindSeat: null,
    smallBlind: state.small_blind,
    bigBlind: state.big_blind,
    board: [],
    pot: 0,
    actingSeat: null,
    seats: state.seats.map((seat) => ({
      seat: seat.seat,
      name: seat.name,
      isHuman: seat.is_human,
      level: seat.level,
      style: seat.style,
      // Fichas al empezar: las de ahora, más lo aportado, menos lo ya cobrado.
      stack: seat.stack + seat.contributed - (payouts[String(seat.seat)] ?? 0),
      bet: 0,
      status: wasDealtIn(seat) ? "active" : "out",
      cards: [],
      action: null,
      won: 0,
      handName: null,
    })),
    events: [],
  };
}
