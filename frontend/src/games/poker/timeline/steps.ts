// Convierte cada estado del servidor en pasos que se reproducen de uno en uno.
//
// El servidor envía la mesa completa tras cada cambio, con un registro
// (`events`) que solo crece. Aquí se compara con el estado anterior, se sacan
// los sucesos nuevos y se calcula cómo se ve la mesa después de cada uno. Esos
// cálculos son solo para dibujar: el último paso es siempre el estado del
// servidor, que sigue siendo la única autoridad.

import { actionLabel, isOpeningBet } from "../format";
import type { GameState, HandEvent } from "../types";
import { frameFromState, newHandFrame, wasDealtIn, type Frame, type SeatFrame } from "./frame";

export type Step =
  | { kind: "new_hand"; frame: Frame } // mesa limpia para la mano nueva
  | { kind: "deal"; seat: number; index: number; frame: Frame } // una carta a un jugador
  | { kind: "board"; street: string; card: string; frame: Frame } // una carta comunitaria
  | { kind: "event"; event: HandEvent; frame: Frame } // ciega, jugada, devolución, mostrar o ganar
  | { kind: "settle"; frame: Frame }; // la mesa tal como la tiene el servidor

function sameEvent(a: HandEvent, b: HandEvent): boolean {
  return (
    a.kind === b.kind &&
    a.seat === b.seat &&
    a.amount === b.amount &&
    a.action === b.action &&
    a.all_in === b.all_in &&
    a.cards.join() === b.cards.join()
  );
}

/**
 * ¿`next` es la misma mano que `previous`, más avanzada?
 *
 * El número de mano no basta: al reiniciar la partida vuelve a ser el 1. Una
 * mano continúa si conserva mis cartas y su registro empieza por el anterior.
 */
export function continuesHand(previous: GameState | null, next: GameState): boolean {
  return (
    previous !== null &&
    previous.hand_number === next.hand_number &&
    previous.hole_cards.join() === next.hole_cards.join() &&
    previous.events.length <= next.events.length &&
    previous.events.every((event, index) => sameEvent(event, next.events[index]))
  );
}

/** Asientos en el orden en que reparte el motor: desde la izquierda del botón. */
export function dealOrder(state: GameState): number[] {
  const button = state.button_seat ?? 0;
  const seats = state.seats.filter(wasDealtIn).map((seat) => seat.seat);
  return [...seats.filter((seat) => seat > button), ...seats.filter((seat) => seat <= button)];
}

function updateSeat(frame: Frame, seat: number | null, change: (seat: SeatFrame) => void): void {
  const index = frame.seats.findIndex((candidate) => candidate.seat === seat);
  if (index < 0) return;
  const updated = { ...frame.seats[index] };
  change(updated);
  frame.seats = frame.seats.map((original, i) => (i === index ? updated : original));
}

/** Quien recupera fichas (devolución o premio) deja de estar all-in. */
function liveStatus(seat: SeatFrame): SeatFrame["status"] {
  return seat.status === "all_in" && seat.stack > 0 ? "active" : seat.status;
}

/** Recoge las apuestas de la ronda y borra las jugadas anunciadas. */
function closeRound(frame: Frame): void {
  frame.seats = frame.seats.map((seat) => ({ ...seat, bet: 0, action: null }));
}

/** La mesa después de un suceso (todos menos las cartas comunitarias). */
function applyEvent(previous: Frame, event: HandEvent, target: GameState): Frame {
  const frame: Frame = { ...previous, events: [...previous.events, event], actingSeat: null };
  const pay = (seat: SeatFrame, amount: number) => {
    seat.stack -= amount;
    seat.bet += amount;
    frame.pot += amount;
  };

  switch (event.kind) {
    case "small_blind":
      frame.smallBlindSeat = event.seat;
      updateSeat(frame, event.seat, (seat) => pay(seat, event.amount));
      break;
    case "big_blind":
      frame.bigBlindSeat = event.seat;
      updateSeat(frame, event.seat, (seat) => pay(seat, event.amount));
      break;
    case "action": {
      const opening = isOpeningBet(frame.events, frame.events.length - 1);
      frame.actingSeat = event.seat;
      updateSeat(frame, event.seat, (seat) => {
        if (event.action === "call") pay(seat, event.amount);
        // En una subida el monto es la apuesta total, no lo que se añade.
        if (event.action === "raise") pay(seat, event.amount - seat.bet);
        if (event.action === "fold") {
          seat.status = "folded";
          seat.cards = [];
        }
        seat.action = actionLabel(event, opening);
      });
      break;
    }
    case "refund":
      updateSeat(frame, event.seat, (seat) => {
        seat.stack += event.amount;
        seat.bet -= event.amount;
        seat.status = liveStatus(seat);
      });
      frame.pot -= event.amount;
      break;
    case "show":
      closeRound(frame);
      updateSeat(frame, event.seat, (seat) => {
        seat.cards = event.cards;
        seat.handName = target.result?.hand_names[String(seat.seat)] ?? null;
      });
      break;
    case "win":
      closeRound(frame);
      updateSeat(frame, event.seat, (seat) => {
        seat.stack += event.amount;
        seat.won += event.amount;
        seat.status = liveStatus(seat);
      });
      frame.pot -= event.amount;
      break;
    case "board":
      throw new Error("Las cartas comunitarias se reparten con boardSteps");
  }

  if (event.all_in) updateSeat(frame, event.seat, (seat) => (seat.status = "all_in"));
  return frame;
}

/** Flop, turn o river: una carta por paso. El suceso entra al registro con la última. */
function boardSteps(previous: Frame, event: HandEvent): Step[] {
  const steps: Step[] = [];
  let frame: Frame = { ...previous, phase: event.action, actingSeat: null };
  closeRound(frame);
  event.cards.forEach((card, index) => {
    const last = index === event.cards.length - 1;
    frame = {
      ...frame,
      board: [...frame.board, card],
      events: last ? [...previous.events, event] : frame.events,
    };
    steps.push({ kind: "board", street: event.action, card, frame });
  });
  return steps;
}

/** Reparto: una carta a cada jugador y luego otra, como hace el motor. */
function dealSteps(previous: Frame, target: GameState): Step[] {
  const steps: Step[] = [];
  let frame = previous;
  for (const index of [0, 1]) {
    for (const seat of dealOrder(target)) {
      frame = { ...frame };
      updateSeat(frame, seat, (dealt) => {
        // Solo conozco mis cartas; las de los demás llegan boca abajo.
        const mine = dealt.seat === target.viewer_seat ? target.hole_cards[index] : undefined;
        dealt.cards = [...dealt.cards, mine ?? null];
      });
      steps.push({ kind: "deal", seat, index, frame });
    }
  }
  return steps;
}

function isBlind(event: HandEvent): boolean {
  return event.kind === "small_blind" || event.kind === "big_blind";
}

/**
 * Pasos para ir de `previous` (lo último recibido) a `next`.
 *
 * El reparto no viene en el registro del servidor: se deduce al detectar una
 * mano nueva y se coloca después de las ciegas.
 */
export function buildSteps(previous: GameState | null, next: GameState): Step[] {
  const steps: Step[] = [];
  let frame: Frame;
  let pending: HandEvent[];
  let dealPending = false;

  if (previous !== null && continuesHand(previous, next)) {
    frame = frameFromState(previous);
    pending = next.events.slice(previous.events.length);
  } else {
    frame = newHandFrame(next);
    pending = next.events;
    dealPending = true;
    steps.push({ kind: "new_hand", frame });
  }

  for (const event of pending) {
    if (dealPending && !isBlind(event)) {
      const dealt = dealSteps(frame, next);
      steps.push(...dealt);
      frame = dealt.at(-1)?.frame ?? frame;
      dealPending = false;
    }
    if (event.kind === "board") {
      const dealt = boardSteps(frame, event);
      steps.push(...dealt);
      frame = dealt.at(-1)?.frame ?? frame;
    } else {
      frame = applyEvent(frame, event, next);
      steps.push({ kind: "event", event, frame });
    }
  }
  if (dealPending) steps.push(...dealSteps(frame, next));

  steps.push({ kind: "settle", frame: frameFromState(next) });
  return steps;
}
