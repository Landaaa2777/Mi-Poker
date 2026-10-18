// Línea de tiempo del blackjack: convierte el registro de la ronda (`events`)
// en pasos que se reproducen de uno en uno: cada carta que sale del zapato,
// cada jugada, la carta tapada que se destapa y los pagos.
//
// Cada paso trae la mesa tal como debe dibujarse (`frame`). Se calcula
// rehaciendo la ronda desde el principio con el registro; el último paso es
// siempre la mesa exacta del servidor.

import type { Timeline, TimelineStep } from "../../shared/timeline/playback";
import type { GameState, HandResult, RoundEvent } from "./types";

export interface HandFrame {
  cards: string[];
  bet: number;
  total: number | null; // null mientras no tiene cartas
  soft: boolean;
  result: HandResult | null;
  payout: number;
  doubled: boolean;
  status: string; // "playing", "stood", "bust", "blackjack" o "surrendered"
}

export interface SeatFrame {
  seat: number;
  name: string;
  isHuman: boolean; // soy yo
  person?: boolean; // en una sala: lo juega una persona
  gone?: boolean; // en una sala: esa persona se ha ido
  level: string;
  stack: number;
  hands: HandFrame[];
  insurance: number;
  action: string | null; // su última jugada, para enseñarla junto al asiento
}

export interface Frame {
  round: number;
  dealer: { cards: (string | null)[]; total: number | null; soft: boolean };
  seats: SeatFrame[];
  acting: { seat: number; hand: number } | null; // mano resaltada
  note: string | null; // aviso del momento: "El crupier mira su carta tapada…"
  events: RoundEvent[]; // registro visible hasta este momento
}

export type Step =
  | { kind: "round"; frame: Frame } // mesa limpia para la ronda nueva
  | { kind: "card"; seat: number | null; frame: Frame } // una carta del zapato (seat null = crupier)
  | { kind: "reveal"; frame: Frame } // el crupier destapa su carta
  | { kind: "event"; event: RoundEvent; frame: Frame } // apuesta, jugada, seguro o pago
  | { kind: "sync"; frame: Frame }; // la mesa exacta del servidor

// --- Valor de las manos (igual que en el servidor) ---

function cardValue(card: string): number {
  const rank = card[0];
  if (rank === "A") return 11;
  if ("TJQK".includes(rank)) return 10;
  return Number(rank);
}

/** El total de unas cartas y si es blando (un As cuenta como 11). */
export function handTotal(cards: string[]): { total: number; soft: boolean } {
  let total = 0;
  let aces = 0;
  for (const card of cards) {
    if (card[0] === "A") {
      aces += 1;
      total += 1;
    } else {
      total += Math.min(cardValue(card), 10);
    }
  }
  if (aces > 0 && total + 10 <= 21) return { total: total + 10, soft: true };
  return { total, soft: false };
}

// --- La mesa del servidor, tal cual ---

export function frameFromState(state: GameState): Frame {
  const dealerCards = state.dealer.cards;
  return {
    round: state.round_number,
    dealer: {
      cards: dealerCards,
      total: dealerCards.length > 0 ? state.dealer.total : null,
      soft: state.dealer.soft,
    },
    seats: state.seats.map((seat) => ({
      seat: seat.seat,
      name: seat.name,
      isHuman: seat.is_human,
      person: seat.person,
      gone: seat.gone,
      level: seat.level,
      stack: seat.stack,
      hands: seat.hands.map((hand) => ({
        cards: hand.cards,
        bet: hand.bet,
        total: hand.cards.length > 0 ? hand.total : null,
        soft: hand.soft,
        result: hand.result,
        payout: hand.payout,
        doubled: hand.doubled,
        status: hand.status,
      })),
      insurance: seat.insurance,
      action: lastActions(state.events).get(seat.seat) ?? null,
    })),
    acting:
      state.to_act_seat !== null && state.to_act_hand !== null
        ? { seat: state.to_act_seat, hand: state.to_act_hand }
        : null,
    note: noteFor(state.events),
    events: state.events,
  };
}

/** Lo último que hizo cada asiento en esta ronda. */
function lastActions(events: RoundEvent[]): Map<number, string> {
  const labels = new Map<number, string>();
  for (const event of events) {
    if (event.seat === null) continue;
    if (event.kind === "action") labels.set(event.seat, event.action);
    if (event.kind === "insurance" && event.amount > 0) labels.set(event.seat, "insurance");
  }
  return labels;
}

/** El aviso que toca enseñar tras el último suceso. */
function noteFor(events: RoundEvent[]): string | null {
  const last = events.at(-1);
  if (!last) return null;
  if (last.kind === "shuffle") return "Se baraja el zapato";
  if (last.kind === "peek") {
    return last.result === "blackjack" ? "¡El crupier tiene blackjack!" : "El crupier no tiene blackjack";
  }
  if (last.kind === "reveal") return "El crupier destapa su carta";
  return null;
}

// --- Rehacer la ronda con el registro ---

/** Dinero que sale de la mesa (apuestas) y que vuelve a ella (pagos), por asiento. */
function flows(events: RoundEvent[], seats: number): { out: number[]; back: number[] } {
  const out = Array<number>(seats).fill(0);
  const back = Array<number>(seats).fill(0);
  const bets = new Map<string, number>(); // apuesta de cada mano: "asiento-mano"
  for (const event of events) {
    if (event.seat === null) continue;
    const key = `${event.seat}-${event.hand ?? 0}`;
    if (event.kind === "bet") {
      out[event.seat] += event.amount;
      bets.set(key, event.amount);
    } else if (event.kind === "split") {
      out[event.seat] += event.amount;
      shiftHands(bets, event.seat, (event.hand ?? 0) + 1);
      bets.set(`${event.seat}-${(event.hand ?? 0) + 1}`, event.amount);
    } else if (event.kind === "action" && event.action === "double") {
      const bet = bets.get(key) ?? 0;
      out[event.seat] += bet;
      bets.set(key, bet * 2);
    } else if (event.kind === "insurance") {
      out[event.seat] += event.amount;
    } else if (event.kind === "insurance_paid" || event.kind === "settle") {
      back[event.seat] += event.amount;
    }
  }
  return { out, back };
}

/** Al dividir, las manos de la derecha se corren un sitio. */
function shiftHands<T>(map: Map<string, T>, seat: number, from: number): void {
  const moved = [...map.entries()]
    .filter(([key]) => key.startsWith(`${seat}-`) && Number(key.split("-")[1]) >= from)
    .sort((a, b) => Number(b[0].split("-")[1]) - Number(a[0].split("-")[1]));
  for (const [key, value] of moved) {
    map.delete(key);
    map.set(`${seat}-${Number(key.split("-")[1]) + 1}`, value);
  }
}

function emptyHand(bet: number): HandFrame {
  return { cards: [], bet, total: null, soft: false, result: null, payout: 0, doubled: false, status: "playing" };
}

function withTotal(hand: HandFrame): HandFrame {
  if (hand.cards.length === 0) return { ...hand, total: null, soft: false };
  const { total, soft } = handTotal(hand.cards);
  return { ...hand, total, soft };
}

/** La mesa tras los `count` primeros sucesos de la ronda de `state`. */
export function frameAt(state: GameState, count: number): Frame {
  const events = state.events.slice(0, count);
  const { out, back } = flows(state.events, state.seats.length);
  const seats: SeatFrame[] = state.seats.map((seat) => ({
    seat: seat.seat,
    name: seat.name,
    isHuman: seat.is_human,
    person: seat.person,
    gone: seat.gone,
    level: seat.level,
    // Las fichas de antes de la ronda: las de ahora, deshaciendo apuestas y pagos.
    stack: seat.stack + out[seat.seat] - back[seat.seat],
    hands: [],
    insurance: 0,
    action: null,
  }));
  const dealer: (string | null)[] = [];
  let acting: Frame["acting"] = null;

  for (const event of events) {
    const seat = event.seat === null ? null : seats[event.seat];
    const index = event.hand ?? 0;
    switch (event.kind) {
      case "bet":
        seat!.stack -= event.amount;
        seat!.hands = [emptyHand(event.amount)];
        break;
      case "card": {
        const hand = seat!.hands[index];
        seat!.hands[index] = withTotal({ ...hand, cards: [...hand.cards, event.card!] });
        break;
      }
      case "dealer_card":
        dealer.push(event.card);
        break;
      case "hole_card":
        dealer.push(null);
        break;
      case "reveal":
        dealer[1] = event.card;
        acting = null;
        break;
      case "insurance":
        seat!.stack -= event.amount;
        seat!.insurance = event.amount;
        if (event.amount > 0) seat!.action = "insurance";
        break;
      case "insurance_paid":
        seat!.stack += event.amount;
        seat!.insurance = 0;
        break;
      case "action": {
        seat!.action = event.action;
        acting = { seat: seat!.seat, hand: index };
        if (event.action === "double") {
          const hand = seat!.hands[index];
          seat!.stack -= hand.bet;
          seat!.hands[index] = { ...hand, bet: hand.bet * 2, doubled: true };
        }
        break;
      }
      case "split": {
        const hand = seat!.hands[index];
        seat!.stack -= event.amount;
        const [first, second] = hand.cards;
        seat!.hands.splice(
          index,
          1,
          withTotal({ ...hand, cards: [first] }),
          withTotal({ ...emptyHand(event.amount), cards: [second] }),
        );
        break;
      }
      case "settle": {
        const hand = seat!.hands[index];
        seat!.stack += event.amount;
        seat!.hands[index] = { ...hand, result: event.result as HandResult, payout: event.amount };
        acting = null;
        break;
      }
      case "peek":
      case "shuffle":
        break;
    }
  }

  const visible = dealer.filter((card): card is string => card !== null);
  return {
    round: state.round_number,
    dealer: {
      cards: dealer,
      total: visible.length > 0 ? handTotal(visible).total : null,
      soft: visible.length > 0 && handTotal(visible).soft,
    },
    seats,
    acting,
    note: noteFor(events),
    events,
  };
}

// --- Pasos ---

/** ¿Sigue `next` la misma ronda que `previous`, con el registro solo crecido? */
export function continuesRound(previous: GameState | null, next: GameState): boolean {
  if (previous === null || previous.round_number !== next.round_number) return false;
  if (next.events.length < previous.events.length) return false;
  return previous.events.every(
    (event, index) => JSON.stringify(event) === JSON.stringify(next.events[index]),
  );
}

export function buildSteps(previous: GameState | null, next: GameState): Step[] {
  const steps: Step[] = [];
  let from = 0;
  if (continuesRound(previous, next)) {
    from = previous!.events.length;
  } else if (next.events.length > 0) {
    steps.push({ kind: "round", frame: frameAt(next, 0) });
  }
  for (let index = from; index < next.events.length; index++) {
    const event = next.events[index];
    const frame = frameAt(next, index + 1);
    if (event.kind === "card" || event.kind === "dealer_card" || event.kind === "hole_card") {
      steps.push({ kind: "card", seat: event.seat, frame });
    } else if (event.kind === "reveal") {
      steps.push({ kind: "reveal", frame });
    } else {
      steps.push({ kind: "event", event, frame });
    }
  }
  steps.push({ kind: "sync", frame: frameFromState(next) });
  return steps;
}

/** Milisegundos que se muestra cada paso. Cada animación dura entre 200 y 500 ms. */
export function stepDelay(step: Step, next: Step | undefined): number {
  switch (step.kind) {
    case "round":
      return 250;
    case "card":
      // En el reparto las cartas salen seguidas, solapándose en el aire.
      return next?.kind === "card" ? 170 : 460;
    case "reveal":
      return 560;
    case "event": {
      const { kind } = step.event;
      if (kind === "bet") return next?.kind === "event" && next.event.kind === "bet" ? 70 : 320;
      if (kind === "settle") {
        return next?.kind === "event" && next.event.kind === "settle" ? 140 : 900;
      }
      if (kind === "peek") return 750;
      if (kind === "shuffle") return 700;
      if (kind === "insurance" || kind === "insurance_paid") return 300;
      return 380; // jugadas y divisiones
    }
    case "sync":
      return 0;
  }
}

export const BLACKJACK_TIMELINE: Timeline<GameState, Frame, Step> = {
  buildSteps,
  frameFromState,
  stepDelay,
  startsRound: (step) => step.kind === "round",
};

export type BlackjackStep = Step & TimelineStep<Frame>;
